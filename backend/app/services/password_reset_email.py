"""Password reset delivery through configured SMTP or an explicit local dev file."""
from email.message import EmailMessage
import os
import smtplib
import ssl
from pathlib import Path

from app.core.config import settings


def deliver_reset_link(email: str, reset_url: str) -> None:
    if settings.password_reset_local_file_configured:
        path = Path(settings.password_reset_dev_token_file or "")
        path.parent.mkdir(parents=True, exist_ok=True)
        file_descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        try:
            with os.fdopen(file_descriptor, "w", encoding="utf-8") as descriptor:
                descriptor.write(reset_url + "\n")
                descriptor.flush()
        finally:
            try:
                os.close(file_descriptor)
            except OSError:
                pass
        return

    if not settings.password_reset_email_configured:
        raise RuntimeError("Password reset delivery is not configured")

    message = EmailMessage()
    message["Subject"] = "Reset your AstroAI password"
    message["From"] = settings.password_reset_smtp_sender
    message["To"] = email
    message.set_content(
        "A password reset was requested for your AstroAI account.\n\n"
        f"Use this link within 30 minutes: {reset_url}\n\n"
        "If you did not request this, you can ignore this message."
    )
    with smtplib.SMTP(settings.password_reset_smtp_host, settings.password_reset_smtp_port, timeout=10) as server:
        if settings.password_reset_smtp_starttls:
            server.starttls(context=ssl.create_default_context())
        if settings.password_reset_smtp_username:
            server.login(settings.password_reset_smtp_username, settings.password_reset_smtp_password or "")
        server.send_message(message)
