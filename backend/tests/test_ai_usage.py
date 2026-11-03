from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.entities import AIUsageDailyCounter, User
from app.services.ai.usage import daily_request_count, reserve_daily_request


def test_daily_quota_reservations_are_atomic_and_user_scoped(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'quota.sqlite3'}",
        connect_args={"check_same_thread": False, "timeout": 10},
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    first_user, second_user = uuid4(), uuid4()
    with Session.begin() as session:
        session.add_all([
            User(id=first_user, email="quota-a@example.com", password_hash="unused"),
            User(id=second_user, email="quota-b@example.com", password_hash="unused"),
        ])

    def reserve(user_id):
        with Session() as session:
            accepted = reserve_daily_request(session, user_id, "2026-11-03", 1, datetime.now(timezone.utc))
            if accepted:
                session.commit()
            else:
                session.rollback()
            return accepted

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(reserve, [first_user, first_user]))
    assert sorted(results) == [False, True]
    assert reserve(second_user) is True
    with Session() as session:
        assert daily_request_count(session, first_user, "2026-11-03") == 1
        assert daily_request_count(session, second_user, "2026-11-03") == 1
        assert session.query(AIUsageDailyCounter).count() == 2
    engine.dispose()
