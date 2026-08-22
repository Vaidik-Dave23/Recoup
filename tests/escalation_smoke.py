"""Focused API smoke test for recovery outcomes and escalations."""

import asyncio
from uuid import uuid4

import httpx
from sqlalchemy import delete

from app.db.database import AsyncSessionLocal
from app.db.models.merchant import Merchant
from app.main import app


async def call(client, method, path, expected, headers=None, json=None):
    print(f"{method} {path}", flush=True)
    response = await client.request(method, path, headers=headers, json=json)
    assert response.status_code == expected, response.text
    return response.json() if response.content else None


async def cleanup() -> None:
    async with AsyncSessionLocal() as session:
        await session.execute(
            delete(Merchant).where(Merchant.email.like("smoke-%@example.com"))
        )
        await session.commit()


async def main() -> None:
    await cleanup()
    suffix = uuid4().hex[:12]
    email = f"smoke-{suffix}@example.com"
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    try:
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            registered = await call(
                client, "POST", "/auth/register", 201,
                json={"name": "Smoke Test", "email": email, "password": "SmokeTestPass123!", "business_name": f"Smoke {suffix}"},
            )
            headers = {"Authorization": f"Bearer {registered['access_token']}"}
            order = await call(
                client, "POST", "/orders", 201, headers,
                {"order_id": f"ORDER-{suffix}", "amount": 49000, "currency": "INR"},
            )
            payment = await call(
                client, "POST", "/payments", 201, headers,
                {"order_id": order["order_id"], "amount": 49000, "currency": "INR", "payment_method": "upi", "transaction_id": f"TXN-{suffix}"},
            )
            case = await call(
                client, "POST", "/recovery-cases", 201, headers,
                {"payment_id": payment["id"], "case_type": "payment_failed", "failure_reason": "Smoke test", "amount_at_risk": 49000, "currency": "INR"},
            )
            action = await call(
                client, "POST", "/recovery-actions", 201, headers,
                {"case_id": case["id"], "action_type": "email", "channel": "email", "subject": "Recover", "message_body": "Retry"},
            )
            outcome = await call(
                client, "POST", "/recovery-outcomes", 201, headers,
                {"case_id": case["id"], "action_id": action["id"], "recovered": True, "amount_recovered": 49000},
            )
            await call(client, "GET", f"/recovery-outcomes/case/{case['id']}", 200, headers)
            await call(client, "GET", f"/recovery-outcomes/{outcome['id']}", 200, headers)
            escalation = await call(
                client, "POST", "/escalations", 201, headers,
                {"case_id": case["id"], "reason": "Smoke test", "priority": "high", "notes": "Needs review"},
            )
            await call(client, "GET", "/escalations", 200, headers)
            await call(client, "GET", f"/escalations/case/{case['id']}", 200, headers)
            await call(client, "GET", f"/escalations/{escalation['id']}", 200, headers)
            updated = await call(
                client, "PATCH", f"/escalations/{escalation['id']}", 200, headers,
                {"status": "resolved", "priority": "low", "notes": "Resolved"},
            )
            assert updated["status"] == "resolved"
            assert updated["priority"] == "low"
            assert updated["notes"] == "Resolved"
            print("Outcome and escalation endpoint smoke checks passed.")
    finally:
        await cleanup()


if __name__ == "__main__":
    asyncio.run(main())
