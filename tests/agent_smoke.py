"""Smoke-test the Gemini recovery-agent routes without an API key.

Without GEMINI_API_KEY, the graph must record its Gemini failures and safely
escalate the case instead of returning a server error.
"""

import asyncio
from uuid import uuid4

import httpx

from app.main import app
from app.core.config import settings
from tests.escalation_smoke import call, cleanup


async def main() -> None:
    await cleanup()
    suffix = uuid4().hex[:12]
    email = f"smoke-{suffix}@example.com"
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    try:
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            registered = await call(
                client, "POST", "/auth/register", 201,
                json={
                    "name": "Agent Smoke",
                    "email": email,
                    "password": "SmokeTestPass123!",
                    "business_name": f"Agent Smoke {suffix}",
                },
            )
            headers = {"Authorization": f"Bearer {registered['access_token']}"}
            order = await call(
                client, "POST", "/orders", 201, headers,
                {"order_id": f"ORDER-{suffix}", "amount": 49000, "currency": "INR"},
            )
            payment = await call(
                client, "POST", "/payments", 201, headers,
                {
                    "order_id": order["order_id"], "amount": 49000,
                    "currency": "INR", "payment_method": "upi",
                    "transaction_id": f"TXN-{suffix}",
                },
            )
            case = await call(
                client, "POST", "/recovery-cases", 201, headers,
                {
                    "payment_id": payment["id"], "case_type": "payment_failed",
                    "failure_reason": "bank timeout", "amount_at_risk": 49000,
                    "currency": "INR",
                },
            )
            result = await call(
                client, "POST", f"/recovery-cases/{case['id']}/agent/run", 200, headers,
            )
            investigations = await call(
                client, "GET", f"/ai-investigations/case/{case['id']}", 200, headers,
            )
            assert len(investigations) >= 2

            if not settings.gemini_api_key:
                assert result["escalated"] is True
                assert result["escalation_id"]
                resumed = await call(
                    client, "POST", f"/recovery-cases/{case['id']}/agent/resume", 200, headers,
                )
                assert resumed["escalation_id"] == result["escalation_id"]
                print("Gemini fallback and resume smoke checks passed.")
            elif result["escalated"]:
                assert result["escalation_id"]
                print("Live Gemini safely escalated the case.")
            else:
                assert result["action_id"]
                action = await call(
                    client, "GET", f"/recovery-actions/{result['action_id']}", 200, headers,
                )
                assert action["status"] == "failed"
                print("Live Gemini generated and persisted a recovery action.")
    finally:
        await cleanup()


if __name__ == "__main__":
    asyncio.run(main())
