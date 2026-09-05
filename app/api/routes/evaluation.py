from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from evaluation.batch_recovery_eval import run_batch_evaluation

router = APIRouter(
    prefix="/evaluation",
    tags=["Evaluation"],
)

RESULTS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "evaluation" / "results"


class EvaluationRunRequest(BaseModel):
    n: int = Field(default=500, ge=1, le=1000, description="Number of synthetic cases to evaluate")
    concurrency: int = Field(default=8, ge=1, le=20, description="Concurrency level for Gemini evaluation")
    seed: int = Field(default=20260902, description="Random seed for synthetic case generation")


class EvaluationRunState:
    def __init__(self, run_id: str, total: int):
        self.run_id = run_id
        self.status = "running"  # "running" | "completed" | "failed"
        self.total = total
        self.completed = 0
        self.started_at = datetime.now(timezone.utc).isoformat()
        self.completed_at: str | None = None
        self.start_time = time.time()
        self.elapsed_seconds: float = 0.0
        self.summary: dict[str, Any] | None = None
        self.json_path: str | None = None
        self.csv_path: str | None = None
        self.error: str | None = None


# In-memory tracking for active and recent evaluation runs
_active_runs: dict[str, EvaluationRunState] = {}
_latest_active_run_id: str | None = None


def _find_latest_result_file() -> dict[str, Any] | None:
    """Find and parse the latest generated batch_*.json file."""
    if not RESULTS_DIR.exists():
        return None

    json_files = sorted(
        RESULTS_DIR.glob("batch_*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not json_files:
        return None

    for candidate in json_files:
        try:
            content = json.loads(candidate.read_text(encoding="utf-8"))
            summary = content.get("summary", content)
            created_at = datetime.fromtimestamp(
                candidate.stat().st_mtime, timezone.utc
            ).isoformat()
            return {
                "file_name": candidate.name,
                "created_at": created_at,
                "summary": summary,
            }
        except Exception:
            continue
    return None


@router.get("/latest")
async def get_latest_evaluation():
    """Return the latest completed synthetic benchmark result."""
    # Check if there is a recently completed in-memory run
    global _latest_active_run_id
    if _latest_active_run_id and _latest_active_run_id in _active_runs:
        run = _active_runs[_latest_active_run_id]
        if run.status == "completed" and run.summary:
            return {
                "has_result": True,
                "run_id": run.run_id,
                "created_at": run.completed_at,
                "summary": run.summary,
            }

    latest = _find_latest_result_file()
    if latest is None:
        return {
            "has_result": False,
            "message": "No evaluation has been run yet.",
        }

    return {
        "has_result": True,
        "file_name": latest["file_name"],
        "created_at": latest["created_at"],
        "summary": latest["summary"],
    }


@router.post("/run", status_code=status.HTTP_202_ACCEPTED)
async def start_evaluation_run(payload: EvaluationRunRequest | None = None):
    """Start a new synthetic 500-case recovery evaluation in the background.

    Strictly synthetic: does NOT create database recovery cases, does NOT call
    Razorpay, does NOT create Payment Links, does NOT send emails.
    """
    global _latest_active_run_id

    req = payload or EvaluationRunRequest()

    # Check if a benchmark is already in flight
    for run in _active_runs.values():
        if run.status == "running":
            return {
                "run_id": run.run_id,
                "status": "running",
                "total": run.total,
                "completed": run.completed,
                "progress_percentage": round((run.completed / run.total) * 100, 1) if run.total else 0.0,
                "message": "A benchmark evaluation is already currently running.",
            }

    run_id = f"eval_{uuid4().hex[:12]}"
    run_state = EvaluationRunState(run_id=run_id, total=req.n)
    _active_runs[run_id] = run_state
    _latest_active_run_id = run_id

    def _on_progress(completed: int, total: int):
        run_state.completed = completed
        run_state.elapsed_seconds = round(time.time() - run_state.start_time, 1)

    async def _execute_bg_benchmark():
        try:
            result = await run_batch_evaluation(
                n=req.n,
                concurrency=req.concurrency,
                seed=req.seed,
                progress_callback=_on_progress,
            )
            run_state.status = "completed"
            run_state.completed = req.n
            run_state.completed_at = datetime.now(timezone.utc).isoformat()
            run_state.elapsed_seconds = round(time.time() - run_state.start_time, 1)
            run_state.summary = result.get("summary")
            run_state.json_path = result.get("json_path")
            run_state.csv_path = result.get("csv_path")
        except Exception as exc:
            run_state.status = "failed"
            run_state.completed_at = datetime.now(timezone.utc).isoformat()
            run_state.elapsed_seconds = round(time.time() - run_state.start_time, 1)
            run_state.error = str(exc)

    asyncio.create_task(_execute_bg_benchmark())

    return {
        "run_id": run_id,
        "status": "running",
        "total": req.n,
        "completed": 0,
        "progress_percentage": 0.0,
        "message": f"Started synthetic evaluation of {req.n} cases.",
    }


@router.get("/status/{run_id}")
async def get_evaluation_status(run_id: str):
    """Get live progress and result of a synthetic evaluation run."""
    run = _active_runs.get(run_id)
    if not run:
        # Check if run_id matches a file or fallback to latest
        latest = _find_latest_result_file()
        if latest:
            return {
                "run_id": run_id,
                "status": "completed",
                "total": latest["summary"].get("cases", 500),
                "completed": latest["summary"].get("cases", 500),
                "progress_percentage": 100.0,
                "summary": latest["summary"],
            }
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evaluation run not found",
        )

    elapsed = round(time.time() - run.start_time, 1) if run.status == "running" else run.elapsed_seconds
    progress = round((run.completed / run.total) * 100, 1) if run.total else 0.0

    return {
        "run_id": run.run_id,
        "status": run.status,
        "total": run.total,
        "completed": run.completed,
        "progress_percentage": progress,
        "elapsed_seconds": elapsed,
        "started_at": run.started_at,
        "completed_at": run.completed_at,
        "summary": run.summary,
        "error": run.error,
    }


@router.get("/runs")
async def list_evaluation_runs():
    """List historical synthetic evaluation batch files."""
    if not RESULTS_DIR.exists():
        return []

    results = []
    json_files = sorted(
        RESULTS_DIR.glob("batch_*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for f in json_files[:10]:
        try:
            content = json.loads(f.read_text(encoding="utf-8"))
            s = content.get("summary", {})
            results.append({
                "file_name": f.name,
                "cases": s.get("cases"),
                "valid_evaluations": s.get("valid_evaluations"),
                "decision_accuracy": s.get("decision_accuracy"),
                "simulated_recovery_rate": s.get("simulated_recovery_rate_by_amount"),
                "created_at": datetime.fromtimestamp(f.stat().st_mtime, timezone.utc).isoformat(),
            })
        except Exception:
            continue
    return results
