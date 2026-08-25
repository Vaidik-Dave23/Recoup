# Recoup

**An AI agent that recovers revenue lost to failed payments, abandoned checkouts, and overdue invoices — built for the Razorpay AI Buildathon (Track 3: AI Revenue Recovery).**

Recoup watches for money that should have landed but didn't, decides what to do about it, and either acts autonomously or hands off to a human — with an audit trail for every decision, a hard cap on retries, and real Razorpay payment links doing the actual recovery work.

---

## What it does

1. **Detects** a failed payment, an abandoned checkout, or an overdue invoice
2. **Triages** the case with Gemini — what happened, how urgent, what's known
3. **Strategizes** a recovery approach and scores its own confidence
4. **Generates** outreach content and a real, payable Razorpay Payment Link (test mode)
5. **Executes** — sends the email, or **escalates to a human** if confidence is too low or the channel isn't safely automatable
6. **Retries up to 3 times**, then force-escalates if nothing's worked — the agent cannot loop forever
7. **Closes the loop** — a Razorpay webhook (or manual sync, for local dev) marks the case recovered the moment the customer actually pays

Every step is logged to an `AIInvestigation` audit trail: what the agent saw, what it decided, and why.

---

## Architecture

```
FastAPI backend (app/)
├── LangGraph agent (app/agent/)
│   ├── triage → strategize → generate_content → execute → escalate
│   ├── confidence-gated routing (low confidence → escalate, not guess)
│   ├── razorpay_client.py — real test-mode Payment Links API
│   └── email_sender.py — real SMTP delivery
├── REST API (app/api/routes/)
│   ├── orders, payments, recovery-cases, recovery-actions, recovery-outcomes
│   ├── ai-investigations (the audit trail)
│   ├── escalations, fault-scenarios (Fault Lab), dashboard, merchants
│   └── webhooks — Razorpay payment_link.paid closes the recovery loop
└── Postgres (SQLAlchemy async + Alembic migrations)

React + TypeScript frontend (frontend/)
├── Dashboard — KPIs: at-risk, recovered, recovery rate
├── Fault Lab — seed realistic failure scenarios with one click
├── Case Detail / Agent Trace — run the agent, watch every step
├── Recovery Actions / Escalations / Outcomes
└── Vite dev server, proxies /api → FastAPI on :8000
```

### Why a real Razorpay integration, not a mock

The recovery loop only means something if the payment link the agent generates is real. `generate_content()` calls Razorpay's actual test-mode **Payment Links API**, embeds the live link in the outreach email, and the resulting `payment_link_id` is tracked on the `RecoveryAction` record. When the customer pays it — for real, through Razorpay's own checkout — a webhook (or the manual sync fallback) marks the case `recovered` and records the exact amount. Nothing about "recovered revenue" in this app is simulated once real keys are configured.

### Stopping rules & escalation

- A confidence threshold (`RECOVERY_CONFIDENCE_THRESHOLD`, default `0.55`) gates every action: below it, the agent stops and escalates to a human with a written handoff summary instead of guessing.
- A hard attempt cap (`RECOVERY_MAX_ATTEMPTS`, default `3`) forces escalation once retries are exhausted — the agent cannot retry indefinitely.
- Only the `email` channel is actually wired to a live provider; this is enforced server-side, not just by prompting the model, so it can't silently no-op on an unimplemented channel.

---

## Setup

### Prerequisites
- Python 3.11+
- Node 18+
- PostgreSQL (local or hosted)

### Backend

```bash
pip install -r requirements.txt --break-system-packages   # or use a venv
cp .env.example .env                                       # fill in the values below
alembic upgrade head
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The Vite dev server proxies `/api/*` to `http://127.0.0.1:8000`, so run the backend first.

### Environment variables (`.env`)

| Variable | Required | Purpose |
|---|---|---|
| `DATABASE_URL` | Yes | Postgres connection string |
| `JWT_SECRET_KEY` | Yes | Auth token signing |
| `GEMINI_API_KEY` | For real agent reasoning | Without it, triage/strategy fall back to low-confidence defaults and everything escalates |
| `GEMINI_MODEL` | No | Defaults to `gemini-2.5-flash` |
| `RECOVERY_CONFIDENCE_THRESHOLD` | No | Default `0.55` |
| `RECOVERY_MAX_ATTEMPTS` | No | Default `3` |
| `RAZORPAY_KEY_ID` / `RAZORPAY_KEY_SECRET` | For real payment links | Test-mode keys (`rzp_test_...`) — free, no KYC. Get them from the Razorpay Dashboard → Test Mode → API Keys |
| `RAZORPAY_WEBHOOK_SECRET` | For closing the loop via webhook | Must match the secret set on your webhook in the Razorpay Dashboard |
| `SMTP_HOST` / `SMTP_USERNAME` / `SMTP_PASSWORD` / `SMTP_FROM_EMAIL` | For real email delivery | Without these, the agent still runs but no email actually sends |

---

## Closing the recovery loop

Creating a payment link only *offers* the customer a way to pay — something has to notice when they actually do.

**Option A — real webhook (production path).** Razorpay Dashboard → Accounts & Settings → Webhooks → Add New Webhook:
- URL: `https://<your-public-host>/webhooks/razorpay`
- Secret: matches `RAZORPAY_WEBHOOK_SECRET`
- Event: `payment_link.paid`

Webhooks require a public URL — `localhost` won't work. For local development, tunnel with ngrok, zrok, or similar, and point the webhook at the tunnel's URL.

**Option B — manual sync (local dev, no tunnel needed).**
```
POST /recovery-actions/{action_id}/sync-payment
```
Polls Razorpay directly for that action's payment link status and records the outcome through the identical code path the webhook uses — so both are provably consistent.

---

## Testing

Three layers, each for a different purpose:

**`tests/razorpay_client_test.py`** — unit tests for the Razorpay wrapper. No DB, no network, no real keys; mocks the SDK to verify error handling (missing keys, missing email, API rejection, network failure) and payload correctness.
```bash
python -m tests.razorpay_client_test
```

**`tests/full_e2e_smoke.py`** — full integration smoke test against a running app + Postgres: merchant isolation, dashboard, audit log, Fault Lab, live Gemini reasoning (if `GEMINI_API_KEY` set), live Razorpay payment link creation (if keys set), the escalation branch, live SMTP send + retry loop (if configured), and outcomes. Anything not configured is skipped cleanly rather than failing.
```bash
python -m tests.full_e2e_smoke
```

**`tests/batch_recovery_report.py`** — not a pass/fail test; a reporting script that seeds a batch of Fault Lab cases (default 50, cycled across all four failure types), runs the real agent on each, and reports escalation rate, channel distribution, and payment links created. Pay a couple of the printed links manually, then re-run with `--sync-only` to see real recovery numbers.
```bash
python -m tests.batch_recovery_report            # seed + run a batch
python -m tests.batch_recovery_report --sync-only # close the loop, report real KPIs
```

Also present from earlier development: `tests/api_smoke.py`, `tests/agent_smoke.py`, `tests/escalation_smoke.py` — narrower smoke tests covering the base API, a single agent run, and the escalation path respectively.

---

## Demoing without a full merchant integration

Recoup normally ingests cases the way a real merchant would: Razorpay pushes a `payment.failed` webhook, Recoup auto-creates a `RecoveryCase`. For demo purposes, the **Fault Lab** page seeds the exact same case shape with one click — it's not a mock of the product, it's a mock of *"a payment just failed on a merchant's real Razorpay account."* Everything downstream (triage, strategy, real payment link, real email, real recovery) runs identically either way.

---

## Track fit (Razorpay AI Buildathon, Track 3: AI Revenue Recovery)

| Bar | How this meets it |
|---|---|
| Detect payment failures & checkout abandonment | `CaseType`: `payment_failed`, `abandoned_checkout`, `overdue_invoice` |
| Measured money recovered across a batch | `tests/batch_recovery_report.py` + `/dashboard/overview` KPIs |
| Compliant escalation | Confidence-gated routing with a written handoff summary on escalation |
| Stopping rules | Hard 3-attempt cap, enforced server-side |
| Audit trail | Every LangGraph node logs to `AIInvestigation` with confidence scores |
| Real Razorpay integration | Payment Links API (test mode) + webhook / manual sync to close the loop |

---

## Known limitations

- Only the `email` channel is live; SMS and other retry channels are enumerated but not implemented.
- Razorpay doesn't offer a server-side API to programmatically complete a Payment Link — a batch's recovery rate can only be pushed above 0% by actually paying links through the real checkout UI (with a Razorpay test card), not by scripting it.
- `RecoveryAction.provider_ref` stores the Razorpay payment link ID as a substring of a free-text field rather than a dedicated column — functional, but worth normalizing if this integration grows further.
- Real ingestion via a `payment.failed` webhook (the production replacement for Fault Lab) is not yet implemented — Fault Lab is the only way cases get created today.
