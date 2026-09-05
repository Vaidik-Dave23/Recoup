# Recoup

### AI-Powered Payment Recovery Platform

Recoup is an end-to-end revenue recovery platform that helps merchants investigate failed or at-risk payments, generate recovery strategies with AI, execute recovery outreach, and escalate uncertain cases to humans.

Recoup is designed to process payment batches, surface useful recovery insights with low latency, and turn individual payment failures into actionable recovery workflows instead of leaving teams to investigate them manually.

The project combines a React dashboard, FastAPI API, PostgreSQL persistence, a LangGraph recovery agent powered by Gemini, Razorpay test-mode Payment Links, SMTP email delivery, and a Fault Lab for reproducible recovery scenarios.

> **Live demo:** https://recoup-one.vercel.app  
> **Repository:** https://github.com/Vaidik-Dave23/Recoup

---

## Architecture

![Recoup Architecture](architecture.png)

The system is organized into six major layers:

1. **Frontend** - React + TypeScript + Vite dashboard for authentication, case management, investigations, actions, outcomes, escalations, audit logs, and Fault Lab scenarios.
2. **Backend API** - FastAPI with JWT authentication, CORS, request validation, merchant isolation, recovery services, and REST endpoints.
3. **AI Agent** - LangGraph orchestration with Gemini for triage, strategy generation, recovery content, execution, and human escalation.
4. **Data Layer** - PostgreSQL accessed asynchronously through SQLAlchemy, with Alembic for migrations.
5. **Integrations** - Razorpay test-mode Payment Links and optional SMTP email delivery.
6. **Infrastructure** - Vercel for the frontend and Azure App Service for the FastAPI backend, with Azure deployment/runtime logs.

---

## Demo Flow

The current demo shows the complete recovery journey from the merchant dashboard to an actual recovery action:

1. A payment batch is monitored and recovery insights are surfaced on the dashboard.
2. Fault Lab is used to create a controlled dummy payment failure.
3. The recovery workflow analyzes the failure and moves through the responsible agent nodes.
4. The system decides whether to recover the payment automatically or escalate it based on the configured confidence threshold.
5. Recovery outreach is generated and sent through the configured email channel.
6. The recovery email contains the Razorpay Payment Link generated in test mode.
7. The link can be opened and completed using Razorpay's test environment, demonstrating the recovery flow end-to-end.

This makes the demo reproducible without requiring a real merchant payment webhook or real-money transaction.

---

## The Recovery Flow

```text
Payment / Recovery Case
        |
        v
     TRIAGE
        |
        v
   STRATEGIZE
        |
        | confidence >= threshold
        +----------------------+
        |                      |
        v                      v
 GENERATE CONTENT          ESCALATE
        |                  TO HUMAN
        v
 EXECUTE RECOVERY
        |
        +----> Razorpay Payment Link (test mode)
        |
        +----> Optional SMTP email
        |
        v
   Recovery Outcome
        |
        v
   Audit / Timeline
```

The important design decision is that the model does **not** get unlimited authority. The backend enforces recovery constraints, including a confidence threshold and maximum retry count. If the strategy does not meet the configured confidence threshold, the graph routes the case to escalation instead of executing an uncertain action.

---

## Core Features

### AI-powered investigation

- Gemini-powered triage of payment/recovery problems.
- Strategy generation with confidence scoring.
- AI-generated customer recovery content.
- Agent trace stored as structured investigation records.
- Human escalation with an AI-generated handoff summary when confidence is too low.

### Recovery execution

- Generates Razorpay Payment Links in **test mode**.
- Supports optional SMTP delivery for recovery emails.
- Records recovery actions and provider references.
- Tracks recovery outcomes and case state.
- Enforces a configurable maximum number of recovery attempts.

### Merchant operations dashboard

- Dashboard KPIs and recovery overview.
- Payment batch monitoring and recovery insights.
- At-risk recovery queue.
- Detailed recovery case view.
- Agent trace for individual cases.
- Recovery actions and outcomes.
- Escalation management.
- Audit log / investigation history.
- Merchant settings.

### Payment batch insights

Recoup is built around batch-level payment visibility so merchants can quickly understand where recovery opportunities are coming from instead of inspecting failures one by one. The dashboard surfaces the relevant recovery information while keeping the detailed investigation available at the case level.

### Fault Lab

Fault Lab provides deterministic scenarios for demonstrating and testing the recovery workflow without needing a live merchant payment integration.

Scenarios can be executed through the application and then passed through the same case, investigation, agent, action, escalation, and outcome flows used by the rest of the system.

---

## AI Agent Architecture

The recovery agent is implemented with **LangGraph** as a stateful workflow.

### First-pass run

```text
TRIAGE
  |
  v
STRATEGIZE
  |
  +---- confidence below threshold ----> ESCALATE
  |
  | confidence meets threshold
  v
GENERATE_CONTENT
  |
  v
EXECUTE
```

### Retry run

Retries start from the strategy stage rather than repeating the initial triage step. The backend tracks attempt count and uses `RECOVERY_MAX_ATTEMPTS` to prevent indefinite retries.

### Confidence-gated execution

The agent's strategy includes a confidence score. The backend compares that score against:

```text
RECOVERY_CONFIDENCE_THRESHOLD=0.55
```

A strategy below the threshold is routed to human escalation.

This is intentionally enforced in application logic rather than relying only on a prompt instruction.

---

## Security and Reliability

### Authentication

- JWT-based authentication.
- Protected merchant routes require an authenticated user.
- Merchant-scoped queries prevent users from accessing another merchant's records.

### Password hashing

The project uses direct `bcrypt` rather than the previously used `passlib` wrapper.

Passwords are SHA-256 pre-hashed before bcrypt so the application can safely handle passwords beyond bcrypt's native 72-byte input limit without silently truncating them. Verification also supports legacy bcrypt hashes for backward compatibility.

Invalid credentials are returned as clean `401 Unauthorized` responses instead of surfacing password-hashing exceptions as `500 Internal Server Error` responses.

### CORS

The production frontend origin is explicitly configured for credentialed CORS requests. Wildcard origins are not used with credentials enabled.

---

## Technology Stack

| Layer | Technology |
|---|---|
| Frontend | React 19, TypeScript, Vite |
| Routing | React Router |
| UI icons | Lucide React |
| Backend | Python, FastAPI, Uvicorn |
| AI orchestration | LangGraph |
| LLM | Google Gemini (`google-genai`) |
| Database | PostgreSQL |
| ORM | SQLAlchemy async |
| Migrations | Alembic |
| Authentication | JWT (`python-jose`) |
| Password hashing | bcrypt + SHA-256 pre-hashing |
| Payments | Razorpay Test Mode |
| Email | SMTP |
| Frontend hosting | Vercel |
| Backend hosting | Azure App Service |

---

## Project Structure

```text
Recoup/
├── app/
│   ├── agent/
│   │   ├── graph.py              # LangGraph workflow
│   │   ├── nodes.py              # Triage, strategy, content, execution, escalation
│   │   ├── state.py              # Agent state
│   │   ├── prompts.py             # Gemini prompts
│   │   ├── gemini_client.py       # Gemini integration
│   │   ├── razorpay_client.py     # Razorpay Payment Links
│   │   └── email_sender.py        # SMTP delivery
│   │
│   ├── api/routes/
│   │   ├── auth.py
│   │   ├── orders.py
│   │   ├── payments.py
│   │   ├── recovery_cases.py
│   │   ├── ai_investigations.py
│   │   ├── recovery_actions.py
│   │   ├── recovery_outcomes.py
│   │   ├── escalations.py
│   │   ├── agent.py
│   │   ├── dashboard.py
│   │   ├── fault_scenarios.py
│   │   ├── audit_logs.py
│   │   └── merchants.py
│   │
│   ├── core/
│   │   ├── config.py              # Environment configuration
│   │   ├── dependencies.py        # Authentication / DB dependencies
│   │   └── security.py            # JWT + password hashing
│   │
│   ├── db/
│   │   ├── database.py
│   │   └── models/                # SQLAlchemy models
│   │
│   ├── schemas/                   # Pydantic request/response models
│   ├── services/                  # Business logic
│   └── main.py                    # FastAPI application entrypoint
│
├── frontend/
│   └── src/
│       ├── pages/                 # Dashboard and product screens
│       ├── components/            # Shared UI components
│       ├── services/api.ts        # API client
│       └── App.tsx                # Routing and auth guards
│
├── alembic/                       # Database migrations
├── tests/
├── docs/
│   └── architecture.png
├── requirements.txt
├── .env.example
└── README.md
```

---

## API Surface

The FastAPI application exposes REST resources for:

- `/auth` - registration, login, current user
- `/orders` - merchant orders
- `/payments` - payment records
- `/recovery-cases` - recovery case lifecycle
- `/ai-investigations` - AI investigation records
- `/recovery-actions` - recovery actions
- `/recovery-outcomes` - recovery outcomes
- `/escalations` - human escalation workflow
- `/dashboard` - recovery KPIs and overview
- `/fault-scenarios` - Fault Lab scenarios
- `/audit-logs` - audit history
- `/merchants` - merchant profile/settings
- `/{case_id}/agent/run` - execute the recovery agent
- `/{case_id}/agent/resume` - resume a recovery workflow

FastAPI also provides the generated API documentation at `/docs` when the backend is running.

---

## Local Development

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL
- A Gemini API key for live AI reasoning
- Razorpay test-mode credentials for Payment Links
- SMTP credentials if real email delivery is required

### 1. Clone the repository

```bash
git clone https://github.com/Vaidik-Dave23/Recoup.git
cd Recoup
```

### 2. Configure the backend

Create a virtual environment and install dependencies:

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS/Linux
# source .venv/bin/activate

pip install -r requirements.txt
```

Create `.env` from `.env.example` and configure your database and service credentials.

### 3. Run database migrations

```bash
alembic upgrade head
```

### 4. Start the backend

```bash
uvicorn app.main:app --reload
```

The API will be available at:

```text
http://127.0.0.1:8000
```

Interactive API documentation:

```text
http://127.0.0.1:8000/docs
```

### 5. Start the frontend

```bash
cd frontend
npm install
npm run dev
```

The Vite development server proxies `/api/*` requests to the local FastAPI server.

---

## Environment Variables

| Variable | Required | Description |
|---|---:|---|
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `JWT_SECRET_KEY` | Yes | Secret used to sign JWT access tokens |
| `JWT_ALGORITHM` | No | JWT algorithm, defaults to `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | JWT lifetime, defaults to `60` |
| `GEMINI_API_KEY` | For AI | Gemini API key |
| `GEMINI_MODEL` | No | Defaults to `gemini-2.5-flash` |
| `RECOVERY_CONFIDENCE_THRESHOLD` | No | Confidence gate, defaults to `0.55` |
| `RECOVERY_MAX_ATTEMPTS` | No | Maximum recovery attempts, defaults to `3` |
| `RAZORPAY_KEY_ID` | For payments | Razorpay test-mode key ID |
| `RAZORPAY_KEY_SECRET` | For payments | Razorpay test-mode key secret |
| `RAZORPAY_WEBHOOK_SECRET` | Optional | Reserved for webhook configuration |
| `SMTP_HOST` | For email | SMTP server hostname |
| `SMTP_PORT` | No | Defaults to `587` |
| `SMTP_USERNAME` | For email | SMTP username |
| `SMTP_PASSWORD` | For email | SMTP password |
| `SMTP_FROM_EMAIL` | For email | Sender address |
| `SMTP_USE_TLS` | No | Defaults to `true` |
| `FRONTEND_URL` | Optional | Additional allowed frontend origins |

Never commit real credentials or `.env` files to source control.

---

## Testing

The repository includes focused smoke and compatibility tests:

```bash
python -m tests.api_smoke
python -m tests.agent_smoke
python -m tests.escalation_smoke
python -m tests.business_state_test
python -m tests.auth_compat_test
python -m tests.razorpay_client_test
python -m tests.full_e2e_smoke
```

### Authentication compatibility coverage

`tests/auth_compat_test.py` specifically covers the production authentication fixes, including:

- correct password verification
- incorrect credentials returning `401`
- nonexistent users returning `401`
- passwords longer than bcrypt's native 72-byte limit
- legacy bcrypt hash verification
- invalid/corrupt password hashes failing safely
- production frontend CORS behavior

---

## Deployment

### Frontend

The frontend is a Vite/React application deployed on Vercel.

`frontend/vercel.json` rewrites incoming routes to `index.html`, which allows React Router routes such as `/login`, `/dashboard`, and `/recovery/cases/:id` to survive direct navigation and browser refreshes.

### Backend

The FastAPI application is deployed to Azure App Service using Uvicorn:

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Production configuration is supplied through Azure App Service environment variables rather than committing secrets to the repository.

---

## Current Scope and Limitations

Recoup is a working prototype focused on demonstrating the complete AI-assisted recovery workflow.

Current limitations include:

- Email is the live recovery outreach channel. Other channels are normalized to email rather than pretending to execute an unsupported provider.
- Razorpay integration is configured for **test mode** and is intended for safe demonstrations rather than real-money recovery.
- Fault Lab is used to reproduce recovery scenarios without requiring a merchant's production payment webhook integration.
- Production-grade concerns such as background job infrastructure, distributed task queues, advanced observability, rate limiting, and additional communication providers would be natural next steps for a larger deployment.

---

## Why This Project Is Interesting

Recoup is not just an LLM wrapper. The project treats the AI model as one component inside a constrained software system:

- **Structured state** is passed through a LangGraph workflow.
- **Business rules are enforced by backend code**, not only by prompts.
- **Confidence controls whether the AI is allowed to act.**
- **Retries have a hard limit.**
- **Actions and AI investigations are persisted for traceability.**
- **Razorpay Payment Links connect an AI recommendation to an actual payment workflow in test mode.**
- **Human escalation is a first-class outcome instead of an error state.**

This makes Recoup a practical example of building an agentic system with real integrations, persistence, guardrails, and an operational UI.

---

## Project Status

**Working end-to-end prototype.**

The current build is demonstrated through a controlled payment-failure scenario in Fault Lab, followed by AI analysis, recovery decision-making, email outreach, and a Razorpay test-mode payment flow.

The deployed application currently supports authentication, dashboard operations, payment batch insights, recovery case management, AI investigation/agent execution, recovery actions, escalation flows, outcomes, audit history, Fault Lab scenarios, Razorpay test-mode payment links, and SMTP email delivery.

---

## Author

**Vaidik Dave**  
AI / GenAI Engineer

- GitHub: https://github.com/Vaidik-Dave23
- Project: https://github.com/Vaidik-Dave23/Recoup
- Live App: https://recoup-one.vercel.app
