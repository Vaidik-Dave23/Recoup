"""Authenticated end-to-end smoke test for every Recoup API route.

The test uses a uniquely named merchant and removes it (and all cascaded test
records) when it finishes, including after a failure.
"""

import asyncio
from uuid import uuid4

import httpx
from sqlalchemy import select

from app.db.database import AsyncSessionLocal
from app.db.models.merchant import Merchant
from app.main import app


async def request(
    client: httpx.AsyncClient,
    method: str,
    path: str,
    *,
    expected: int,
    headers: dict[str, str] | None = None,
    payload: dict | None = None,
) -> dict | list | None:
    print(f"{method} {path}", flush=True)
    response = await client.request(
        method,
        path,
        headers=headers,
        json=payload,
    )
    if response.status_code != expected:
        raise AssertionError(
            f"{method} {path}: expected {expected}, got "
            f"{response.status_code}: {response.text}"
        )
    return response.json() if response.content else None


async def delete_test_merchant(email: str) -> None:
    async with AsyncSessionLocal() as session:
        merchant = await session.scalar(
            select(Merchant).where(Merchant.email == email)
        )
        if merchant is not None:
            await session.delete(merchant)
            await session.commit()


async def main() -> None:
    suffix = uuid4().hex[:12]
    email = f"smoke-{suffix}@example.com"
    password = "SmokeTestPass123!"
    merchant_id: str | None = None

    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    try:
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            registered = await request(
                client,
                "POST",
                "/auth/register",
                expected=201,
                payload={
                    "name": "Smoke Test",
                    "email": email,
                    "password": password,
                    "business_name": f"Smoke {suffix}",
                },
            )
            assert isinstance(registered, dict)
            merchant_id = registered["user"]["merchant_id"]
            headers = {"Authorization": f"Bearer {registered['access_token']}"}

            await request(
                client,
                "POST",
                "/auth/login",
                expected=200,
                payload={"email": email, "password": password},
            )
            await request(client, "GET", "/auth/me", expected=200, headers=headers)

            order = await request(
                client,
                "POST",
                "/orders",
                expected=201,
                headers=headers,
                payload={
                    "order_id": f"ORDER-{suffix}",
                    "amount": 49000,
                    "currency": "INR",
                },
            )
            assert isinstance(order, dict)
            order_id = order["id"]
            await request(client, "GET", "/orders", expected=200, headers=headers)
            await request(client, "GET", f"/orders/{order_id}", expected=200, headers=headers)
            await request(
                client,
                "PATCH",
                f"/orders/{order_id}",
                expected=200,
                headers=headers,
                payload={"status": "paid"},
            )

            deletable_order = await request(
                client,
                "POST",
                "/orders",
                expected=201,
                headers=headers,
                payload={
                    "order_id": f"DELETE-{suffix}",
                    "amount": 100,
                    "currency": "INR",
                },
            )
            assert isinstance(deletable_order, dict)
            await request(
                client,
                "DELETE",
                f"/orders/{deletable_order['id']}",
                expected=204,
                headers=headers,
            )

            payment = await request(
                client,
                "POST",
                "/payments",
                expected=201,
                headers=headers,
                payload={
                    "order_id": f"ORDER-{suffix}",
                    "amount": 49000,
                    "currency": "INR",
                    "payment_method": "upi",
                    "transaction_id": f"TXN-{suffix}",
                },
            )
            assert isinstance(payment, dict)
            payment_id = payment["id"]
            await request(client, "GET", "/payments", expected=200, headers=headers)
            await request(client, "GET", f"/payments/{payment_id}", expected=200, headers=headers)

            case = await request(
                client,
                "POST",
                "/recovery-cases",
                expected=201,
                headers=headers,
                payload={
                    "payment_id": payment_id,
                    "case_type": "payment_failed",
                    "failure_reason": "Smoke test failure",
                    "amount_at_risk": 49000,
                    "currency": "INR",
                },
            )
            assert isinstance(case, dict)
            case_id = case["id"]
            await request(client, "GET", "/recovery-cases", expected=200, headers=headers)
            await request(client, "GET", f"/recovery-cases/{case_id}", expected=200, headers=headers)
            await request(
                client,
                "PATCH",
                f"/recovery-cases/{case_id}",
                expected=200,
                headers=headers,
                payload={"stage": "triage", "financial_impact": 0},
            )

            investigation = await request(
                client,
                "POST",
                "/ai-investigations",
                expected=201,
                headers=headers,
                payload={
                    "case_id": case_id,
                    "node_name": "triage",
                    "model_name": "smoke-test",
                    "input_payload": {"source": "smoke"},
                    "response_payload": {"recommendation": "email"},
                    "confidence": "0.9000",
                },
            )
            assert isinstance(investigation, dict)
            investigation_id = investigation["id"]
            await request(
                client,
                "GET",
                f"/ai-investigations/case/{case_id}",
                expected=200,
                headers=headers,
            )
            await request(
                client,
                "GET",
                f"/ai-investigations/{investigation_id}",
                expected=200,
                headers=headers,
            )

            action = await request(
                client,
                "POST",
                "/recovery-actions",
                expected=201,
                headers=headers,
                payload={
                    "case_id": case_id,
                    "investigation_id": investigation_id,
                    "action_type": "email",
                    "channel": "email",
                    "subject": "Recover your payment",
                    "message_body": "Please retry.",
                },
            )
            assert isinstance(action, dict)
            action_id = action["id"]
            await request(
                client,
                "GET",
                f"/recovery-actions/case/{case_id}",
                expected=200,
                headers=headers,
            )
            await request(
                client,
                "GET",
                f"/recovery-actions/{action_id}",
                expected=200,
                headers=headers,
            )

            outcome = await request(
                client,
                "POST",
                "/recovery-outcomes",
                expected=201,
                headers=headers,
                payload={
                    "case_id": case_id,
                    "action_id": action_id,
                    "recovered": True,
                    "amount_recovered": 49000,
                    "notes": "Recovered during smoke test",
                },
            )
            assert isinstance(outcome, dict)
            outcome_id = outcome["id"]
            await request(
                client,
                "GET",
                f"/recovery-outcomes/case/{case_id}",
                expected=200,
                headers=headers,
            )
            await request(
                client,
                "GET",
                f"/recovery-outcomes/{outcome_id}",
                expected=200,
                headers=headers,
            )

            escalation = await request(
                client,
                "POST",
                "/escalations",
                expected=201,
                headers=headers,
                payload={
                    "case_id": case_id,
                    "reason": "Smoke test escalation",
                    "priority": "high",
                    "notes": "Escalation smoke test",
                },
            )
            assert isinstance(escalation, dict)
            escalation_id = escalation["id"]
            await request(client, "GET", "/escalations", expected=200, headers=headers)
            await request(
                client,
                "GET",
                f"/escalations/case/{case_id}",
                expected=200,
                headers=headers,
            )
            await request(
                client,
                "GET",
                f"/escalations/{escalation_id}",
                expected=200,
                headers=headers,
            )
            await request(
                client,
                "PATCH",
                f"/escalations/{escalation_id}",
                expected=200,
                headers=headers,
                payload={"status": "resolved", "priority": "low", "notes": "Resolved"},
            )

            print("All 29 authenticated endpoint smoke checks passed.")
    finally:
        if merchant_id is not None:
            await delete_test_merchant(email)


if __name__ == "__main__":
    asyncio.run(main())
