from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.auth import router as auth_router
from app.api.routes.orders import router as orders_router
from app.api.routes.payments import router as payments_router
from app.api.routes.recovery_cases import router as recovery_cases_router
from app.api.routes.ai_investigations import router as ai_investigations_router
from app.api.routes.recovery_actions import router as recovery_actions_router
from app.api.routes.recovery_outcomes import router as recovery_outcomes_router
from app.api.routes.escalations import router as escalations_router
from app.api.routes.agent import router as agent_router
from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.fault_scenarios import router as fault_scenarios_router
from app.api.routes.audit_logs import router as audit_logs_router
from app.api.routes.merchants import router as merchants_router

app = FastAPI(
    title="Recoup API",
    version="1.0.0",
)

# Enable CORS for frontend local development and standard origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(orders_router)
app.include_router(payments_router)
app.include_router(recovery_cases_router)
app.include_router(ai_investigations_router)
app.include_router(recovery_actions_router)
app.include_router(recovery_outcomes_router)
app.include_router(escalations_router)
app.include_router(agent_router)
app.include_router(dashboard_router)
app.include_router(fault_scenarios_router)
app.include_router(audit_logs_router)
app.include_router(merchants_router)
