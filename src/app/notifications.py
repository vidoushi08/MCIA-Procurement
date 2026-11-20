import logging
import os
import smtplib
from email.message import EmailMessage

logger = logging.getLogger("mcia.notifications")


def smtp_configured() -> bool:
    return bool(os.getenv("SMTP_HOST") and os.getenv("SMTP_FROM"))


def send_email(to_address: str, subject: str, body: str) -> bool:
    """Send an email when SMTP is configured. Otherwise log it and return False."""
    if not smtp_configured():
        logger.warning("SMTP not configured; would email %s: %s", to_address, subject)
        return False

    message = EmailMessage()
    message["From"] = os.getenv("SMTP_FROM")
    message["To"] = to_address
    message["Subject"] = subject
    message.set_content(body)

    port = int(os.getenv("SMTP_PORT", "587"))
    with smtplib.SMTP(os.getenv("SMTP_HOST"), port, timeout=20) as server:
        server.starttls()
        user = os.getenv("SMTP_USER")
        if user:
            server.login(user, os.getenv("SMTP_PASSWORD", ""))
        server.send_message(message)
    return True
