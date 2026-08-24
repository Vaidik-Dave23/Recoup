"""Integration tests for business state transitions, data derivation, enums, and merchant isolation.

Unlike full_e2e_smoke, this tests the exact state changes in the database and ensures business outcomes are strictly correct.
"""

import asyncio
from uuid import uuid4

import httpx
from sqlalchemy import select, delete

from app.db.database import AsyncSessionLocal
from app.db.models.merchant import Merchant
from app.db.models.payment import Payment
from app.db.models.order import Order
from app.db.models.enums import PaymentStatus, OrderStatus, RecoveryCaseStatus, RecoveryStage
from app.main import app

PREFIX = "bizstate"
TEST_ACCOUNT_PASSWORD = "BizStateTest!2026"


async def call(client, method, path, expected, headers=None, json=None):
    response = await client.request(method, path, headers=headers, json=json)
    assert response.status_code == expected, f"{method} {path}: expected {expected}, got {response.status_code}: {response.text}"
    return response.json() if response.content else None


async def cleanup() -> None:
    async with AsyncSessionLocal() as session:
        await session.execute(
            delete(Merchant).where(Merchant.email.like(f"{PREFIX}-%@example.com"))
        )
        await session.commit()


async def register(client, tag: str, suffix: str) -> tuple[dict, dict]:
    email = f"{PREFIX}-{tag}-{suffix}@example.com"
    registered = await call(
        client, "POST", "/auth/register", 201,
        json={
            "name": f"BIZ {tag.upper()}",
            "email": email,
            "password": TEST_ACCOUNT_PASSWORD,
            "business_name": f"BIZ {tag.upper()} {suffix}",
        },
    )
    headers = {"Authorization": f"Bearer {registered['access_token']}"}
    return registered, headers


async def main() -> None:
    await cleanup()
    suffix = uuid4().hex[:10]
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    
    try:
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            print("\n=== 1. Register two isolation merchants (A and B) ===")
            merchant_a, headers_a = await register(client, "a", suffix)
            merchant_b, headers_b = await register(client, "b", suffix)
            
            merchant_a_id = merchant_a["user"]["merchant_id"]
            merchant_b_id = merchant_b["user"]["merchant_id"]

            print("\n=== 2. Test Failed Payment creation & status lifecycle ===")
            order_a = await call(
                client, "POST", "/orders", 201, headers_a,
                json={"order_id": f"ORD-A-{suffix}", "amount": 5000, "currency": "INR", "customer_email": "cust@example.com"},
            )
            
            # Create a FAILED payment
            payment_failed = await call(
                client, "POST", "/payments", 201, headers_a,
                json={
                    "order_id": order_a["order_id"],
                    "amount": 5000,
                    "currency": "INR",
                    "payment_method": "card",
                    "transaction_id": f"txn-failed-{suffix}",
                    "status": "failed",
                    "failure_reason": "card declined",
                }
            )
            assert payment_failed["status"] == "failed", f"Expected failed payment, got {payment_failed['status']}"
            
            # Verify status in database
            async with AsyncSessionLocal() as session:
                db_payment = await session.get(Payment, uuid4().UUID(payment_failed["id"]) if hasattr(uuid4(), "UUID") else payment_failed["id"])
                assert db_payment.status == PaymentStatus.FAILED, f"Expected FAILED enum, got {db_payment.status}"
                assert db_payment.failure_reason == "card declined"

            print("\n=== 3. Test Recovery Case authoritative derivation ===")
            # Omit case_type, failure_reason, amount_at_risk, currency and ensure they are derived from Payment
            case_derived = await call(
                client, "POST", "/recovery-cases", 201, headers_a,
                json={
                    "payment_id": payment_failed["id"],
                }
            )
            assert case_derived["amount_at_risk"] == 5000
            assert case_derived["currency"] == "INR"
            assert case_derived["failure_reason"] == "card declined"
            assert case_derived["case_type"] == "payment_failed"
            assert case_derived["status"] == "in_progress"

            print("\n=== 4. Test Case creation reject inconsistent data ===")
            # Try to pass mismatched amount
            response = await client.request(
                "POST", "/recovery-cases", headers=headers_a,
                json={
                    "payment_id": payment_failed["id"],
                    "amount_at_risk": 99999,  # Mismatched amount
                }
            )
            assert response.status_code == 404 or response.status_code == 400, f"Expected rejection, got {response.status_code}"
            
            # Try to pass mismatched currency
            response = await client.request(
                "POST", "/recovery-cases", headers=headers_a,
                json={
                    "payment_id": payment_failed["id"],
                    "currency": "USD",  # Mismatched currency
                }
            )
            assert response.status_code == 404 or response.status_code == 400, f"Expected rejection, got {response.status_code}"

            print("\n=== 5. Test Case creation reject already SUCCEEDED payment ===")
            order_succeed = await call(
                client, "POST", "/orders", 201, headers_a,
                json={"order_id": f"ORD-SUCCEED-{suffix}", "amount": 2500, "currency": "INR", "customer_email": "cust2@example.com"},
            )
            payment_succeeded = await call(
                client, "POST", "/payments", 201, headers_a,
                json={
                    "order_id": order_succeed["order_id"],
                    "amount": 2500,
                    "currency": "INR",
                    "payment_method": "card",
                    "transaction_id": f"txn-succeed-{suffix}",
                    "status": "succeeded",
                }
            )
            response = await client.request(
                "POST", "/recovery-cases", headers=headers_a,
                json={
                    "payment_id": payment_succeeded["id"],
                }
            )
            assert response.status_code == 400 or response.status_code == 404, f"Expected rejection, got {response.status_code}"

            print("\n=== 6. Test Successful Recovery status propagation (enum-validated) ===")
            # Create an action for case_derived
            action = await call(
                client, "POST", "/recovery-actions", 201, headers_a,
                json={
                    "case_id": case_derived["id"],
                    "action_type": "email",
                    "channel": "email",
                    "subject": "outreach",
                    "message_body": "pay here",
                }
            )
            
            # Record a successful outcome
            outcome = await call(
                client, "POST", "/recovery-outcomes", 201, headers_a,
                json={
                    "case_id": case_derived["id"],
                    "action_id": action["id"],
                    "recovered": True,
                    "amount_recovered": 5000,
                    "notes": "customer paid manually",
                }
            )
            
            # Verify Payment is SUCCEEDED and Order is PAID in database
            async with AsyncSessionLocal() as session:
                db_p = await session.scalar(select(Payment).where(Payment.id == db_payment.id))
                db_o = await session.scalar(select(Order).where(Order.id == db_p.order_id))
                assert db_p.status == PaymentStatus.SUCCEEDED, f"Expected payment status succeeded, got {db_p.status}"
                assert db_o.status == OrderStatus.PAID, f"Expected order status paid, got {db_o.status}"

            print("\n=== 7. Test duplicate successful recovery outcome protection ===")
            # Try to add another successful outcome to the same case
            response = await client.request(
                "POST", "/recovery-outcomes", headers=headers_a,
                json={
                    "case_id": case_derived["id"],
                    "action_id": action["id"],
                    "recovered": True,
                    "amount_recovered": 5000,
                    "notes": "duplicate",
                }
            )
            assert response.status_code == 400, f"Expected 400 for duplicate outcome, got {response.status_code}: {response.text}"

            print("\n=== 8. Test Retry Loop check & Retry Exhaustion ===")
            # Create another case for testing retries
            order_retry = await call(
                client, "POST", "/orders", 201, headers_a,
                json={"order_id": f"ORD-RETRY-{suffix}", "amount": 3000, "currency": "INR"},
            )
            payment_retry = await call(
                client, "POST", "/payments", 201, headers_a,
                json={
                    "order_id": order_retry["order_id"],
                    "amount": 3000,
                    "currency": "INR",
                    "payment_method": "card",
                    "transaction_id": f"txn-retry-{suffix}",
                    "status": "failed",
                }
            )
            case_retry = await call(
                client, "POST", "/recovery-cases", 201, headers_a,
                json={"payment_id": payment_retry["id"]},
            )
            
            # Record failed outcome 1
            action1 = await call(
                client, "POST", "/recovery-actions", 201, headers_a,
                json={"case_id": case_retry["id"], "action_type": "email", "channel": "email", "subject": "a1", "message_body": "m1"},
            )
            await call(
                client, "POST", "/recovery-outcomes", 201, headers_a,
                json={"case_id": case_retry["id"], "action_id": action1["id"], "recovered": False, "amount_recovered": 0},
            )
            
            # Check case attempt count is 1 and status is in_progress
            c1 = await call(client, "GET", f"/recovery-cases/{case_retry['id']}", 200, headers_a)
            assert c1["attempt_count"] == 1
            assert c1["status"] == "in_progress"

            # Record failed outcome 2
            action2 = await call(
                client, "POST", "/recovery-actions", 201, headers_a,
                json={"case_id": case_retry["id"], "action_type": "email", "channel": "email", "subject": "a2", "message_body": "m2"},
            )
            await call(
                client, "POST", "/recovery-outcomes", 201, headers_a,
                json={"case_id": case_retry["id"], "action_id": action2["id"], "recovered": False, "amount_recovered": 0},
            )
            c2 = await call(client, "GET", f"/recovery-cases/{case_retry['id']}", 200, headers_a)
            assert c2["attempt_count"] == 2
            assert c2["status"] == "in_progress"

            # Record failed outcome 3 -> exhaustion limit (max attempts = 3)
            action3 = await call(
                client, "POST", "/recovery-actions", 201, headers_a,
                json={"case_id": case_retry["id"], "action_type": "email", "channel": "email", "subject": "a3", "message_body": "m3"},
            )
            await call(
                client, "POST", "/recovery-outcomes", 201, headers_a,
                json={"case_id": case_retry["id"], "action_id": action3["id"], "recovered": False, "amount_recovered": 0},
            )
            c3 = await call(client, "GET", f"/recovery-cases/{case_retry['id']}", 200, headers_a)
            assert c3["attempt_count"] == 3
            assert c3["status"] == "escalated"  # Escalated after 3 attempts

            print("\n=== 9. Test Closed/Recovered Case Resume does nothing ===")
            # Resume on case_derived (already recovered)
            resumed_outcome = await call(
                client, "POST", f"/recovery-cases/{case_derived['id']}/agent/resume", 200, headers_a,
            )
            assert resumed_outcome is None, f"Expected None on recovered case resume, got {resumed_outcome}"

            print("\n=== 10. Test Merchant Isolation ===")
            # Merchant B must not be able to get A's payments
            response = await client.request("GET", f"/payments/{payment_failed['id']}", headers=headers_b)
            assert response.status_code == 404
            
            # Merchant B must not be able to get A's cases
            response = await client.request("GET", f"/recovery-cases/{case_derived['id']}", headers=headers_b)
            assert response.status_code == 404
            
            # Merchant B must not be able to get A's outcomes
            response = await client.request("GET", f"/recovery-outcomes/{outcome['id']}", headers=headers_b)
            assert response.status_code == 404

            # Merchant B must not be able to get A's actions
            response = await client.request("GET", f"/recovery-actions/{action['id']}", headers=headers_b)
            assert response.status_code == 404

            print("\nAll Business State Transition and Validation Checks PASSED!")
    finally:
        await cleanup()


if __name__ == "__main__":
    asyncio.run(main())
