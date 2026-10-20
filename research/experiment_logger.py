
import csv
import os
from datetime import datetime

RESULTS_FILE = "research/experiment_results.csv"

FIELDNAMES = [
    "timestamp",
    "category",
    "question",
    "selected_model",
    "quality_score",
    "verification_score",
    "verification_confidence",
    "verification_available",
    "consistency_score",
    "evidence_score",
    "supported_claims",
    "contradicted_claims",
    "insufficient_evidence",
    "error_claims",
    "total_claims",
    "final_trust_score",
    "trust_level",
]


def _round_optional(value, digits=4):
    if value is None:
        return ""
    try:
        return round(float(value), digits)
    except (TypeError, ValueError):
        return ""


def log_experiment(
    question,
    category,
    selected_model,
    quality_score,
    verification_score,
    verification_confidence,
    consistency_score,
    evidence_score,
    supported_count,
    contradicted_count,
    insufficient_count,
    total_claims,
    final_trust_score,
    trust_level,
    error_count=0,
):
    os.makedirs("research", exist_ok=True)
    file_exists = os.path.isfile(RESULTS_FILE)

    row = {
        "timestamp": datetime.now().isoformat(
            timespec="seconds"
        ),
        "category": category,
        "question": question,
        "selected_model": selected_model,
        "quality_score": _round_optional(quality_score),
        "verification_score": _round_optional(
            verification_score
        ),
        "verification_confidence": _round_optional(
            verification_confidence
        ),
        "verification_available": (
            verification_score is not None
        ),
        "consistency_score": _round_optional(
            consistency_score
        ),
        "evidence_score": _round_optional(evidence_score),
        "supported_claims": supported_count,
        "contradicted_claims": contradicted_count,
        "insufficient_evidence": insufficient_count,
        "error_claims": error_count,
        "total_claims": total_claims,
        "final_trust_score": _round_optional(
            final_trust_score
        ),
        "trust_level": trust_level,
    }

    with open(
        RESULTS_FILE,
        "a",
        newline="",
        encoding="utf-8",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=FIELDNAMES,
            extrasaction="ignore",
        )

        if not file_exists:
            writer.writeheader()

        writer.writerow(row)

    return RESULTS_FILE
