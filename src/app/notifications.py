import logging
import os
import smtplib
from email.message import EmailMessage

logger = logging.getLogger("mcia.notifications")


def send_email(to_address: str, subject: str, body: str) -> bool:
    """Send an email when SMTP is configured. Otherwise log it and return False."""
    smtp_host = os.getenv("SMTP_HOST")
    sender = os.getenv("SMTP_FROM")
    if not smtp_host or not sender:
        logger.warning("SMTP not configured; would email %s: %s", to_address, subject)
        return False

    message = EmailMessage()
    message["From"] = sender
    message["To"] = to_address
    message["Subject"] = subject
    message.set_content(body)

    port = int(os.getenv("SMTP_PORT", "587"))
    try:
        with smtplib.SMTP(smtp_host, port, timeout=20) as server:
            server.starttls()
            user = os.getenv("SMTP_USER")
            if user:
                server.login(user, os.getenv("SMTP_PASSWORD", ""))
            refused = server.send_message(message)
    except (OSError, smtplib.SMTPException):
        logger.exception("SMTP delivery failed for %s: %s", to_address, subject)
        return False
    if refused:
        logger.error("SMTP server refused %s for %s", to_address, subject)
        return False
    return True
