"""
FastAPI wrapper around the existing Multi-Agent validation pipeline.

Run from the project root:
    uvicorn api.main:app --port 8000
"""

import csv
import os
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# pipeline.py and the experiment logger use paths relative to the
# project root, so run from there.
os.chdir(PROJECT_ROOT)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

BENCHMARK_FILE = PROJECT_ROOT / "research" / "benchmark_questions.csv"
RESULTS_FILE = PROJECT_ROOT / "research" / "experiment_results.csv"

STARTUP_ERROR = None

try:
    from api import runner
except Exception as exc:  # noqa: BLE001
    runner = None
    STARTUP_ERROR = str(exc)


app = FastAPI(title="Verity AI API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ValidateRequest(BaseModel):
    question: str
    category: str = "Manual"


# ---------------------------------------------------------
# HEALTH
# ---------------------------------------------------------

@app.get("/api/health")
def health():
    return {
        "ok": STARTUP_ERROR is None,
        "error": STARTUP_ERROR,
        "busy": bool(runner and runner.is_busy()),
    }


# ---------------------------------------------------------
# BENCHMARK QUESTIONS (read-only)
# ---------------------------------------------------------

@app.get("/api/benchmark-questions")
def benchmark_questions():
    if not BENCHMARK_FILE.is_file():
        return []

    with open(BENCHMARK_FILE, newline="", encoding="utf-8") as file:
        return [
            {
                "id": row.get("question_id", ""),
                "category": row.get("category", ""),
                "question": (row.get("question") or "").strip(),
            }
            for row in csv.DictReader(file)
            if row.get("question")
        ]


# ---------------------------------------------------------
# VALIDATE
# ---------------------------------------------------------

@app.post("/api/validate", status_code=202)
def validate(request: ValidateRequest):
    if runner is None:
        raise HTTPException(
            status_code=503,
            detail=f"Backend failed to start: {STARTUP_ERROR}",
        )

    question = request.question.strip()

    if not question:
        raise HTTPException(
            status_code=422, detail="Please enter a question."
        )

    if len(question) > 1000:
        raise HTTPException(
            status_code=422,
            detail="Question must be 1000 characters or fewer.",
        )

    run_id = runner.start_run(question, request.category or "Manual")

    if run_id is None:
        raise HTTPException(
            status_code=409,
            detail=(
                "Another validation is already running. "
                "Please wait for it to finish."
            ),
        )

    return {"id": run_id}


@app.get("/api/runs/{run_id}")
def get_run(run_id: str):
    if runner is None:
        raise HTTPException(status_code=503, detail=STARTUP_ERROR)

    run = runner.get_run(run_id)

    if run is None:
        raise HTTPException(status_code=404, detail="Run not found.")

    return run


# ---------------------------------------------------------
# HISTORY (read-only view of the experiment CSV)
# ---------------------------------------------------------

def _to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


@app.get("/api/history")
def history():
    rows = []

    if RESULTS_FILE.is_file():
        with open(RESULTS_FILE, newline="", encoding="utf-8") as file:
            rows = list(csv.DictReader(file))

    latest_run_for_question = {}

    if runner is not None:
        for saved in sorted(
            runner.list_saved_runs(),
            key=lambda item: item.get("created_at") or "",
        ):
            if saved["status"] == "done":
                latest_run_for_question[saved["question"]] = saved["id"]

    items = []

    for row in rows:
        trust = _to_float(row.get("final_trust_score"))
        question = (row.get("question") or "").strip()

        if trust is None or not question:
            continue

        items.append(
            {
                "timestamp": row.get("timestamp", ""),
                "question": question,
                "category": row.get("category", ""),
                "winner": row.get("selected_model", ""),
                "trust_score": trust,
                "trust_level": row.get("trust_level", ""),
                "run_id": latest_run_for_question.get(question),
            }
        )

    items.sort(key=lambda item: item["timestamp"], reverse=True)

    scores = [item["trust_score"] for item in items]
    winners = Counter(item["winner"] for item in items if item["winner"])

    stats = {
        "total": len(items),
        "average_trust": (sum(scores) / len(scores)) if scores else None,
        "high_trust_pct": (
            100 * sum(1 for item in items if item["trust_level"] == "HIGH TRUST")
            / len(items)
            if items
            else None
        ),
        "top_model": winners.most_common(1)[0][0] if winners else None,
        "model_wins": dict(winners),
        "levels": dict(Counter(item["trust_level"] for item in items)),
    }

    by_category = {}

    for item in items:
        by_category.setdefault(item["category"], []).append(
            item["trust_score"]
        )

    stats["category_average"] = {
        category: sum(values) / len(values)
        for category, values in by_category.items()
    }

    return {"items": items, "stats": stats}
