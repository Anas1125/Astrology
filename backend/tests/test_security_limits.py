from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from types import SimpleNamespace

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.entities import SecurityRateLimitBucket
from app.services.security_limits import client_ip_for_rate_limit, consume_rate_limit
from app.core.config import settings


def test_limit_is_atomic_and_shared_between_database_sessions(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'limits.sqlite3'}", connect_args={"timeout": 20})
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    now = datetime(2026, 11, 3, 12, 0, tzinfo=timezone.utc)

    def attempt(_):
        with sessions() as db:
            return consume_rate_limit(db, "chat:user:account-a", limit=5, window_seconds=60, now=now)

    with ThreadPoolExecutor(max_workers=10) as pool:
        accepted = list(pool.map(attempt, range(20)))
    assert sum(accepted) == 5
    with sessions() as db:
        bucket = db.scalar(select(SecurityRateLimitBucket))
        assert bucket.request_count == 5
        assert "account-a" not in bucket.key_hash
        assert consume_rate_limit(db, "chat:user:account-b", limit=5, window_seconds=60, now=now)
    engine.dispose()


def test_limit_resets_in_next_fixed_window(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'windows.sqlite3'}")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    first = datetime(2026, 11, 3, 12, 0, 30, tzinfo=timezone.utc)
    next_window = datetime(2026, 11, 3, 12, 1, 0, tzinfo=timezone.utc)
    with sessions() as db:
        assert consume_rate_limit(db, "reset:ip:local", limit=1, window_seconds=60, now=first)
        assert not consume_rate_limit(db, "reset:ip:local", limit=1, window_seconds=60, now=first)
        assert consume_rate_limit(db, "reset:ip:local", limit=1, window_seconds=60, now=next_window)
    engine.dispose()


def test_forwarded_client_ip_is_used_only_for_explicitly_trusted_proxy(monkeypatch):
    request = SimpleNamespace(
        client=SimpleNamespace(host="10.0.0.2"),
        headers={"x-forwarded-for": "198.51.100.8, 10.0.0.1"},
    )
    monkeypatch.setattr(settings, "trusted_proxy_ips", "")
    assert client_ip_for_rate_limit(request) == "10.0.0.2"
    monkeypatch.setattr(settings, "trusted_proxy_ips", "10.0.0.2")
    assert client_ip_for_rate_limit(request) == "198.51.100.8"
    request.headers["x-forwarded-for"] = "not-an-ip"
    assert client_ip_for_rate_limit(request) == "10.0.0.2"
