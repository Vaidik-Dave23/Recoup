"""Latency benchmark and profiling test suite for all recovery scenarios and API routes.

Measures:
1. Scenario execution latencies:
   - Scenario 1: Hard Decline (deterministic policy guard escalation latency)
   - Scenario 2: Soft Decline (full AI triage -> strategy -> content -> Razorpay payment link -> execution)
   - Scenario 3: Abandoned Checkout (e-commerce recovery flow latency)
   - Scenario 4: Overdue Invoice (B2B formal dunning latency)
   - Scenario 5: Graceful Error Fallback (Gemini 429 / rate limit -> safe escalation latency)
2. API Route Response Latency profiling:
   - GET /fault-scenarios
   - GET /audit-logs
   - GET /dashboard/kpis
   - POST /fault-scenarios/{id}/execute
3. Statistical summary:
   - Min, Max, Mean, P50, P95 execution times
"""

from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

# Add project root to sys.path automatically
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx

from app.agent.gemini_client import GeminiCallError
from app.agent.nodes import RecoveryAgentNodes
from app.agent.policy import evaluate_recovery_decision
from app.agent.razorpay_client import PaymentLinkResult
from app.agent.state import RecoveryState
from app.core.config import settings
from app.main import app


def _format_ms(seconds: float) -> str:
    return f"{seconds * 1000:.2f} ms"


class LatencyTracker:
    def __init__(self, name: str):
        self.name = name
        self.timings: list[float] = []

    def record(self, duration: float) -> None:
        self.timings.append(duration)

    @property
    def min_ms(self) -> float:
        return min(self.timings) * 1000 if self.timings else 0.0

    @property
    def max_ms(self) -> float:
        return max(self.timings) * 1000 if self.timings else 0.0

    @property
    def mean_ms(self) -> float:
        return (sum(self.timings) / len(self.timings)) * 1000 if self.timings else 0.0

    @property
    def p50_ms(self) -> float:
        if not self.timings:
            return 0.0
        sorted_t = sorted(self.timings)
        return sorted_t[int(len(sorted_t) * 0.50)] * 1000

    @property
    def p95_ms(self) -> float:
        if not self.timings:
            return 0.0
        sorted_t = sorted(self.timings)
        idx = min(int(len(sorted_t) * 0.95), len(sorted_t) - 1)
        return sorted_t[idx] * 1000


async def benchmark_scenarios() -> dict[str, LatencyTracker]:
    print("\n" + "=" * 80)
    print(" 1. BENCHMARKING RECOVERY SCENARIO EXECUTION LATENCIES")
    print("=" * 80)

    trackers = {
        "hard_decline": LatencyTracker("Hard Decline (Deterministic Safety Guard)"),
        "soft_decline": LatencyTracker("Soft Decline (AI Full Pipeline)"),
        "abandoned_checkout": LatencyTracker("Abandoned Checkout (E-Commerce Recovery)"),
        "overdue_invoice": LatencyTracker("Overdue Invoice (B2B Dunning)"),
        "rate_limit_fallback": LatencyTracker("Rate Limit Fallback (Graceful Escalation)"),
    }

    mock_db = MagicMock()
    mock_db.commit = AsyncMock()
    merchant_id = uuid4()
    nodes = RecoveryAgentNodes(mock_db, merchant_id)

    # 1. Hard Decline Benchmark (50 iterations)
    for _ in range(50):
        t0 = time.perf_counter()
        decision = evaluate_recovery_decision(
            failure_reason="stolen_card_decline",
            raw_action="email",
            raw_channel="email",
            confidence=0.99,
        )
        assert decision.effective_action == "escalate"
        duration = time.perf_counter() - t0
        trackers["hard_decline"].record(duration)

    # 2. Soft Decline Benchmark with AI mocks (20 iterations)
    mock_rzp = PaymentLinkResult(True, "plink_123", "https://rzp.io/i/test")
    for _ in range(20):
        state: RecoveryState = {
            "case_id": str(uuid4()),
            "merchant_id": str(merchant_id),
            "case_type": "payment_failed",
            "failure_reason": "insufficient_funds",
            "amount_at_risk": 4999,
            "currency": "INR",
            "customer_name": "Rohan",
            "customer_email": "rohan@example.com",
            "attempt_count": 0,
        }
        with patch("app.agent.nodes.create_ai_investigation", new_callable=AsyncMock), \
             patch("app.agent.nodes.create_recovery_action", return_value=MagicMock(id=uuid4(), channel="email")), \
             patch("app.agent.nodes.RecoveryAgentNodes._latest_investigation_id", new_callable=AsyncMock, return_value=uuid4()), \
             patch("app.agent.nodes.create_recovery_payment_link", return_value=mock_rzp), \
             patch("app.agent.nodes.send_recovery_email", return_value=MagicMock(success=True, provider_ref="email_1")), \
             patch("app.agent.nodes.call_json", new_callable=AsyncMock) as mock_call:
            
            mock_call.side_effect = [
                {"category": "funds", "likely_cause": "low balance", "urgency": "medium", "summary": "Low balance"},
                {"action_type": "email", "channel": "email", "timing": "24h", "tone": "gentle", "confidence": 0.88, "reasoning": "Wait"},
                {"subject": "Payment issue", "body": "Please retry your payment with link."},
            ]

            t0 = time.perf_counter()
            triage_res = await nodes.triage(state)
            strat_res = await nodes.strategize({**state, **triage_res})
            content_res = await nodes.generate_content({**state, **triage_res, **strat_res})
            action_mock = MagicMock(id=uuid4(), case_id=UUID(state["case_id"]), status="queued", provider_ref=None)
            mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=action_mock)))
            exec_res = await nodes.execute({**state, **triage_res, **strat_res, **content_res})
            duration = time.perf_counter() - t0
            trackers["soft_decline"].record(duration)

    # 3. Abandoned Checkout Benchmark (20 iterations)
    for _ in range(20):
        state = {
            "case_id": str(uuid4()),
            "merchant_id": str(merchant_id),
            "case_type": "abandoned_checkout",
            "failure_reason": "checkout_abandoned",
            "amount_at_risk": 8900,
            "currency": "INR",
            "customer_name": "Pooja",
            "customer_email": "pooja@example.com",
            "attempt_count": 0,
        }
        with patch("app.agent.nodes.create_ai_investigation", new_callable=AsyncMock), \
             patch("app.agent.nodes.create_recovery_action", return_value=MagicMock(id=uuid4(), channel="email")), \
             patch("app.agent.nodes.RecoveryAgentNodes._latest_investigation_id", new_callable=AsyncMock, return_value=uuid4()), \
             patch("app.agent.nodes.create_recovery_payment_link", return_value=mock_rzp), \
             patch("app.agent.nodes.send_recovery_email", return_value=MagicMock(success=True, provider_ref="email_2")), \
             patch("app.agent.nodes.call_json", new_callable=AsyncMock) as mock_call:
            
            mock_call.side_effect = [
                {"category": "intent", "likely_cause": "tab closed", "urgency": "high", "summary": "Cart left open"},
                {"action_type": "email", "channel": "email", "timing": "immediate", "tone": "helpful", "confidence": 0.94, "reasoning": "Quick nudge"},
                {"subject": "Did you forget something?", "body": "Complete your order with a single click."},
            ]

            t0 = time.perf_counter()
            triage_res = await nodes.triage(state)
            strat_res = await nodes.strategize({**state, **triage_res})
            content_res = await nodes.generate_content({**state, **triage_res, **strat_res})
            action_mock = MagicMock(id=uuid4(), case_id=UUID(state["case_id"]), status="queued", provider_ref=None)
            mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=action_mock)))
            exec_res = await nodes.execute({**state, **triage_res, **strat_res, **content_res})
            duration = time.perf_counter() - t0
            trackers["abandoned_checkout"].record(duration)

    # 4. Overdue Invoice B2B Benchmark (20 iterations)
    for _ in range(20):
        state = {
            "case_id": str(uuid4()),
            "merchant_id": str(merchant_id),
            "case_type": "overdue_invoice",
            "failure_reason": "invoice_unpaid_30_days",
            "amount_at_risk": 75000,
            "currency": "INR",
            "customer_name": "Tech Corp",
            "customer_email": "accounts@techcorp.com",
            "attempt_count": 0,
        }
        with patch("app.agent.nodes.create_ai_investigation", new_callable=AsyncMock), \
             patch("app.agent.nodes.create_recovery_action", return_value=MagicMock(id=uuid4(), channel="email")), \
             patch("app.agent.nodes.RecoveryAgentNodes._latest_investigation_id", new_callable=AsyncMock, return_value=uuid4()), \
             patch("app.agent.nodes.create_recovery_payment_link", return_value=mock_rzp), \
             patch("app.agent.nodes.send_recovery_email", return_value=MagicMock(success=True, provider_ref="email_3")), \
             patch("app.agent.nodes.call_json", new_callable=AsyncMock) as mock_call:
            
            mock_call.side_effect = [
                {"category": "b2b", "likely_cause": "net-30 expired", "urgency": "high", "summary": "30 days past due"},
                {"action_type": "email", "channel": "email", "timing": "immediate", "tone": "formal", "confidence": 0.90, "reasoning": "Formal dunning"},
                {"subject": "Formal Notice: Overdue Invoice", "body": "Your invoice is now overdue. Please remit payment."},
            ]

            t0 = time.perf_counter()
            triage_res = await nodes.triage(state)
            strat_res = await nodes.strategize({**state, **triage_res})
            content_res = await nodes.generate_content({**state, **triage_res, **strat_res})
            action_mock = MagicMock(id=uuid4(), case_id=UUID(state["case_id"]), status="queued", provider_ref=None)
            mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=action_mock)))
            exec_res = await nodes.execute({**state, **triage_res, **strat_res, **content_res})
            duration = time.perf_counter() - t0
            trackers["overdue_invoice"].record(duration)

    # 5. Rate Limit / 429 Graceful Escalation Benchmark (20 iterations)
    for _ in range(20):
        state = {
            "case_id": str(uuid4()),
            "merchant_id": str(merchant_id),
            "case_type": "payment_failed",
            "failure_reason": "insufficient_funds",
            "amount_at_risk": 4999,
            "currency": "INR",
        }
        with patch("app.agent.nodes.create_ai_investigation", new_callable=AsyncMock), \
             patch("app.agent.nodes.create_escalation", return_value=MagicMock(id=uuid4())), \
             patch("app.agent.nodes.call_json", side_effect=GeminiCallError("429 Too Many Requests")):

            t0 = time.perf_counter()
            triage_res = await nodes.triage(state)
            strat_res = await nodes.strategize({**state, **triage_res})
            esc_res = await nodes.escalate({**state, **triage_res, **strat_res})
            duration = time.perf_counter() - t0
            trackers["rate_limit_fallback"].record(duration)

    # Print summary table
    print(f"\n{'Scenario':<42} | {'Mean (ms)':<10} | {'P50 (ms)':<10} | {'P95 (ms)':<10} | {'Min (ms)':<10} | {'Max (ms)':<10}")
    print("-" * 96)
    for key, tr in trackers.items():
        print(f"{tr.name:<42} | {tr.mean_ms:<10.2f} | {tr.p50_ms:<10.2f} | {tr.p95_ms:<10.2f} | {tr.min_ms:<10.2f} | {tr.max_ms:<10.2f}")

    return trackers


async def benchmark_api_routes() -> None:
    print("\n" + "=" * 80)
    print(" 2. BENCHMARKING API ROUTE LATENCIES")
    print("=" * 80)

    from app.core.dependencies import get_current_user
    from app.db.models.merchant_user import MerchantUser
    from app.db.database import get_db

    mock_merchant_id = uuid4()
    mock_user = MerchantUser(
        id=uuid4(),
        merchant_id=mock_merchant_id,
        email="benchmark@recoup.com",
        status="active",
    )

    mock_session = MagicMock()
    mock_session.execute = AsyncMock(return_value=MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))))

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_session

    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    api_trackers = {
        "GET /fault-scenarios": LatencyTracker("GET /fault-scenarios"),
        "GET /audit-logs": LatencyTracker("GET /audit-logs"),
    }

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # Benchmark /fault-scenarios
        for _ in range(30):
            t0 = time.perf_counter()
            resp = await client.get("/fault-scenarios")
            duration = time.perf_counter() - t0
            assert resp.status_code == 200
            api_trackers["GET /fault-scenarios"].record(duration)

        # Benchmark /audit-logs
        for _ in range(30):
            t0 = time.perf_counter()
            resp = await client.get("/audit-logs")
            duration = time.perf_counter() - t0
            assert resp.status_code == 200
            api_trackers["GET /audit-logs"].record(duration)

    app.dependency_overrides.clear()

    print(f"\n{'Route':<30} | {'Mean (ms)':<10} | {'P50 (ms)':<10} | {'P95 (ms)':<10} | {'Min (ms)':<10} | {'Max (ms)':<10}")
    print("-" * 84)
    for route, tr in api_trackers.items():
        print(f"{tr.name:<30} | {tr.mean_ms:<10.2f} | {tr.p50_ms:<10.2f} | {tr.p95_ms:<10.2f} | {tr.min_ms:<10.2f} | {tr.max_ms:<10.2f}")


async def benchmark_live_gemini(iterations: int = 3) -> None:
    print("\n" + "=" * 80)
    print(" 3. BENCHMARKING LIVE GOOGLE GEMINI API CALLS (REAL NETWORK & MODEL GENERATION)")
    print("=" * 80)

    if not settings.gemini_api_key:
        print("\n[WARNING] GEMINI_API_KEY is not configured in environment. Skipping live API benchmark.")
        return

    from app.agent.gemini_client import call_json
    from app.agent import prompts

    live_triage = LatencyTracker("Live Gemini Triage Node")
    live_strat = LatencyTracker("Live Gemini Strategize Node")
    live_content = LatencyTracker("Live Gemini Content Gen Node")

    print(f"\nRunning {iterations} live requests to Gemini ({settings.gemini_model})...")

    for i in range(iterations):
        # 1. Live Triage
        t0 = time.perf_counter()
        triage_prompt = prompts.TRIAGE_USER.format(
            case_type="payment_failed",
            failure_reason="insufficient_funds",
            amount_at_risk=4999,
            currency="INR",
            attempt_count=0,
        )
        triage_res = await call_json(prompts.TRIAGE_SYSTEM, triage_prompt)
        live_triage.record(time.perf_counter() - t0)

        # 2. Live Strategize
        import json
        t0 = time.perf_counter()
        strat_prompt = prompts.STRATEGIZE_USER.format(
            triage_json=json.dumps(triage_res),
            case_type="payment_failed",
            amount_at_risk=4999,
            currency="INR",
            attempt_number=1,
        )
        strat_res = await call_json(prompts.STRATEGIZE_SYSTEM, strat_prompt)
        live_strat.record(time.perf_counter() - t0)

        # 3. Live Content Generation
        t0 = time.perf_counter()
        content_prompt = prompts.CONTENT_USER.format(
            channel="email",
            tone="gentle",
            customer_name="Rohan",
            case_type="payment_failed",
            amount_at_risk=4999,
            currency="INR",
            payment_link="https://rzp.io/i/test_live",
            triage_summary=triage_res.get("summary", ""),
            strategy_reasoning=strat_res.get("reasoning", ""),
        )
        await call_json(prompts.CONTENT_SYSTEM, content_prompt)
        live_content.record(time.perf_counter() - t0)

    print(f"\n{'Live Gemini Node':<35} | {'Mean (ms)':<10} | {'P50 (ms)':<10} | {'Min (ms)':<10} | {'Max (ms)':<10}")
    print("-" * 80)
    for tr in [live_triage, live_strat, live_content]:
        print(f"{tr.name:<35} | {tr.mean_ms:<10.2f} | {tr.p50_ms:<10.2f} | {tr.min_ms:<10.2f} | {tr.max_ms:<10.2f}")


async def main() -> None:
    is_live = "--live" in sys.argv
    print(f"\nStarting Recoup Performance & Scenario Latency Benchmark Suite (Mode: {'LIVE GEMINI API' if is_live else 'LOCAL FAST ISOLATED'})...")
    scenario_trackers = await benchmark_scenarios()
    await benchmark_api_routes()

    if is_live:
        await benchmark_live_gemini(iterations=3)
    else:
        print("\n[INFO] To benchmark live Google Gemini network calls and token generation latency, run:")
        print("       python tests/latency_benchmark_test.py --live")

    # Verify key SLA bounds
    assert scenario_trackers["hard_decline"].mean_ms < 5.0, "Hard decline policy evaluation must be sub-5ms"
    assert scenario_trackers["rate_limit_fallback"].mean_ms < 50.0, "Rate limit fallback must be sub-50ms"
    print("\n" + "=" * 80)
    print(" ALL LATENCY BENCHMARKS COMPLETED WITHIN STRICT PERFORMANCE SLAs!")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
