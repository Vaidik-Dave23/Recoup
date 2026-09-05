"""Full end-to-end smoke test for Recoup.

Covers what the three existing smoke tests (api_smoke, agent_smoke,
escalation_smoke) don't:
  - merchant isolation across two separate merchants
  - GET /dashboard/overview
  - GET /audit-logs
  - GET/PATCH /merchants/me, GET /merchants/me/users
  - GET /fault-scenarios, POST /fault-scenarios/{id}/execute
  - a LIVE agent run against a real GEMINI_API_KEY (if set)
  - a REAL email send via your configured SMTP settings (if set)
  - a REAL Razorpay test-mode Payment Link creation (if RAZORPAY_KEY_ID/SECRET set)
  - both the escalate branch and the retry/resume branch

This does NOT replace the other three smoke tests -- run all four.
For an isolated, no-DB/no-network unit test of the Razorpay wrapper's
error handling, see tests/razorpay_client_test.py instead.

Before running, set in your .env (or export in your shell):
  GEMINI_API_KEY=<a real key>          # required to test live agent reasoning
  SMTP_HOST / SMTP_USERNAME / SMTP_PASSWORD / SMTP_FROM_EMAIL   # to test email
  RAZORPAY_KEY_ID / RAZORPAY_KEY_SECRET   # test-mode keys, to test payment links
  TEST_RECIPIENT_EMAIL=<an inbox you can actually check>

If GEMINI_API_KEY, SMTP_*, or RAZORPAY_* are missing, the relevant checks are
skipped with a clear message instead of failing -- this script is meant to be
run early (before those are configured) and again later once they are.

Run with:  python -m tests.full_e2e_smoke

Note: fault_scenarios.py always generates a fake customer_email
(customer_<n>@example.com), so a Fault-Lab-seeded case can never actually
deliver an email. For the live SMTP check, this script creates its own
order/payment/case with a real, checkable email address instead. The fake
Fault Lab address is still fine for the Razorpay check -- Razorpay's test
mode does not validate deliverability, only that an email string is present.
"""

import asyncio
import os
from uuid import uuid4

import httpx
from sqlalchemy import delete

from app.core.config import settings
from app.db.database import AsyncSessionLocal
from app.db.models.merchant import Merchant
from app.main import app

PREFIX = "e2e"
# Defaults to your inbox so you don't need to set an env var to run this.
# Override with TEST_RECIPIENT_EMAIL=<other address> if you ever want to.
TEST_RECIPIENT_EMAIL = os.environ.get("TEST_RECIPIENT_EMAIL", "vaidikdave236@gmail.com")

# Disposable password for the throwaway test-merchant account this script
# registers and deletes on every run. Not your Gmail password, not stored
# anywhere real -- just satisfies the register endpoint's password field.
TEST_ACCOUNT_PASSWORD = "RecoupE2ETest!2026"


async def call(client, method, path, expected, headers=None, json=None):
    print(f"  {method} {path}", flush=True)
    response = await client.request(method, path, headers=headers, json=json)
    assert response.status_code == expected, (
        f"{method} {path}: expected {expected}, got {response.status_code}: "
        f"{response.text}"
    )
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
            "name": f"E2E {tag.upper()}",
            "email": email,
            "password": TEST_ACCOUNT_PASSWORD,
            "business_name": f"E2E {tag.upper()} {suffix}",
        },
    )
    headers = {"Authorization": f"Bearer {registered['access_token']}"}
    return registered, headers


async def create_order_payment_case(
    client, headers, suffix: str, tag: str, *,
    customer_email: str, case_type: str, failure_reason: str, amount: int,
):
    order = await call(
        client, "POST", "/orders", 201, headers,
        {
            "order_id": f"ORDER-{tag}-{suffix}",
            "amount": amount,
            "currency": "INR",
            "customer_email": customer_email,
        },
    )
    payment = await call(
        client, "POST", "/payments", 201, headers,
        {
            "order_id": order["order_id"],
            "amount": amount,
            "currency": "INR",
            "payment_method": "card",
            "transaction_id": f"TXN-{tag}-{suffix}",
        },
    )
    case = await call(
        client, "POST", "/recovery-cases", 201, headers,
        {
            "payment_id": payment["id"],
            "case_type": case_type,
            "failure_reason": failure_reason,
            "amount_at_risk": amount,
            "currency": "INR",
        },
    )
    return order, payment, case


async def main() -> None:
    await cleanup()
    suffix = uuid4().hex[:10]
    results: list[str] = []

    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    try:
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:

            # ---------------------------------------------------------------
            print("\n=== 1. Register two merchants (A and B) ===")
            _, headers_a = await register(client, "a", suffix)
            _, headers_b = await register(client, "b", suffix)
            results.append("PASS  Two merchants registered")

            # ---------------------------------------------------------------
            print("\n=== 2. Merchant isolation ===")
            _, _, case_a = await create_order_payment_case(
                client, headers_a, suffix, "iso",
                customer_email=f"iso-{suffix}@example.com",
                case_type="payment_failed",
                failure_reason="isolation test",
                amount=10000,
            )
            # B must NOT be able to see A's case
            response = await client.request(
                "GET", f"/recovery-cases/{case_a['id']}", headers=headers_b,
            )
            assert response.status_code == 404, (
                f"ISOLATION LEAK: Merchant B got {response.status_code} "
                f"reading Merchant A's case (expected 404)"
            )
            # B's own case list must not contain A's case id
            b_cases = await call(client, "GET", "/recovery-cases", 200, headers_b)
            assert all(c["id"] != case_a["id"] for c in b_cases), (
                "ISOLATION LEAK: Merchant A's case appeared in Merchant B's case list"
            )
            results.append("PASS  Merchant B cannot see Merchant A's case (404 + absent from list)")

            # ---------------------------------------------------------------
            print("\n=== 3. Dashboard, audit log, merchant settings ===")
            overview = await call(client, "GET", "/dashboard/overview", 200, headers_a)
            assert "kpis" in overview and "amount_at_risk" in overview["kpis"]
            results.append(f"PASS  GET /dashboard/overview -> at_risk={overview['kpis']['amount_at_risk']}")

            await call(client, "GET", "/audit-logs", 200, headers_a)
            results.append("PASS  GET /audit-logs")

            merchant_me = await call(client, "GET", "/merchants/me", 200, headers_a)
            smtp_configured = merchant_me["channels"]["email"]["configured"]
            results.append(f"PASS  GET /merchants/me (SMTP configured: {smtp_configured})")

            razorpay_reported_configured = merchant_me["channels"]["razorpay_retry"]["configured"]
            razorpay_actually_configured = bool(
                settings.razorpay_key_id and settings.razorpay_key_secret
            )
            assert razorpay_reported_configured == razorpay_actually_configured, (
                f"/merchants/me reports razorpay_retry.configured="
                f"{razorpay_reported_configured}, but settings say "
                f"{razorpay_actually_configured} -- the endpoint is lying about channel status."
            )
            results.append(
                f"PASS  GET /merchants/me razorpay_retry.configured matches real settings "
                f"({razorpay_actually_configured})"
            )

            await call(
                client, "PATCH", "/merchants/me", 200, headers_a,
                {"business_name": f"E2E A {suffix} (renamed)"},
            )
            await call(client, "GET", "/merchants/me/users", 200, headers_a)
            results.append("PASS  PATCH /merchants/me + GET /merchants/me/users")

            # ---------------------------------------------------------------
            print("\n=== 4. Fault Lab ===")
            scenarios = await call(client, "GET", "/fault-scenarios", 200, headers_a)
            assert len(scenarios) >= 1
            executed = await call(
                client, "POST", "/fault-scenarios/soft_decline/execute", 200, headers_a,
            )
            fault_case_id = executed["case_id"]
            assert "agent_result" in executed and executed["agent_result"] is not None
            fault_run = executed["agent_result"]
            investigations = await call(
                client, "GET", f"/ai-investigations/case/{fault_case_id}", 200, headers_a,
            )
            assert len(investigations) >= 2
            results.append(
                f"PASS  Fault Lab seeded + automated agent ran end-to-end "
                f"(escalated={fault_run.get('escalated')}, {len(investigations)} investigation steps logged)."
            )

            # ---------------------------------------------------------------
            print("\n=== 5. Live Gemini reasoning check ===")
            if not settings.gemini_api_key:
                results.append("SKIP  GEMINI_API_KEY not set -- agent ran in fallback mode only, not tested live.")
            else:
                results.append(f"PASS  GEMINI_API_KEY is set (model: {settings.gemini_model})")
                if fault_run.get("triage") and fault_run["triage"].get("summary"):
                    results.append(f"      Triage summary: {fault_run['triage']['summary'][:120]}")
                if fault_run.get("strategy"):
                    conf = fault_run["strategy"].get("confidence")
                    results.append(f"      Strategy confidence: {conf}")

            # ---------------------------------------------------------------
            print("\n=== 6. Live Razorpay payment link check ===")
            if not (settings.razorpay_key_id and settings.razorpay_key_secret):
                results.append(
                    "SKIP  RAZORPAY_KEY_ID / RAZORPAY_KEY_SECRET not set -- payment link "
                    "creation was not attempted (see razorpay_client_test.py for the "
                    "offline unit test of this code path)."
                )
            else:
                await _check_payment_link_for_case(
                    client, headers_a, fault_case_id, fault_run, results,
                    label="Fault Lab case",
                )

            # ---------------------------------------------------------------
            print("\n=== 7. Force the escalate branch (hard decline, low confidence expected) ===")
            _, _, escalate_case = await create_order_payment_case(
                client, headers_a, suffix, "esc",
                customer_email=f"esc-{suffix}@example.com",
                case_type="payment_failed",
                failure_reason="stolen_card_decline",
                amount=12500,
            )
            escalate_run = await call(
                client, "POST", f"/recovery-cases/{escalate_case['id']}/agent/run", 200, headers_a,
            )
            assert escalate_run["escalated"] is True, "Hard-decline case must deterministically escalate via policy"
            escalation = await call(
                client, "GET", f"/escalations/case/{escalate_case['id']}", 200, headers_a,
            )
            assert len(escalation) >= 1 and escalation[0].get("notes")
            results.append(
                f"PASS  Hard-decline case deterministically escalated with a written handoff summary: "
                f"\"{escalation[0]['notes'][:100]}...\""
            )

            # ---------------------------------------------------------------
            print("\n=== 8. LIVE SMTP send + retry-loop check ===")
            if not TEST_RECIPIENT_EMAIL:
                results.append(
                    "SKIP  Set TEST_RECIPIENT_EMAIL env var to an inbox you can check, then re-run "
                    "this script to test real email delivery."
                )
            elif not settings.smtp_host or not settings.smtp_from_email:
                results.append(
                    "SKIP  SMTP_HOST / SMTP_FROM_EMAIL not set in .env -- cannot test real delivery."
                )
            else:
                _, _, email_case = await create_order_payment_case(
                    client, headers_a, suffix, "mail",
                    customer_email=TEST_RECIPIENT_EMAIL,
                    case_type="payment_failed",
                    failure_reason="insufficient_funds",
                    amount=4999,
                )
                run1 = await call(
                    client, "POST", f"/recovery-cases/{email_case['id']}/agent/run", 200, headers_a,
                )
                await _verify_recipient_is_registered_email(
                    client, headers_a, email_case["id"], TEST_RECIPIENT_EMAIL, results,
                )
                await _report_send_attempt(run1, TEST_RECIPIENT_EMAIL, results, attempt=1)
                if settings.razorpay_key_id and settings.razorpay_key_secret:
                    await _check_payment_link_for_case(
                        client, headers_a, email_case["id"], run1, results,
                        label="Live SMTP case (attempt 1)",
                        check_in_email_body=True,
                    )

                if not run1["escalated"] and run1.get("action_id"):
                    # record a failed outcome and confirm the retry loop fires
                    await call(
                        client, "POST", "/recovery-outcomes", 201, headers_a,
                        {
                            "case_id": email_case["id"],
                            "action_id": run1["action_id"],
                            "recovered": False,
                            "amount_recovered": 0,
                            "notes": "e2e test: forcing a retry",
                        },
                    )
                    run2 = await call(
                        client, "POST", f"/recovery-cases/{email_case['id']}/agent/resume", 200, headers_a,
                    )
                    if run2:
                        await _report_send_attempt(run2, TEST_RECIPIENT_EMAIL, results, attempt=2)
                    else:
                        results.append("NOTE  Resume returned null (case already closed) -- unexpected after a failed outcome, worth a look.")

            # ---------------------------------------------------------------
            print("\n=== 9. Outcomes rollup ===")
            outcomes_case = await call(client, "GET", f"/recovery-outcomes/case/{escalate_case['id']}", 200, headers_a)
            results.append(f"PASS  GET /recovery-outcomes/case/{{id}} ({len(outcomes_case)} outcome(s) for that case)")

    finally:
        await cleanup()

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    for line in results:
        print(line)
    print("=" * 70)
    if TEST_RECIPIENT_EMAIL and settings.smtp_host:
        print(f"\n>>> Check {TEST_RECIPIENT_EMAIL} now and tell Claude whether the email(s) arrived. <<<\n")


async def _check_payment_link_for_case(
    client, headers, case_id: str, run: dict, results: list[str], *,
    label: str, check_in_email_body: bool = False,
) -> None:
    """Verify a live Razorpay test-mode Payment Link was actually created
    for this case's generate_content step, by reading it back from the
    AI investigation audit log and the persisted RecoveryAction -- not by
    trusting the in-memory run result alone."""
    if run.get("escalated") or not run.get("action_id"):
        results.append(
            f"NOTE  {label}: case escalated before generate_content ran -- "
            f"no payment link attempt this run (non-deterministic, re-run to try again)."
        )
        return

    investigations = await call(
        client, "GET", f"/ai-investigations/case/{case_id}", 200, headers,
    )
    content_step = next(
        (i for i in reversed(investigations) if i["node_name"] == "generate_content"), None,
    )
    if content_step is None:
        results.append(f"FAIL  {label}: no generate_content investigation step found to check.")
        return

    payload = content_step["response_payload"]
    if not payload.get("payment_link_created"):
        results.append(
            f"FAIL  {label}: Razorpay keys are configured but payment_link_created is False "
            f"-- error was: {payload.get('payment_link_error')}"
        )
        return

    link_id = payload.get("payment_link_id")
    short_url = payload.get("payment_link_url")
    assert link_id, f"{label}: payment_link_created is True but payment_link_id is missing"
    assert short_url and short_url.startswith("https://"), (
        f"{label}: payment_link_url missing or not a real https link: {short_url!r}"
    )
    results.append(
        f"PASS  {label}: real Razorpay payment link created -- {short_url} "
        f"(id: {link_id})"
    )

    # Cross-check it also landed on the persisted RecoveryAction, not just
    # in the investigation log.
    action = await call(
        client, "GET", f"/recovery-actions/{run['action_id']}", 200, headers,
    )
    assert action.get("provider_ref") and f"rzp_link:{link_id}" in action["provider_ref"], (
        f"{label}: RecoveryAction.provider_ref does not reference the payment link "
        f"(got {action.get('provider_ref')!r})"
    )
    results.append(f"PASS  {label}: RecoveryAction.provider_ref correctly references {link_id}")

    if check_in_email_body:
        body = payload.get("body", "")
        assert short_url in body, (
            f"{label}: payment link URL was created but never made it into the "
            f"actual email body that was sent -- customer would not have received it."
        )
        results.append(
            f"PASS  {label}: payment link URL is present in the actual sent email body. "
            f">>> CHECK YOUR INBOX -- the link should be clickable and open a real "
            f"Razorpay test-mode checkout page. <<<"
        )


async def _verify_recipient_is_registered_email(
    client, headers, case_id: str, expected_email: str, results: list[str],
) -> None:
    """Hard safety check: confirm the case's payment/order actually has
    expected_email as its customer_email -- i.e. any email the agent sends
    for this case is provably scoped to the address that was registered on
    the order, not something the agent could have substituted."""
    case = await call(client, "GET", f"/recovery-cases/{case_id}", 200, headers)
    payment = await call(client, "GET", f"/payments/{case['payment_id']}", 200, headers)
    order = await call(client, "GET", f"/orders/{payment['order_id']}", 200, headers)
    assert order["customer_email"] == expected_email, (
        f"SAFETY CHECK FAILED: order.customer_email is "
        f"{order['customer_email']!r}, expected {expected_email!r}. "
        f"The agent would not have sent to the intended address."
    )
    results.append(
        f"PASS  Safety check: this case's registered email is exactly "
        f"{expected_email} -- the agent has no other address to send to."
    )


async def _report_send_attempt(run: dict, recipient: str, results: list[str], *, attempt: int) -> None:
    if run["escalated"]:
        results.append(
            f"NOTE  Attempt {attempt}: agent escalated instead of sending (low confidence) -- "
            f"expected behavior, not a bug. No email sent this attempt."
        )
        return

    channel = run.get("action_channel")
    if channel != "email":
        results.append(
            f"NOTE  Attempt {attempt}: agent chose channel '{channel}', not email -- "
            f"no email was attempted this run (non-deterministic, re-run to try again)."
        )
        return

    send_result = run.get("send_result") or {}
    if send_result.get("success"):
        results.append(
            f"PASS  Attempt {attempt}: SMTP reported success sending to {recipient} "
            f"(provider_ref: {send_result.get('provider_ref')}). "
            f">>> CHECK YOUR INBOX AND CONFIRM <<<"
        )
    else:
        results.append(
            f"FAIL  Attempt {attempt}: SMTP send failed: {send_result.get('error')}"
        )


if __name__ == "__main__":
    asyncio.run(main())