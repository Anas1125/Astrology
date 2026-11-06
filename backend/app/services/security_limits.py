"""Database-shared fixed-window abuse limits for supported SQL backends."""
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import ipaddress
from threading import Lock
from uuid import uuid4

from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert as postgres_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.entities import SecurityRateLimitBucket

_cleanup_lock = Lock()
_last_cleanup_hour_by_database: dict[str, str] = {}


def _key_hash(key: str) -> str:
    return hmac.new(settings.secret_key.encode(), key.encode(), hashlib.sha256).hexdigest()


def consume_rate_limit(db: Session, key: str, *, limit: int, window_seconds: int, now: datetime | None = None) -> bool:
    """Atomically consume a slot; identifiers are HMACed before persistence."""
    if limit < 1 or window_seconds < 1:
        return False
    current = now or datetime.now(timezone.utc)
    database_key = str(db.bind.url)
    cleanup_hour = current.strftime("%Y-%m-%dT%H")
    with _cleanup_lock:
        if _last_cleanup_hour_by_database.get(database_key) != cleanup_hour:
            db.execute(delete(SecurityRateLimitBucket).where(
                SecurityRateLimitBucket.window_start < current - timedelta(days=2)
            ))
            _last_cleanup_hour_by_database[database_key] = cleanup_hour
    epoch = int(current.timestamp())
    start = datetime.fromtimestamp(epoch - epoch % window_seconds, timezone.utc)
    table = SecurityRateLimitBucket.__table__
    values = {
        "id": uuid4(),
        "key_hash": _key_hash(key),
        "window_start": start,
        "request_count": 1,
        "updated_at": current,
    }
    dialect = db.bind.dialect.name
    if dialect == "postgresql":
        insert = postgres_insert(table).values(**values)
    elif dialect == "sqlite":
        insert = sqlite_insert(table).values(**values)
    else:
        raise RuntimeError(f"Atomic security rate limits are unsupported for database dialect {dialect}")
    statement = insert.on_conflict_do_update(
        index_elements=[table.c.key_hash, table.c.window_start],
        set_={"request_count": table.c.request_count + 1, "updated_at": current},
        where=table.c.request_count < limit,
    ).returning(table.c.request_count)
    accepted = db.execute(statement).scalar_one_or_none() is not None
    db.commit()
    return accepted


def bucket_window_start(now: datetime, window_seconds: int) -> datetime:
    """Exposed for tests and operational inspection without exposing a key."""
    epoch = int(now.timestamp())
    return datetime.fromtimestamp(epoch - epoch % window_seconds, timezone.utc)


def client_ip_for_rate_limit(request) -> str:
    """Use forwarded client IP only when the direct peer is explicitly trusted."""
    peer = request.client.host if request.client else "unknown"
    if peer not in settings.trusted_proxy_ip_list:
        return peer
    forwarded = request.headers.get("x-forwarded-for", "").split(",", 1)[0].strip()
    try:
        return str(ipaddress.ip_address(forwarded))
    except ValueError:
        return peer
