"""Atomic free-tier AI request reservations for supported SQL backends."""
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as postgres_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.models.entities import AIUsageDailyCounter


def reserve_daily_request(db: Session, user_id: UUID, period_key: str, limit: int, now: datetime) -> bool:
    """Atomically increment one user's daily counter only while it is below limit."""
    if limit <= 0:
        return False
    dialect = db.bind.dialect.name
    counter = AIUsageDailyCounter.__table__
    values = {"user_id": user_id, "period_key": period_key, "request_count": 1, "updated_at": now}
    if dialect == "postgresql":
        insert = postgres_insert(counter).values(**values)
    elif dialect == "sqlite":
        insert = sqlite_insert(counter).values(**values)
    else:
        raise RuntimeError(f"Atomic AI quota reservations are unsupported for database dialect {dialect}")

    statement = insert.on_conflict_do_update(
        index_elements=[counter.c.user_id, counter.c.period_key],
        set_={"request_count": counter.c.request_count + 1, "updated_at": now},
        where=counter.c.request_count < limit,
    ).returning(counter.c.request_count)
    return db.execute(statement).scalar_one_or_none() is not None


def daily_request_count(db: Session, user_id: UUID, period_key: str) -> int:
    return int(db.scalar(select(AIUsageDailyCounter.request_count).where(
        AIUsageDailyCounter.user_id == user_id,
        AIUsageDailyCounter.period_key == period_key,
    )) or 0)
