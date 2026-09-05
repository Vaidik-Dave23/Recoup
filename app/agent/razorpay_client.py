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
        return PaymentLinkResult(
            True,
            payment_link_id=link.get("id"),
            short_url=link.get("short_url"),
        )
    except Exception as exc:
        err_msg = str(exc)
        if "limit of 30" in err_msg.lower() or "limit" in err_msg.lower():
            try:
                # When Razorpay test mode 30-link limit is reached, create a genuine Razorpay Order
                c = _client()
                order = c.order.create({
                    "amount": amount,
                    "currency": currency.upper(),
                    "receipt": reference_id[:40],
                    "notes": {
                        "description": description[:200],
                        "customer_name": customer_name or "Customer",
                        "customer_email": customer_email,
                    },
                })
                order_id = order.get("id")
                frontend_base = (settings.frontend_url.split(",")[0].strip() if settings.frontend_url else "http://localhost:5173").rstrip("/")
                hosted_url = f"{frontend_base}/pay/{order_id}"
                return PaymentLinkResult(
                    True,
                    payment_link_id=order_id,
                    short_url=hosted_url,
                )
            except Exception as order_exc:
                return PaymentLinkResult(False, error=f"Razorpay fallback failed: {order_exc}")
        else:
            return PaymentLinkResult(False, error=str(exc))


def fetch_payment_link_status(payment_link_id: str) -> dict:
    """Fetch current status of a payment link or order -- 'paid', 'created', 'expired', etc.

    Poll this (or wire the webhook) to auto-mark a RecoveryCase as recovered
    when the customer actually pays.
    """
    client = _client()
    if payment_link_id.startswith("order_"):
        ord_data = client.order.fetch(payment_link_id)
        # Normalize order status to match payment link format
        ord_status = ord_data.get("status")
        amount_paid = ord_data.get("amount_paid", 0)
        is_paid = ord_status == "paid" or (amount_paid and amount_paid > 0)

        # Extra verification: check individual payment captures for this order
        if not is_paid:
            try:
                payments = client.order.payments(payment_link_id)
                for p in payments.get("items", []):
                    if p.get("status") in ("captured", "authorized"):
                        is_paid = True
                        amount_paid = p.get("amount", amount_paid)
                        break
            except Exception:
                pass

        return {
            "id": ord_data.get("id"),
            "status": "paid" if is_paid else (ord_status or "created"),
            "amount_paid": amount_paid,
            "currency": ord_data.get("currency", "INR"),
        }
    return client.payment_link.fetch(payment_link_id)
