import os
import time
import random

from dotenv import load_dotenv
from google import genai
from groq import Groq

from evaluation.similarity import calculate_similarity
from evaluation.evaluator import evaluate_response
from evaluation.scoring import (
    calculate_quality_scores,
    rank_models,
)

from verification.verifier import verify_answer
from verification.claim_extractor import extract_claims

from retrieval.evidence_retriever import retrieve_evidence
from retrieval.evidence_verifier import verify_claim_with_evidence

from research.experiment_logger import log_experiment


# =========================================================
# CONFIGURATION
# =========================================================

load_dotenv()

google_api_key = os.getenv("GOOGLE_API_KEY")
groq_api_key = os.getenv("GROQ_API_KEY")

if not groq_api_key:
    raise RuntimeError(
        "GROQ_API_KEY is missing from the .env file."
    )

gemini_client = (
    genai.Client(api_key=google_api_key)
    if google_api_key
    else None
)

groq_client = Groq(
    api_key=groq_api_key
)


# =========================================================
# MODEL RESPONSE GENERATION
# =========================================================
def run_with_retry(
    function,
    *args,
    max_retries=3,
    base_delay=15,
    **kwargs
):
    """
    Execute an API-dependent function with retry support.

    Useful for temporary rate-limit (429) and
    service availability errors.
    """

    last_error = None

    for attempt in range(max_retries):

        try:
            return function(*args, **kwargs)

        except Exception as e:

            last_error = e
            error_text = str(e).lower()

            # ---------------------------------------------
            # Daily quota exhausted -> do NOT retry
            # ---------------------------------------------
            daily_quota_exhausted = any(
                keyword in error_text
                for keyword in [
                    "tokens per day",
                    "(tpd)",
                    "daily limit",
                    "daily quota"
                ]
            )

            if daily_quota_exhausted:

                print(
                    "Daily API token quota exhausted. "
                    "Skipping retries for this request."
                )

                raise

            # ---------------------------------------------
            # Temporary API/rate-limit errors -> retry
            # ---------------------------------------------
            retryable = any(
                keyword in error_text
                for keyword in [
                    "429",
                    "rate limit",
                    "rate_limit",
                    "too many requests",
                    "temporarily unavailable",
                    "503",
                    "invalid json",
                    "empty response",
                    "timed out",
                    "timeout",
                    "connection"
                ]
            )

            if not retryable:
                raise

            if attempt == max_retries - 1:
                break

            wait_time = (
                base_delay * (2 ** attempt)
                + random.uniform(0, 3)
            )

            print(
                f"Temporary API limit. "
                f"Retrying in {wait_time:.1f} seconds..."
            )

            time.sleep(wait_time)

    raise last_error

def generate_model_responses(question):

    agent_prompt = f"""
Answer the following question accurately, clearly,
and completely.

Instructions:

- Answer only what is asked.
- Keep the final response between approximately
  250 and 400 words.
- Include the important information required to
  answer the question.
- Avoid unnecessary repetition.
- Be factual and objective.
- Use headings or bullet points only when useful.
- Do not expose internal reasoning or chain-of-thought.
- Make sure the final answer is complete and does
  not end in the middle of a sentence, list, or table.

User Question:

{question}
"""

    responses = {}
    errors = {}

    # -----------------------------------------------------
    # GEMINI
    # -----------------------------------------------------

    if gemini_client is not None:

        try:

            response = gemini_client.models.generate_content(
                model="gemini-3-flash-preview",
                contents=agent_prompt
            )

            text = response.text

            if text and text.strip():
                responses["Gemini"] = text.strip()

        except Exception as e:

            errors["Gemini"] = str(e)

    else:

        errors["Gemini"] = (
            "GOOGLE_API_KEY is unavailable."
        )

    # -----------------------------------------------------
    # GPT-OSS
    # -----------------------------------------------------

    try:

        response = groq_client.chat.completions.create(

            model="openai/gpt-oss-120b",

            messages=[
                {
                    "role": "user",
                    "content": agent_prompt
                }
            ],

            temperature=0.7,
            max_tokens=4096
        )

        text = (
            response
            .choices[0]
            .message
            .content
        )

        if text and text.strip():
            responses["GPT-OSS"] = text.strip()

    except Exception as e:

        errors["GPT-OSS"] = str(e)

    # -----------------------------------------------------
    # QWEN
    # -----------------------------------------------------

    try:

        response = groq_client.chat.completions.create(

            model="qwen/qwen3.8-27b",

            messages=[
                {
                    "role": "user",
                    "content": agent_prompt
                }
            ],

            reasoning_effort="none",
            temperature=0.7,
            max_tokens=2000
        )

        text = (
            response
            .choices[0]
            .message
            .content
        )

        if text and text.strip():
            responses["Qwen"] = text.strip()

    except Exception as e:

        errors["Qwen"] = str(e)

    return responses, errors


# =========================================================
# CONSISTENCY CALCULATION
# =========================================================

def calculate_consistency(responses):

    if len(responses) < 2:
        return {}, None

    model_names, similarity_matrix = (
        calculate_similarity(responses)
    )

    consistency_scores = {}

    for i, model in enumerate(model_names):

        other_scores = [
            similarity_matrix[i][j]
            for j in range(len(model_names))
            if i != j
        ]

        if other_scores:

            average_similarity = (
                sum(other_scores)
                / len(other_scores)
            )

        else:

            average_similarity = 0

        consistency_scores[model] = float(
            average_similarity
        )

    return consistency_scores, similarity_matrix


# =========================================================
# RESPONSE EVALUATION
# =========================================================
def evaluate_responses(
    question,
    responses,
    consistency_scores
):

    evaluation_results = {}
    errors = {}

    for model, response_text in responses.items():

        try:

            scores = run_with_retry(
                evaluate_response,
                groq_client,
                question,
                response_text,
                max_retries=3,
                base_delay=15
            )

            if model in consistency_scores:

                scores["consistency"] = (
                    consistency_scores[model] * 10
                )

            evaluation_results[model] = scores

        except Exception as e:

            errors[model] = str(e)

            print(
                f"Evaluation failed for "
                f"{model}: {e}"
            )

    return evaluation_results, errors


# =========================================================
# VERIFICATION
# =========================================================

def run_verification(
    question,
    selected_response
):

    verification = {}
    verification_score = None
    confidence = None
    verification_available = False
    error = None

    try:

        verification = run_with_retry(
        verify_answer,
        groq_client,
        question,
        selected_response,
        max_retries=3,
        base_delay=15
    )

        verification_score = verification.get(
            "verification_score"
        )

        confidence = verification.get(
            "confidence"
        )

        verification_available = (
            verification_score is not None
        )

    except Exception as e:

        error = str(e)

    return {
        "verification": verification,
        "verification_score": verification_score,
        "confidence": confidence,
        "available": verification_available,
        "error": error
    }


# =========================================================
# CLAIM EXTRACTION
# =========================================================

def run_claim_extraction(
    question,
    selected_response
):

    try:

        claims = extract_claims(
            groq_client,
            question,
            selected_response
        )

        return claims or [], None

    except Exception as e:

        return [], str(e)


# =========================================================
# EXTERNAL EVIDENCE
# =========================================================

def verify_external_evidence(claims):

    evidence_results = []

    for claim in claims:

        try:

            evidence = run_with_retry(
                retrieve_evidence,
                claim,
                max_results=3,
                max_retries=3,
                base_delay=5
            )

            if evidence:

                verification = run_with_retry(
                    verify_claim_with_evidence,
                    client=groq_client,
                    claim=claim,
                    evidence=evidence,
                    max_retries=3,
                    base_delay=5
                )

            else:

                verification = {
                    "status": "INSUFFICIENT_EVIDENCE",
                    "confidence": 0,
                    "reason": (
                        "No relevant external evidence "
                        "was retrieved."
                    )
                }

            evidence_results.append({

                "claim": claim,

                "status": verification.get(
                    "status",
                    "INSUFFICIENT_EVIDENCE"
                ),

                "confidence": verification.get(
                    "confidence",
                    0
                ),

                "reason": verification.get(
                    "reason",
                    ""
                ),

                "evidence": evidence or []
            })

        except Exception as e:

            print(
                f"DEBUG: Evidence check failed for claim "
                f"{claim!r}: {e}"
            )

            evidence_results.append({

                "claim": claim,

                "status": "ERROR",

                "confidence": 0,

                "reason": str(e),

                "evidence": []
            })
    print("DEBUG: Input claims:", len(claims))
    print("DEBUG: Result statuses:", [
    item.get("status") for item in evidence_results
])
    print("\nDEBUG: Evidence results count:", len(evidence_results))
    print("DEBUG: Input claims count:", len(claims))

    for item in evidence_results:
        print(
            "DEBUG:",
            item.get("status"),
            "-",
            item.get("claim")
        )

    return evidence_results


    

# =========================================================
# EVIDENCE SCORE
# =========================================================

def calculate_evidence_score(
    evidence_results
):

    supported = 0
    contradicted = 0
    insufficient = 0
    errors = 0

    for result in evidence_results:

        status = str(
            result.get("status", "")
        ).upper()

        if status == "SUPPORTED":
            supported += 1

        elif status == "CONTRADICTED":
            contradicted += 1

        elif status == "INSUFFICIENT_EVIDENCE":
            insufficient += 1

        else:
            errors += 1

    total = len(evidence_results)

    print("\n--- DEBUG: EVIDENCE RESULTS ---")
    print("Total evidence results:", total)

    for i, result in enumerate(evidence_results, start=1):
        print(
        f"Claim {i}: "
        f"status={result.get('status', 'MISSING')}"
    )

    print("--- END DEBUG ---\n")

    if total > 0:

        evidence_points = (
            supported
            + (0.5 * insufficient)
        )

        evidence_component = (
            evidence_points / total
        ) * 10

    else:

        evidence_component = 0

    
    return {
        "score": evidence_component,
        "supported": supported,
        "contradicted": contradicted,
        "insufficient": insufficient,
        "errors": errors,
        "total": total,
        "classified": (
            supported + contradicted + insufficient
        ),
        "unaccounted": (
            total
            - supported
            - contradicted
            - insufficient
            - errors
        ),
    }


# =========================================================
# FINAL TRUST CALCULATION
# =========================================================

def calculate_final_trust(
    quality_score,
    verification_score,
    verification_available,
    evidence_score,
    consistency_score
):

    weights = {
        "quality": 0.30,
        "verification": 0.25,
        "evidence": 0.35,
        "consistency": 0.10
    }

    active_components = {
        "quality": quality_score,
        "evidence": evidence_score,
        "consistency": consistency_score
    }

    if verification_available:

        active_components["verification"] = (
            verification_score
        )

    active_weight_total = sum(
        weights[name]
        for name in active_components
    )

    normalized_weights = {
        name:
            weights[name]
            / active_weight_total

        for name in active_components
    }

    final_score = sum(
        active_components[name]
        * normalized_weights[name]

        for name in active_components
    )

    if final_score >= 8:
        trust_level = "HIGH TRUST"

    elif final_score >= 6:
        trust_level = "MODERATE TRUST"

    else:
        trust_level = "LOW TRUST"

    return (
        final_score,
        trust_level,
        normalized_weights
    )


# =========================================================
# COMPLETE VALIDATION PIPELINE
# =========================================================

def run_validation_pipeline(
    question,
    category="General",
    log_result=True
):

    result = {
        "success": False,
        "question": question,
        "category": category
    }

    # -----------------------------------------------------
    # 1. GENERATE RESPONSES
    # -----------------------------------------------------

    responses, generation_errors = (
        generate_model_responses(question)
    )

    result["responses"] = responses
    result["generation_errors"] = generation_errors

    if len(responses) < 2:

        result["error"] = (
            "At least two successful model responses "
            "are required."
        )

        return result

    # -----------------------------------------------------
    # 2. CROSS-MODEL CONSISTENCY
    # -----------------------------------------------------

    try:

        (
            consistency_scores,
            similarity_matrix

        ) = calculate_consistency(
            responses
        )

    except Exception as e:

        result["error"] = (
            f"Similarity calculation failed: {e}"
        )

        return result

    result["consistency_scores"] = (
        consistency_scores
    )

    result["similarity_matrix"] = (
        similarity_matrix
    )

    # -----------------------------------------------------
    # 3. EVALUATION
    # -----------------------------------------------------

    (
        evaluation_results,
        evaluation_errors

    ) = evaluate_responses(
        question,
        responses,
        consistency_scores
    )

    result["evaluation_results"] = (
        evaluation_results
    )

    result["evaluation_errors"] = (
        evaluation_errors
    )

    if not evaluation_results:

        error_details = "; ".join(
            f"{model}: {error}"
            for model, error
            in evaluation_errors.items()
        )

        result["error"] = (
            "No model could be evaluated. "
            + (
                f"Details: {error_details}"
                if error_details
                else ""
            )
        )

        return result

    # -----------------------------------------------------
    # 4. QUALITY SCORING
    # -----------------------------------------------------

    quality_scores = calculate_quality_scores(
        evaluation_results
    )

    ranked_models = rank_models(
        quality_scores
    )

    if not ranked_models:

        result["error"] = (
            "Model ranking failed."
        )

        return result

    best_model = ranked_models[0][0]
    best_score = float(ranked_models[0][1])

    best_response = responses[
        best_model
    ]

    result["quality_scores"] = quality_scores
    result["ranked_models"] = ranked_models

    result["selected_model"] = best_model
    result["quality_score"] = best_score
    result["selected_response"] = best_response

    # -----------------------------------------------------
    # 5. VERIFICATION AGENT
    # -----------------------------------------------------

    verification_result = (
        run_verification(
            question,
            best_response
        )
    )

    result["verification"] = (
        verification_result
    )

    verification_score = (
        verification_result[
            "verification_score"
        ]
    )

    confidence = (
        verification_result[
            "confidence"
        ]
    )

    verification_available = (
        verification_result[
            "available"
        ]
    )

    # -----------------------------------------------------
    # 6. CLAIM EXTRACTION
    # -----------------------------------------------------

    claims, claim_error = (
        run_claim_extraction(
            question,
            best_response
        )
    )

    result["claims"] = claims
    result["claim_extraction_error"] = (
        claim_error
    )

    # -----------------------------------------------------
    # 7. EXTERNAL EVIDENCE
    # -----------------------------------------------------

    evidence_results = (
        verify_external_evidence(
            claims
        )
    )

    result["evidence_results"] = (
        evidence_results
    )

    
    # Diagnostic: compare extracted claims with evidence results
    print("\nCLAIM COUNT DIAGNOSTICS")
    print("-----------------------")
    print("Extracted claims:", len(claims))
    print("Evidence results:", len(evidence_results))

    status_counts = {}

    for item in evidence_results:
        status = str(
            item.get("status", "MISSING")
        ).upper()

        status_counts[status] = (
            status_counts.get(status, 0) + 1
        )

    print("Evidence status counts:", status_counts)


    # -----------------------------------------------------
    # 8. EVIDENCE SCORE
    # -----------------------------------------------------

    evidence_summary = (
        calculate_evidence_score(
            evidence_results
        )
    )

    result["evidence_summary"] = (
        evidence_summary
    )

    print("\n=== PIPELINE EVIDENCE SUMMARY ===")
    print("Actual evidence results:", len(evidence_results))
    print("Evidence summary:", evidence_summary)
    print("Original extracted claims:", len(claims))

    # -----------------------------------------------------
    # BENCHMARK VALIDITY CHECK
    # -----------------------------------------------------

    validation_errors = []

    verification_error = verification_result.get("error")

    if verification_error:
        validation_errors.append(
            f"Verification failed: {verification_error}"
        )

    if not verification_available:
        validation_errors.append(
            "Verification score unavailable."
        )

    if claim_error:
        validation_errors.append(
            f"Claim extraction failed: {claim_error}"
        )

    if not claims:
        validation_errors.append(
            "No factual claims were extracted."
        )

    evidence_error_count = evidence_summary.get("errors", 0)

    if evidence_error_count > 0:
        validation_errors.append(
            f"{evidence_error_count} evidence "
            "verification operation(s) failed."
        )

    benchmark_valid = len(validation_errors) == 0

    result["benchmark_valid"] = benchmark_valid
    result["validation_errors"] = validation_errors

    # -----------------------------------------------------
    # 9. CONSISTENCY COMPONENT
    # -----------------------------------------------------

    consistency_component = (
        consistency_scores.get(
            best_model,
            0
        ) * 10
    )

    # -----------------------------------------------------
    # 10. FINAL TRUST SCORE
    # -----------------------------------------------------

    (
        final_trust_score,
        trust_level,
        normalized_weights

    ) = calculate_final_trust(

        quality_score=best_score,

        verification_score=(
            verification_score
        ),

        verification_available=(
            verification_available
        ),

        evidence_score=(
            evidence_summary["score"]
        ),

        consistency_score=(
            consistency_component
        )
    )

    result["consistency_score"] = (
        consistency_component
    )

    result["final_trust_score"] = (
        final_trust_score
    )

    result["trust_percentage"] = (
        final_trust_score * 10
    )

    result["trust_level"] = trust_level

    result["normalized_weights"] = (
        normalized_weights
    )

    # -----------------------------------------------------
    # 11. LOG EXPERIMENT
    # -----------------------------------------------------

    if log_result and benchmark_valid:

        try:

            log_experiment(

                question=question,

                category=category,

                selected_model=best_model,

                quality_score=best_score,

                verification_score=(
                    verification_score
                ),

                verification_confidence=(
                    confidence
                ),

                consistency_score=(
                    consistency_component
                ),

                evidence_score=(
                    evidence_summary["score"]
                ),

                supported_count=(
                    evidence_summary["supported"]
                ),

                contradicted_count=(
                    evidence_summary["contradicted"]
                ),

                insufficient_count=(
                    evidence_summary["insufficient"]
                ),

                total_claims=(
                    evidence_summary["total"]
                ),

                final_trust_score=(
                    final_trust_score
                ),

                trust_level=trust_level
            )

            result["logged"] = True

        except Exception as e:

            result["logged"] = False
            result["logging_error"] = str(e)

    elif log_result and not benchmark_valid:

        result["logged"] = False
        result["logging_error"] = (
            "Experiment was not logged because "
            "one or more required validation "
            "stages were incomplete."
        )

    # -----------------------------------------------------
    # COMPLETE
    # -----------------------------------------------------

    if benchmark_valid:
        result["success"] = True
    else:
        result["success"] = False
        result["incomplete"] = True
        result["error"] = (
            "Experiment incomplete: "
            + " | ".join(validation_errors)
        )

    return result