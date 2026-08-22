import random
from typing import Annotated
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.database import get_db
from app.db.models.merchant_user import MerchantUser
from app.schemas.order import OrderCreate
from app.schemas.payment import PaymentCreate
from app.schemas.recovery_case import RecoveryCaseCreate
from app.services.order_service import create_order
from app.services.payment_service import create_payment
from app.services.recovery_case_service import create_recovery_case

router = APIRouter(
    prefix="/fault-scenarios",
    tags=["Fault Lab"],
)

CurrentUser = Annotated[
    MerchantUser,
    Depends(get_current_user),
]

DBSession = Annotated[
    AsyncSession,
    Depends(get_db),
]

SCENARIOS = {
    "hard_decline": {
        "id": "hard_decline",
        "name": "Hard Decline (Stolen Card)",
        "description": "Card is reported stolen. The bank instantly blocks the payment. The AI should flag this and immediately escalate to human review.",
        "case_type": "payment_failed",
        "failure_reason": "stolen_card_decline",
        "amount": 12500,
        "currency": "INR",
        "payment_method": "card",
    },
    "soft_decline": {
        "id": "soft_decline",
        "name": "Soft Decline (Insufficient Funds)",
        "description": "Customer has insufficient funds. The AI should wait 24 hours, send a gentle reminder email, and trigger an automated retry.",
        "case_type": "payment_failed",
        "failure_reason": "insufficient_funds",
        "amount": 4999,
        "currency": "INR",
        "payment_method": "card",
    },
    "abandoned_checkout": {
        "id": "abandoned_checkout",
        "name": "Abandoned Checkout",
        "description": "Customer left items in their cart and closed the tab. AI triggers an abandoned checkout sequence with a discount link.",
        "case_type": "abandoned_checkout",
        "failure_reason": "checkout_abandoned",
        "amount": 8900,
        "currency": "INR",
        "payment_method": "upi",
    },
    "overdue_invoice": {
        "id": "overdue_invoice",
        "name": "Overdue Invoice B2B",
        "description": "A high-value invoice remains unpaid for 30 days. AI sends formal dunning notices and escalates if unanswered.",
        "case_type": "overdue_invoice",
        "failure_reason": "invoice_unpaid_30_days",
        "amount": 75000,
        "currency": "INR",
        "payment_method": "bank_transfer",
    },
}


@router.get("")
async def list_scenarios(current_user: CurrentUser):
    return list(SCENARIOS.values())


@router.post("/{scenario_id}/execute")
async def execute_scenario(
    scenario_id: str,
    current_user: CurrentUser,
    db: DBSession,
):
    if scenario_id not in SCENARIOS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fault scenario not found",
        )

    sc = SCENARIOS[scenario_id]
    suffix = f"{random.randint(100, 999)}"
    order_custom_id = f"ORDER_FAULT_{scenario_id[:4].upper()}_{suffix}"
    txn_id = f"pay_FAULT_{scenario_id[:4].upper()}_{suffix}"
    customer_email = f"customer_{suffix}@example.com"

    # 1. Create order
    order_in = OrderCreate(
        order_id=order_custom_id,
        amount=sc["amount"],
        currency=sc["currency"],
        customer_email=customer_email,
    )
    order = await create_order(db, current_user.merchant_id, order_in)

    # 2. Create payment
    payment_in = PaymentCreate(
        order_id=order_custom_id,
        amount=Decimal(str(sc["amount"])),
        currency=sc["currency"],
        payment_method=sc["payment_method"],
        transaction_id=txn_id,
    )
    payment = await create_payment(db, current_user.merchant_id, payment_in)

    # 3. Create case
    case_in = RecoveryCaseCreate(
        payment_id=payment.id,
        case_type=sc["case_type"],
        failure_reason=sc["failure_reason"],
        amount_at_risk=sc["amount"],
        currency=sc["currency"],
    )
    case = await create_recovery_case(db, current_user.merchant_id, case_in)

    return {
        "success": True,
        "case_id": str(case.id),
        "message": f"Successfully created case for {sc['name']}",
    }
