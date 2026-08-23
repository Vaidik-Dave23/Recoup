"""Real Razorpay test-mode integration for the recovery agent.

Used to create a genuine, payable Razorpay Payment Link (test mode --
no real money moves) for each at-risk case, so the AI-drafted recovery
email points the customer at an actual Razorpay checkout instead of a
stubbed retry channel.

Requires RAZORPAY_KEY_ID / RAZORPAY_KEY_SECRET (test mode, rzp_test_...)
to be set. If they are not configured, callers get back a clearly
failed result rather than an exception -- this keeps the agent's
"one failure handled gracefully" behaviour intact.
"""

from __future__ import annotations

from dataclasses import dataclass

import razorpay

from app.core.config import settings


@dataclass
class PaymentLinkResult:
    success: bool
    payment_link_id: str | None = None
    short_url: str | None = None
    error: str | None = None


def _client() -> razorpay.Client:
    return razorpay.Client(auth=(settings.razorpay_key_id, settings.razorpay_key_secret))


def create_recovery_payment_link(
    *,
    amount: int,
    currency: str,
    description: str,
    customer_name: str | None,
    customer_email: str | None,
    reference_id: str,
) -> PaymentLinkResult:
    """Create a Razorpay Payment Link (test mode) for one recovery attempt.

    `reference_id` must be unique per attempt (e.g. f"{case_id}-{attempt}")
    -- Razorpay rejects a duplicate reference_id while a prior link for it
    is still active.
    """
    if not settings.razorpay_key_id or not settings.razorpay_key_secret:
        return PaymentLinkResult(False, error="Razorpay keys are not configured")

    if not customer_email:
        return PaymentLinkResult(False, error="No customer email on file for payment link")

    payload = {
        "amount": amount,
        "currency": currency.upper(),
        "description": description[:255],
        "reference_id": reference_id,
        "customer": {
            "name": customer_name or "Customer",
            "email": customer_email,
        },
        "notify": {"email": False, "sms": False},
        "reminder_enable": False,
    }

    try:
        link = _client().payment_link.create(payload)
    except razorpay.errors.BadRequestError as exc:
        return PaymentLinkResult(False, error=f"Razorpay rejected the request: {exc}")
    except Exception as exc:  # noqa: BLE001 -- network/SDK errors, surfaced to caller
        return PaymentLinkResult(False, error=str(exc))

    return PaymentLinkResult(
        True,
        payment_link_id=link.get("id"),
        short_url=link.get("short_url"),
    )


def fetch_payment_link_status(payment_link_id: str) -> dict:
    """Fetch current status of a payment link -- 'paid', 'created', 'expired', etc.

    Poll this (or wire the payment_link.paid webhook) to auto-mark a
    RecoveryCase as recovered when the customer actually pays via the link.
    """
    return _client().payment_link.fetch(payment_link_id)
