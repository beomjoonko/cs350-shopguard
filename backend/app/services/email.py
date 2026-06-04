"""Outbound email — SRS §3.4 / §4.1 REQ-2."""
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.config import settings

logger = logging.getLogger(__name__)


def send_password_reset_email(to_email: str, reset_url: str) -> None:
    """Send reset link. Without SMTP_HOST, log the link (dev/tests)."""
    if not settings.SMTP_HOST:
        logger.info("Password reset for %s: %s", to_email, reset_url)
        return

    subject = f"{settings.APP_NAME} — Reset your password"
    text = (
        f"You requested a password reset for {settings.APP_NAME}.\n\n"
        f"Open this link (valid for {settings.PASSWORD_RESET_EXPIRE_MINUTES} minutes):\n"
        f"{reset_url}\n\n"
        "If you did not request this, ignore this email."
    )
    html = (
        f"<p>You requested a password reset for <strong>{settings.APP_NAME}</strong>.</p>"
        f'<p><a href="{reset_url}">Reset your password</a></p>'
        f"<p>This link expires in {settings.PASSWORD_RESET_EXPIRE_MINUTES} minutes.</p>"
        "<p>If you did not request this, you can ignore this email.</p>"
    )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.SMTP_FROM
    msg["To"] = to_email
    msg.attach(MIMEText(text, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as smtp:
        if settings.SMTP_USER and settings.SMTP_PASSWORD:
            smtp.starttls()
            smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        smtp.sendmail(settings.SMTP_FROM, [to_email], msg.as_string())
