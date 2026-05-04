"""Simple SMTP email sender using Python's smtplib.

No external dependency needed. Reads SMTP configuration from system_parameters.
All send failures are logged and swallowed — email is fire-and-forget.
"""

from __future__ import annotations

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.system_params import system_params

logger = logging.getLogger("mica.email")


async def send_email(
    db: AsyncSession,
    to_email: str,
    subject: str,
    body: str,
) -> bool:
    """Send an HTML email via SMTP. Returns True on success, False on failure.

    Reads SMTP config from system_parameters (email.* keys).
    Non-blocking in practice — failures are logged and swallowed.
    """
    enabled = await system_params.get(db, "email.enabled", False)
    if not enabled:
        return False

    smtp_host = await system_params.get(db, "email.smtp_host", "")
    smtp_port = int(await system_params.get(db, "email.smtp_port", 587))
    smtp_user = await system_params.get(db, "email.smtp_user", "")
    smtp_pass = await system_params.get(db, "email.smtp_password", "")

    if not smtp_host:
        return False

    msg = MIMEMultipart()
    msg["From"] = smtp_user or "mica@localhost"
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "html"))

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
            server.starttls()
            if smtp_user:
                server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        return True
    except Exception:
        logger.warning("Failed to send email to %s", to_email, exc_info=True)
        return False
