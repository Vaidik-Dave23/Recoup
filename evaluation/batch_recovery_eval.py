"""Synthetic batch benchmark for the Recoup recovery decision loop.

This benchmark intentionally separates model decisions from real money movement.
It generates a deterministic synthetic batch, runs the same Gemini triage and
strategy prompts used by the product, then evaluates the decisions against
known synthetic ground truth and a deterministic customer-response simulator.

Usage:
    python -m evaluation.batch_recovery_eval --n 100
    python -m evaluation.batch_recovery_eval --n 500 --concurrency 8

Outputs are written to evaluation/results/ as JSON + CSV.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import random
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.agent.gemini_client import GeminiCallError, call_json
from app.agent import prompts
from app.agent.policy import evaluate_recovery_decision
from app.core.config import settings


ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"

SCENARIOS = {
    "hard_decline": {
        "case_type": "payment_failed",
        "failure_reason": "stolen_card_decline",
        "amount_range": (1000, 25000),
        "payment_method": "card",
        "email_recovery_probability": 0.0,
        "ground_truth_action": "escalate",
    },
    "soft_decline": {
        "case_type": "payment_failed",
        "failure_reason": "insufficient_funds",
        "amount_range": (1000, 15000),
        "payment_method": "card",
        "email_recovery_probability": 0.68,
        "ground_truth_action": "email",
    },
    "abandoned_checkout": {
        "case_type": "abandoned_checkout",
        "failure_reason": "checkout_abandoned",
        "amount_range": (1500, 20000),
        "payment_method": "upi",
        "email_recovery_probability": 0.54,
        "ground_truth_action": "email",
    },
    "overdue_invoice": {
        "case_type": "overdue_invoice",
        "failure_reason": "invoice_unpaid_30_days",
        "amount_range": (15000, 150000),
        "payment_method": "bank_transfer",
        "email_recovery_probability": 0.42,
        "ground_truth_action": "email",
    },
}


@dataclass(frozen=True)
class SyntheticCase:
    case_id: str
    scenario: str
    case_type: str
    failure_reason: str
    amount_at_risk: int
    currency: str
    payment_method: str
    customer_name: str
    customer_email: str
    attempt_count: int
    would_recover_after_email: bool


@dataclass
class EvaluationRow:
    case_id: str
    scenario: str
    amount_at_risk: int
    ground_truth_action: str
    model_action: str
    model_confidence: float
    escalated: bool
    decision_source: str
    policy_reason: str | None
    decision_correct: bool
    simulated_recovered: bool
    simulated_amount_recovered: int
    error: str | None = None
    api_error: bool = False


def generate_cases(n: int, seed: int) -> list[SyntheticCase]:
    rng = random.Random(seed)
    scenario_names = list(SCENARIOS)
    cases: list[SyntheticCase] = []
    for i in range(n):
        scenario = scenario_names[i % len(scenario_names)]
        spec = SCENARIOS[scenario]
        amount = rng.randint(*spec["amount_range"])
        recovered = rng.random() < spec["email_recovery_probability"]
        cases.append(
            SyntheticCase(
                case_id=f"BATCH-{i + 1:04d}",
                scenario=scenario,
                case_type=spec["case_type"],
                failure_reason=spec["failure_reason"],
                amount_at_risk=amount,
                currency="INR",
                payment_method=spec["payment_method"],
                customer_name=f"Customer {i + 1}",
                customer_email=f"batch-{i + 1:04d}@example.com",
                attempt_count=0,
                would_recover_after_email=recovered,
            )
        )
    return cases


async def evaluate_case(case: SyntheticCase, sem: asyncio.Semaphore) -> EvaluationRow:
    async with sem:
        triage_prompt = prompts.TRIAGE_USER.format(
            case_type=case.case_type,
            failure_reason=case.failure_reason,
            amount_at_risk=case.amount_at_risk,
            currency=case.currency,
            attempt_count=case.attempt_count,
        )
        try:
            triage = await call_json(prompts.TRIAGE_SYSTEM, triage_prompt)
            strategy_prompt = prompts.STRATEGIZE_USER.format(
                triage_json=json.dumps(triage),
                case_type=case.case_type,
                amount_at_risk=case.amount_at_risk,
                currency=case.currency,
                attempt_number=case.attempt_count + 1,
            )
            strategy = await call_json(prompts.STRATEGIZE_SYSTEM, strategy_prompt)
            raw_action = str(strategy.get("action_type", "unknown")).lower()
            raw_channel = str(strategy.get("channel", "unknown")).lower()
            confidence = float(strategy.get("confidence", 0.0))

            # Evaluate using the exact same deterministic backend policy as production
            policy_decision = evaluate_recovery_decision(
                failure_reason=case.failure_reason,
                raw_action=raw_action,
                raw_channel=raw_channel,
                confidence=confidence,
                confidence_threshold=settings.recovery_confidence_threshold,
            )

            effective_action = policy_decision.effective_action
            escalated = policy_decision.escalated
            correct = effective_action == case_ground_truth(case)
            simulated_recovered = (
                effective_action == "email" and case.would_recover_after_email
            )
            amount_recovered = case.amount_at_risk if simulated_recovered else 0
            return EvaluationRow(
                case_id=case.case_id,
                scenario=case.scenario,
                amount_at_risk=case.amount_at_risk,
                ground_truth_action=case_ground_truth(case),
                model_action=effective_action,
                model_confidence=confidence,
                escalated=escalated,
                decision_source=policy_decision.decision_source,
                policy_reason=policy_decision.policy_reason,
                decision_correct=correct,
                simulated_recovered=simulated_recovered,
                simulated_amount_recovered=amount_recovered,
            )
        except GeminiCallError as exc:
            return EvaluationRow(
                case_id=case.case_id,
                scenario=case.scenario,
                amount_at_risk=case.amount_at_risk,
                ground_truth_action=case_ground_truth(case),
                model_action="error",
                model_confidence=0.0,
                escalated=False,
                decision_source="error",
                policy_reason=None,
                decision_correct=False,
                simulated_recovered=False,
                simulated_amount_recovered=0,
                error=str(exc),
                api_error=True,
            )
        except (TypeError, ValueError, KeyError) as exc:
            return EvaluationRow(
                case_id=case.case_id,
                scenario=case.scenario,
                amount_at_risk=case.amount_at_risk,
                ground_truth_action=case_ground_truth(case),
                model_action="error",
                model_confidence=0.0,
                escalated=False,
                decision_source="error",
                policy_reason=None,
                decision_correct=False,
                simulated_recovered=False,
                simulated_amount_recovered=0,
                error=str(exc),
                api_error=False,
            )


def case_ground_truth(case: SyntheticCase) -> str:
    return SCENARIOS[case.scenario]["ground_truth_action"]


def summarize(cases: list[SyntheticCase], rows: list[EvaluationRow], seed: int) -> dict[str, Any]:
    total = len(rows)
    valid_rows = [r for r in rows if not r.api_error and r.model_action != "error"]
    api_errors = [r for r in rows if r.api_error]
    total_at_risk = sum(c.amount_at_risk for c in cases)

    # Recovery is only measured from valid model decisions.
    recovered = sum(r.simulated_amount_recovered for r in valid_rows)
    correct = sum(r.decision_correct for r in valid_rows)
    escalations = sum(r.escalated for r in valid_rows)
    policy_overrides = sum(1 for r in valid_rows if r.decision_source == "policy")
    errors = len(api_errors)

    by_scenario: dict[str, dict[str, Any]] = {}
    for scenario in SCENARIOS:
        subset = [r for r in rows if r.scenario == scenario]
        valid_subset = [r for r in subset if not r.api_error and r.model_action != "error"]
        if not subset:
            continue

        at_risk = sum(r.amount_at_risk for r in valid_subset)
        recovered_s = sum(r.simulated_amount_recovered for r in valid_subset)

        by_scenario[scenario] = {
            "cases": len(subset),
            "valid_evaluations": len(valid_subset),
            "api_errors": sum(r.api_error for r in subset),
            "policy_overrides": sum(1 for r in valid_subset if r.decision_source == "policy"),
            "decision_accuracy": (
                round(sum(r.decision_correct for r in valid_subset) / len(valid_subset), 4)
                if valid_subset else None
            ),
            "escalation_rate": (
                round(sum(r.escalated for r in valid_subset) / len(valid_subset), 4)
                if valid_subset else None
            ),
            "simulated_amount_at_risk_inr": at_risk,
            "simulated_amount_recovered_inr": recovered_s,
            "simulated_recovery_rate_by_amount": (
                round(recovered_s / at_risk, 4) if at_risk else 0.0
            ),
        }

    return {
        "benchmark": "Recoup synthetic batch recovery benchmark",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "seed": seed,
        "cases": total,
        "valid_evaluations": len(valid_rows),
        "api_errors": errors,
        "policy_overrides": policy_overrides,
        "valid_evaluation_rate": round(len(valid_rows) / total, 4) if total else 0.0,
        "confidence_threshold": settings.recovery_confidence_threshold,
        "decision_accuracy": (
            round(correct / len(valid_rows), 4) if valid_rows else None
        ),
        "escalation_rate": (
            round(escalations / len(valid_rows), 4) if valid_rows else None
        ),
        "error_rate": round(errors / total, 4) if total else 0.0,
        "simulated_amount_at_risk_inr": total_at_risk,
        "simulated_amount_recovered_inr": recovered,
        "simulated_recovery_rate_by_amount": (
            round(recovered / total_at_risk, 4) if total_at_risk else 0.0
        ),
        "scenario_breakdown": by_scenario,
        "important_note": (
            "Recovered-money figures are synthetic benchmark outcomes, not real customer payments. "
            "Decision accuracy, escalation rate, and recovery metrics are calculated only from "
            "valid model evaluations. Gemini/API failures are reported separately as api_errors "
            "and are not counted as model decisions."
        ),
    }


def write_results(cases: list[SyntheticCase], rows: list[EvaluationRow], summary: dict[str, Any]) -> tuple[Path, Path]:
    RESULTS.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = RESULTS / f"batch_{stamp}.json"
    csv_path = RESULTS / f"batch_{stamp}.csv"
    payload = {"summary": summary, "cases": [asdict(c) for c in cases], "results": [asdict(r) for r in rows]}
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(asdict(rows[0]).keys()) if rows else list(EvaluationRow.__annotations__.keys()))
        writer.writeheader()
        writer.writerows(asdict(r) for r in rows)
    return json_path, csv_path


async def run_batch_evaluation(
    n: int = 500,
    concurrency: int = 8,
    seed: int = 20260902,
    progress_callback: Any = None,
) -> dict[str, Any]:
    """Execute synthetic batch recovery benchmark programmatically."""
    if not settings.gemini_api_key:
        raise ValueError("GEMINI_API_KEY is required to run the batch benchmark.")

    cases = generate_cases(n, seed)
    sem = asyncio.Semaphore(max(1, concurrency))
    completed_count = 0

    async def _eval_with_progress(c: SyntheticCase) -> EvaluationRow:
        nonlocal completed_count
        row = await evaluate_case(c, sem)
        completed_count += 1
        if progress_callback:
            try:
                progress_callback(completed_count, len(cases))
            except Exception:
                pass
        return row

    rows = await asyncio.gather(*(_eval_with_progress(case) for case in cases))
    summary = summarize(cases, rows, seed)
    json_path, csv_path = write_results(cases, rows, summary)
    return {
        "summary": summary,
        "json_path": str(json_path),
        "csv_path": str(csv_path),
    }


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=100, help="Number of synthetic cases")
    parser.add_argument("--seed", type=int, default=20260902)
    parser.add_argument("--concurrency", type=int, default=8)
    args = parser.parse_args()
    if args.n < 1:
        raise SystemExit("--n must be >= 1")
    if not settings.gemini_api_key:
        raise SystemExit("GEMINI_API_KEY is required to run the batch benchmark.")

    print(f"Running synthetic recovery evaluation for {args.n} cases (concurrency={args.concurrency})...")
    res = await run_batch_evaluation(
        n=args.n,
        concurrency=args.concurrency,
        seed=args.seed,
        progress_callback=lambda curr, total: print(f"  Evaluated: {curr}/{total} cases", end="\r", flush=True) if curr % 10 == 0 or curr == total else None
    )
    print("\n")
    print(json.dumps(res["summary"], indent=2))
    print(f"\nJSON: {res['json_path']}")
    print(f"CSV:  {res['csv_path']}")
    if res["summary"]["api_errors"]:
        print(
            f"\nWARNING: {res['summary']['api_errors']} API/model calls failed. "
            "Those rows are excluded from decision metrics."
        )


if __name__ == "__main__":
    asyncio.run(main())
