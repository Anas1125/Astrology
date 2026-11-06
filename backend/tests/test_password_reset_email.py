import os

from app.core.config import settings
from app.services.password_reset_email import deliver_reset_link


def test_local_development_delivery_writes_private_link_file(monkeypatch, tmp_path):
    path = tmp_path / "nested" / "reset-link.txt"
    monkeypatch.setattr(settings, "app_env", "development")
    monkeypatch.setattr(settings, "password_reset_dev_token_file", str(path))
    deliver_reset_link("person@example.test", "http://localhost:5173/reset-password#token=secret-test-token")
    assert path.read_text() == "http://localhost:5173/reset-password#token=secret-test-token\n"
    assert os.stat(path).st_mode & 0o077 == 0


def test_smtp_delivery_uses_tls_and_configured_sender(monkeypatch):
    import app.services.password_reset_email as mailer

    calls = []

    class FakeSMTP:
        def __init__(self, host, port, timeout): calls.append(("connect", host, port, timeout))
        def __enter__(self): return self
        def __exit__(self, *args): calls.append(("close",))
        def starttls(self, **kwargs): calls.append(("starttls", bool(kwargs.get("context"))))
        def login(self, username, password): calls.append(("login", username, password))
        def send_message(self, message): calls.append(("send", message["From"], message["To"], message.get_content()))

    monkeypatch.setattr(settings, "app_env", "production")
    monkeypatch.setattr(settings, "password_reset_dev_token_file", None)
    monkeypatch.setattr(settings, "password_reset_smtp_host", "mail.example.test")
    monkeypatch.setattr(settings, "password_reset_smtp_port", 587)
    monkeypatch.setattr(settings, "password_reset_smtp_username", "smtp-user")
    monkeypatch.setattr(settings, "password_reset_smtp_password", "smtp-secret")
    monkeypatch.setattr(settings, "password_reset_smtp_sender", "AstroAI <no-reply@example.test>")
    monkeypatch.setattr(settings, "password_reset_smtp_starttls", True)
    monkeypatch.setattr(mailer.smtplib, "SMTP", FakeSMTP)
    deliver_reset_link("person@example.test", "https://astroai.test/reset-password#token=opaque")
    assert calls[0] == ("connect", "mail.example.test", 587, 10)
    assert calls[1][0] == "starttls" and calls[1][1]
    assert calls[2] == ("login", "smtp-user", "smtp-secret")
    assert calls[3][0:3] == ("send", "AstroAI <no-reply@example.test>", "person@example.test")
    assert "https://astroai.test/reset-password#token=opaque" in calls[3][3]
