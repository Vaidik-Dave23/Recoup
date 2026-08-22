"""Optional SMTP delivery for recovery outreach."""

from __future__ import annotations

import smtplib
from dataclasses import dataclass
from email.message import EmailMessage

from app.core.config import settings


@dataclass
class EmailSendResult:
    success: bool
    provider_ref: str | None
    error: str | None = None


def send_recovery_email(to_email: str, subject: str, body: str) -> EmailSendResult:
    if not settings.smtp_host or not settings.smtp_from_email:
        return EmailSendResult(False, None, "SMTP is not configured")

    message = EmailMessage()
    message["Subject"] = subject or "Regarding your recent payment"
    message["From"] = settings.smtp_from_email
    message["To"] = to_email
    message.set_content(body)

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as server:
            if settings.smtp_use_tls:
                server.starttls()
            if settings.smtp_username and settings.smtp_password:
                server.login(settings.smtp_username, settings.smtp_password)
            server.send_message(message)
    except Exception as exc:  # noqa: BLE001
        return EmailSendResult(False, None, str(exc))

    return EmailSendResult(True, message.get("Message-Id") or f"smtp-sent-{to_email}")
