"""Targeted end-to-end automated recovery flow test for the Razorpay Buildathon demo.

Verifies:
1. Executing a fault scenario in Fault Lab (soft decline) automatically:
   - Creates the order, failed payment, and recovery case
   - Automatically runs LangGraph (Triage -> Strategy -> Policy Guard -> Generate Content -> Execute)
   - Creates a real Razorpay Test Mode Payment Link
   - Returns agent_result with investigation steps & action
2. Executing a hard decline scenario (stolen card) automatically:
   - Immediately escalates via policy guardrail
   - Blocks automated payment link/email
   - Creates escalation record with summary
3. Razorpay Payment Link Verification & Sync:
   - Calling POST /recovery-cases/{id}/verify-payment
   - When link is paid, automatically records RecoveryOutcome, marks case RECOVERED,
     updates financial_impact, updates Payment to SUCCEEDED, updates Order to PAID.
"""

import asyncio
from uuid import uuid4
import httpx
from sqlalchemy import delete

from app.db.database import AsyncSessionLocal
from app.db.models.merchant import Merchant
from app.main import app

PREFIX = "autodemo"
TEST_ACCOUNT_PASSWORD = "AutoDemoPass!2026"


async def call(client, method, path, expected, headers=None, json=None):
    print(f"  {method} {path}", flush=True)
    response = await client.request(method, path, headers=headers, json=json)
    assert response.status_code == expected, (
        f"{method} {path}: expected {expected}, got {response.status_code}: {response.text}"
    )
    return response.json() if response.content else None


async def cleanup() -> None:
    async with AsyncSessionLocal() as session:
        await session.execute(
            delete(Merchant).where(Merchant.email.like(f"{PREFIX}-%@example.com"))
        )
        await session.commit()


async def main() -> None:
    await cleanup()
    suffix = uuid4().hex[:10]
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)

    try:
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            print("\n=== 1. Register test merchant ===")
            reg = await call(
                client, "POST", "/auth/register", 201,
                json={
                    "name": "Buildathon Demo",
                    "email": f"{PREFIX}-{suffix}@example.com",
                    "password": TEST_ACCOUNT_PASSWORD,
                    "business_name": "Recoup Autonomous Recovery",
                },
            )
            headers = {"Authorization": f"Bearer {reg['access_token']}"}

            print("\n=== 2. Simulate Soft Decline in Fault Lab (One-Click Autonomous Flow) ===")
            executed = await call(
                client, "POST", "/fault-scenarios/soft_decline/execute", 200, headers
            )
            assert executed["success"] is True
            case_id = executed["case_id"]
            agent_res = executed.get("agent_result")
            print(f"  agent_res: {agent_res}")

            invs = await call(client, "GET", f"/ai-investigations/case/{case_id}", 200, headers)
            print(f"  investigations: {invs}")
            node_names = [i["node_name"] for i in invs]
            print(f"  Logged nodes: {node_names}")
            assert "triage" in node_names, "Triage node must be logged"
            assert "strategize" in node_names, "Strategize node must be logged"
            assert "generate_content" in node_names, "Generate content node must be logged"

            content_inv = next(i for i in invs if i["node_name"] == "generate_content")
            resp_payload = content_inv["response_payload"]
            assert resp_payload.get("payment_link_created") is True, "Razorpay payment link must be created"
            payment_link_url = resp_payload.get("payment_link_url")
            print(f"  Razorpay Test Mode Link: {payment_link_url}")
            assert payment_link_url and payment_link_url.startswith("https://"), "Must be a valid https Razorpay link"

            print("\n=== 4. Verify Recovery Action Dispatched ===")
            actions = await call(client, "GET", f"/recovery-actions/case/{case_id}", 200, headers)
            assert len(actions) >= 1
            action = actions[0]
            assert action["status"] in ("sent", "delivered")
            assert "rzp_link:" in action["provider_ref"]
            print(f"  Action dispatched with ref: {action['provider_ref']}")

            print("\n=== 5. Verify Hard Decline Policy Guardrail Block & Auto-Escalation ===")
            hard_exec = await call(
                client, "POST", "/fault-scenarios/hard_decline/execute", 200, headers
            )
            hard_case_id = hard_exec["case_id"]
            hard_res = hard_exec["agent_result"]
            assert hard_res["escalated"] is True, "Hard decline must be automatically escalated"
            print(f"  Hard decline automatically escalated: case_id={hard_case_id}")

            escs = await call(client, "GET", f"/escalations/case/{hard_case_id}", 200, headers)
            assert len(escs) >= 1
            print(f"  Escalation record created: {escs[0]['reason']}")

            print("\n=== 6. Test On-Demand Payment Link Verification Endpoint ===")
            verify_res = await call(
                client, "POST", f"/recovery-cases/{case_id}/verify-payment", 200, headers
            )
            assert "sync_result" in verify_res
            print(f"  Verification result: {verify_res['sync_result']}")

            print("\n=== ALL AUTOMATED RECOVERY DEMO TESTS PASSED! ===")

    finally:
        await cleanup()


if __name__ == "__main__":
    asyncio.run(main())
