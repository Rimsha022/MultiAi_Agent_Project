"""
Step-by-step runner that wraps the existing pipeline functions so the
React UI can show live progress. It reuses pipeline.py unchanged and
follows the same order and validity rules as run_validation_pipeline().
"""

import json
import threading
from datetime import datetime
from pathlib import Path

import pipeline as P
from agents.synthesis_agent import synthesize_verified_answer
from research.experiment_logger import log_experiment

RUNS_DIR = Path(__file__).resolve().parent / "data" / "runs"
RUNS_DIR.mkdir(parents=True, exist_ok=True)

MODEL_NAMES = ["Gemini", "GPT-OSS", "Qwen"]

STAGES = [
    ("generate", "Generate answers"),
    ("compare", "Compare responses"),
    ("judge", "Judge quality"),
    ("verify", "Verify claims"),
    ("evidence", "Check evidence"),
    ("trust", "Compute trust score"),
]

RATE_LIMIT_KEYWORDS = ("429", "rate limit", "rate_limit", "quota", "resource_exhausted")

_lock = threading.Lock()
_runs = {}
_active_run_id = None


# ---------------------------------------------------------
# RUN STATE HELPERS
# ---------------------------------------------------------

def _now():
    return datetime.now().isoformat(timespec="seconds")


def _next_id():
    numbers = []
    for path in RUNS_DIR.glob("VR-*.json"):
        try:
            numbers.append(int(path.stem.split("-")[1]))
        except (IndexError, ValueError):
            continue
    for run_id in _runs:
        try:
            numbers.append(int(run_id.split("-")[1]))
        except (IndexError, ValueError):
            continue
    return f"VR-{(max(numbers) + 1 if numbers else 1):05d}"


def _set_stage(run, key, status, detail=None):
    with _lock:
        for stage in run["stages"]:
            if stage["key"] == key:
                stage["status"] = status
                if detail is not None:
                    stage["detail"] = detail


def _notice(run, level, title, message):
    with _lock:
        run["notices"].append(
            {"level": level, "title": title, "message": message}
        )


def _set_model(run, name, status, detail):
    with _lock:
        run["models"][name] = {"status": status, "detail": detail}


def _save(run):
    path = RUNS_DIR / f"{run['id']}.json"
    with _lock:
        path.write_text(json.dumps(run, indent=2), encoding="utf-8")


def is_busy():
    return _active_run_id is not None


def get_run(run_id):
    with _lock:
        if run_id in _runs:
            return json.loads(json.dumps(_runs[run_id]))
    path = RUNS_DIR / f"{run_id}.json"
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    return None


def list_saved_runs():
    runs = []
    for path in RUNS_DIR.glob("VR-*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        runs.append(
            {
                "id": data.get("id"),
                "question": (data.get("question") or "").strip(),
                "created_at": data.get("created_at"),
                "status": data.get("status"),
            }
        )
    return runs


def start_run(question, category):
    """Create a run and start it in a background thread."""
    global _active_run_id

    with _lock:
        if _active_run_id is not None:
            return None

        run_id = _next_id()

        run = {
            "id": run_id,
            "question": question,
            "category": category,
            "status": "running",
            "created_at": _now(),
            "finished_at": None,
            "stages": [
                {"key": key, "label": label, "status": "queued", "detail": ""}
                for key, label in STAGES
            ],
            "models": {
                name: {"status": "queued", "detail": "Waiting"}
                for name in MODEL_NAMES
            },
            "notices": [],
            "result": None,
            "error": None,
        }

        _runs[run_id] = run
        _active_run_id = run_id

    threading.Thread(target=_execute, args=(run,), daemon=True).start()
    return run_id


# ---------------------------------------------------------
# EXECUTION
# ---------------------------------------------------------

def _execute(run):
    global _active_run_id

    try:
        _run_steps(run)
        run["status"] = "done"

    except Exception as exc:  # noqa: BLE001
        run["status"] = "error"
        run["error"] = str(exc)

        for stage in run["stages"]:
            if stage["status"] == "in_progress":
                stage["status"] = "error"

    finally:
        run["finished_at"] = _now()
        _save(run)

        with _lock:
            _active_run_id = None


def _short(text, limit=220):
    text = str(text).replace("\n", " ").strip()
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _run_steps(run):
    question = run["question"]
    category = run["category"]

    # -----------------------------------------------------
    # 1. GENERATE
    # -----------------------------------------------------
    _set_stage(run, "generate", "in_progress", "Asking three models")

    for name in MODEL_NAMES:
        _set_model(run, name, "generating", "Generating…")

    responses, generation_errors = P.generate_model_responses(question)

    for name in MODEL_NAMES:
        if name in responses:
            _set_model(run, name, "responded", "Responded")
            continue

        error_text = generation_errors.get(name, "No response returned.")
        rate_limited = any(
            keyword in error_text.lower()
            for keyword in RATE_LIMIT_KEYWORDS
        )

        _set_model(
            run,
            name,
            "rate_limited" if rate_limited else "failed",
            "Rate limit reached" if rate_limited else "Request failed",
        )
        _notice(
            run,
            "warning",
            f"{name} request limit reached"
            if rate_limited
            else f"{name} failed",
            _short(error_text),
        )

    if len(responses) < 2:
        raise RuntimeError(
            "At least two successful model responses are required."
        )

    if len(responses) < len(MODEL_NAMES):
        _notice(
            run,
            "info",
            "Failed model fallback",
            f"Proceeding with {len(responses)} valid model answers.",
        )

    _set_stage(
        run, "generate", "complete", f"{len(responses)} answers received"
    )

    # -----------------------------------------------------
    # 2. COMPARE
    # -----------------------------------------------------
    _set_stage(run, "compare", "in_progress", "Measuring agreement")

    consistency_scores, similarity_matrix = P.calculate_consistency(
        responses
    )
    similarity_models = list(responses.keys())

    _set_stage(run, "compare", "complete", "Agreement measured")

    # -----------------------------------------------------
    # 3. JUDGE
    # -----------------------------------------------------
    _set_stage(run, "judge", "in_progress", "Scoring each answer")

    evaluation_results, evaluation_errors = P.evaluate_responses(
        question, responses, consistency_scores
    )

    for name, error_text in evaluation_errors.items():
        _notice(
            run,
            "warning",
            f"{name} could not be judged",
            _short(error_text),
        )

    if not evaluation_results:
        raise RuntimeError("No model could be evaluated.")

    quality_scores = P.calculate_quality_scores(evaluation_results)
    ranked_models = P.rank_models(quality_scores)

    if not ranked_models:
        raise RuntimeError("Model ranking failed.")

    best_model = ranked_models[0][0]
    best_score = float(ranked_models[0][1])
    best_response = responses[best_model]

    _set_stage(run, "judge", "complete", f"Winner: {best_model}")

    # -----------------------------------------------------
    # 4. VERIFY (verifier agent + claim extraction)
    # -----------------------------------------------------
    _set_stage(run, "verify", "in_progress", "Extracting claims")

    verification_result = P.run_verification(question, best_response)
    claims, claim_error = P.run_claim_extraction(question, best_response)

    verification_score = verification_result["verification_score"]
    verification_available = verification_result["available"]

    _set_stage(run, "verify", "complete", f"{len(claims)} claims found")

    # -----------------------------------------------------
    # 5. EVIDENCE (one claim at a time for live progress)
    # -----------------------------------------------------
    _set_stage(run, "evidence", "in_progress", f"0 / {len(claims)} claims")

    evidence_results = []

    for index, claim in enumerate(claims, start=1):
        evidence_results.extend(P.verify_external_evidence([claim]))
        _set_stage(
            run,
            "evidence",
            "in_progress",
            f"{index} / {len(claims)} claims",
        )

    evidence_summary = P.calculate_evidence_score(evidence_results)

    _set_stage(
        run,
        "evidence",
        "complete",
        f"{evidence_summary['supported']} of {evidence_summary['total']} supported",
    )

    # -----------------------------------------------------
    # VALIDITY (same rules as run_validation_pipeline)
    # -----------------------------------------------------
    validation_errors = []

    if verification_result.get("error"):
        validation_errors.append(
            f"Verification failed: {verification_result['error']}"
        )

    if not verification_available:
        validation_errors.append("Verification score unavailable.")

    if claim_error:
        validation_errors.append(
            f"Claim extraction failed: {claim_error}"
        )

    if not claims:
        validation_errors.append("No factual claims were extracted.")

    if evidence_summary.get("errors", 0) > 0:
        validation_errors.append(
            f"{evidence_summary['errors']} evidence verification "
            "operation(s) failed."
        )

    valid = not validation_errors

    # -----------------------------------------------------
    # 6. TRUST SCORE
    # -----------------------------------------------------
    _set_stage(run, "trust", "in_progress", "Combining scores")

    consistency_component = consistency_scores.get(best_model, 0) * 10

    final_score, trust_level, weights = P.calculate_final_trust(
        quality_score=best_score,
        verification_score=verification_score,
        verification_available=verification_available,
        evidence_score=evidence_summary["score"],
        consistency_score=consistency_component,
    )

    # Verified answer (kept non-fatal: a failure falls back to the
    # selected answer and is reported as a notice).
    verified_answer = best_response
    corrections = []
    uncertain_removed = []
    synthesis_ok = False

    try:
        synthesis = P.run_with_retry(
            synthesize_verified_answer,
            P.groq_client,
            question,
            best_response,
            evidence_results,
            max_retries=3,
            base_delay=15,
        )
        verified_answer = synthesis["verified_answer"]
        corrections = [str(item) for item in synthesis["corrections_made"]]
        uncertain_removed = [
            str(item) for item in synthesis["uncertain_claims_removed"]
        ]
        synthesis_ok = True

    except Exception as exc:  # noqa: BLE001
        _notice(
            run,
            "warning",
            "Verified answer unavailable",
            f"Showing the selected model answer instead. {_short(exc)}",
        )

    logged = False
    logging_error = None

    if valid:
        try:
            log_experiment(
                question=question,
                category=category,
                selected_model=best_model,
                quality_score=best_score,
                verification_score=verification_score,
                verification_confidence=verification_result["confidence"],
                consistency_score=consistency_component,
                evidence_score=evidence_summary["score"],
                supported_count=evidence_summary["supported"],
                contradicted_count=evidence_summary["contradicted"],
                insufficient_count=evidence_summary["insufficient"],
                total_claims=evidence_summary["total"],
                final_trust_score=final_score,
                trust_level=trust_level,
                error_count=evidence_summary["errors"],
            )
            logged = True
        except Exception as exc:  # noqa: BLE001
            logging_error = str(exc)
    else:
        _notice(
            run,
            "warning",
            "Incomplete validation",
            " | ".join(validation_errors),
        )

    _set_stage(run, "trust", "complete", f"{final_score:.1f} / 10")

    # -----------------------------------------------------
    # RESULT PAYLOAD
    # -----------------------------------------------------
    answers = []

    for name, text in responses.items():
        criteria = {
            key: float(value)
            for key, value in evaluation_results.get(name, {}).items()
            if key != "consistency"
        }
        answers.append(
            {
                "model": name,
                "text": text,
                "quality": quality_scores.get(name),
                "consistency": float(consistency_scores.get(name, 0)),
                "criteria": criteria,
                "selected": name == best_model,
            }
        )

    answers.sort(key=lambda item: (not item["selected"], -(item["quality"] or 0)))

    claim_rows = []

    for item in evidence_results:
        claim_rows.append(
            {
                "claim": item.get("claim", ""),
                "status": str(item.get("status", "")).upper(),
                "confidence": float(item.get("confidence") or 0),
                "reason": item.get("reason", ""),
                "sources": [
                    {
                        "title": source.get("title", ""),
                        "url": source.get("url", ""),
                        "snippet": source.get("content", ""),
                    }
                    for source in item.get("evidence", [])
                ],
            }
        )

    verification = verification_result.get("verification", {}) or {}

    run["result"] = {
        "valid": valid,
        "validation_errors": validation_errors,
        "logged": logged,
        "logging_error": logging_error,
        "trust_score": float(final_score),
        "trust_level": trust_level,
        "weights": weights,
        "scores": {
            "quality": float(best_score),
            "consistency": float(consistency_component),
            "verification": (
                float(verification_score)
                if verification_score is not None
                else None
            ),
            "evidence": float(evidence_summary["score"]),
        },
        "winning_model": best_model,
        "models_compared": len(responses),
        "verified_answer": verified_answer,
        "verified_answer_generated": synthesis_ok,
        "corrections": corrections,
        "uncertain_removed": uncertain_removed,
        "answers": answers,
        "similarity": {
            "models": similarity_models,
            "matrix": [
                [float(value) for value in row]
                for row in similarity_matrix
            ],
        },
        "claims": claim_rows,
        "claims_summary": {
            "supported": evidence_summary["supported"],
            "contradicted": evidence_summary["contradicted"],
            "insufficient": evidence_summary["insufficient"],
            "errors": evidence_summary["errors"],
            "total": evidence_summary["total"],
        },
        "verification": {
            "score": verification_score,
            "confidence": verification_result.get("confidence"),
            "reason": verification.get("reason", ""),
            "unsupported_claims": verification.get("unsupported_claims", []),
        },
    }
