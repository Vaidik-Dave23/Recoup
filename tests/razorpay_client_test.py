"""Unit test for app.agent.razorpay_client -- no DB, no network, no real keys.

Unlike the other files in tests/ (which are async smoke tests that hit a
running app + Postgres), this one only exercises create_recovery_payment_link
in isolation by mocking the razorpay SDK. Run it directly:

    python -m tests.razorpay_client_test

It intentionally does NOT import app.main, so it also works before the DB
or GEMINI_API_KEY are configured -- only RAZORPAY_KEY_ID/SECRET matter, and
even those are monkeypatched per-case below.
"""

from __future__ import annotations

from unittest.mock import patch

import razorpay

from app.agent.razorpay_client import create_recovery_payment_link, fetch_payment_link_status
from app.core.config import settings


def _check(label: str, condition: bool) -> None:
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {label}")
    assert condition, label


def test_missing_keys_fail_gracefully() -> None:
    with patch.object(settings, "razorpay_key_id", ""), patch.object(
        settings, "razorpay_key_secret", ""
    ):
        result = create_recovery_payment_link(
            amount=49900,
            currency="INR",
            description="test",
            customer_name="Test User",
            customer_email="test@example.com",
            reference_id="case-1-attempt-1",
        )
    _check("missing keys -> success is False", result.success is False)
    _check("missing keys -> error message set", bool(result.error))
    _check("missing keys -> no link id", result.payment_link_id is None)


def test_missing_customer_email_fails_gracefully() -> None:
    with patch.object(settings, "razorpay_key_id", "rzp_test_fake"), patch.object(
        settings, "razorpay_key_secret", "fake_secret"
    ):
        result = create_recovery_payment_link(
            amount=49900,
            currency="INR",
            description="test",
            customer_name="Test User",
            customer_email=None,
            reference_id="case-1-attempt-1",
        )
    _check("no customer email -> success is False", result.success is False)
    _check("no customer email -> error mentions email", "email" in (result.error or "").lower())


def test_successful_link_creation_parses_response() -> None:
    fake_response = {
        "id": "plink_FAKE123",
        "short_url": "https://rzp.io/i/fake123",
        "status": "created",
    }
    with patch.object(settings, "razorpay_key_id", "rzp_test_fake"), patch.object(
        settings, "razorpay_key_secret", "fake_secret"
    ), patch("app.agent.razorpay_client._client") as mock_client_factory:
        mock_client_factory.return_value.payment_link.create.return_value = fake_response
        result = create_recovery_payment_link(
            amount=49900,
            currency="INR",
            description="payment_failed recovery -- case abcd1234",
            customer_name="Test User",
            customer_email="test@example.com",
            reference_id="case-1-attempt-1",
        )

    _check("success path -> success is True", result.success is True)
    _check("success path -> payment_link_id parsed", result.payment_link_id == "plink_FAKE123")
    _check(
        "success path -> short_url parsed",
        result.short_url == "https://rzp.io/i/fake123",
    )

    call_kwargs = mock_client_factory.return_value.payment_link.create.call_args[0][0]
    _check("payload -> amount passed through", call_kwargs["amount"] == 49900)
    _check("payload -> currency uppercased", call_kwargs["currency"] == "INR")
    _check(
        "payload -> reference_id passed through",
        call_kwargs["reference_id"] == "case-1-attempt-1",
    )
    _check(
        "payload -> customer email passed through",
        call_kwargs["customer"]["email"] == "test@example.com",
    )
    _check("payload -> no unsolicited notify", call_kwargs["notify"] == {"email": False, "sms": False})


def test_bad_request_from_razorpay_fails_gracefully() -> None:
    with patch.object(settings, "razorpay_key_id", "rzp_test_fake"), patch.object(
        settings, "razorpay_key_secret", "fake_secret"
    ), patch("app.agent.razorpay_client._client") as mock_client_factory:
        mock_client_factory.return_value.payment_link.create.side_effect = (
            razorpay.errors.BadRequestError("invalid currency")
        )
        result = create_recovery_payment_link(
            amount=49900,
            currency="INR",
            description="test",
            customer_name="Test User",
            customer_email="test@example.com",
            reference_id="case-1-attempt-1",
        )
    _check("bad request -> success is False", result.success is False)
    _check("bad request -> error surfaced, no exception raised", "invalid currency" in (result.error or ""))


def test_unexpected_error_is_caught_not_raised() -> None:
    with patch.object(settings, "razorpay_key_id", "rzp_test_fake"), patch.object(
        settings, "razorpay_key_secret", "fake_secret"
    ), patch("app.agent.razorpay_client._client") as mock_client_factory:
        mock_client_factory.return_value.payment_link.create.side_effect = ConnectionError(
            "network down"
        )
        result = create_recovery_payment_link(
            amount=49900,
            currency="INR",
            description="test",
            customer_name="Test User",
            customer_email="test@example.com",
            reference_id="case-1-attempt-1",
        )
    _check("network error -> success is False", result.success is False)
    _check("network error -> error surfaced", "network down" in (result.error or ""))


def test_fetch_status_delegates_to_sdk() -> None:
    with patch.object(settings, "razorpay_key_id", "rzp_test_fake"), patch.object(
        settings, "razorpay_key_secret", "fake_secret"
    ), patch("app.agent.razorpay_client._client") as mock_client_factory:
        mock_client_factory.return_value.payment_link.fetch.return_value = {
            "id": "plink_FAKE123",
            "status": "paid",
        }
        status = fetch_payment_link_status("plink_FAKE123")
    _check(
        "fetch -> delegates with correct id",
        mock_client_factory.return_value.payment_link.fetch.call_args[0][0] == "plink_FAKE123",
    )
    _check("fetch -> returns SDK response", status["status"] == "paid")


def main() -> None:
    test_missing_keys_fail_gracefully()
    test_missing_customer_email_fails_gracefully()
    test_successful_link_creation_parses_response()
    test_bad_request_from_razorpay_fails_gracefully()
    test_unexpected_error_is_caught_not_raised()
    test_fetch_status_delegates_to_sdk()
    print("\nAll razorpay_client tests passed.")


if __name__ == "__main__":
    main()
