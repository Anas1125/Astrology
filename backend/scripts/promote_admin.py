"""Promote an existing local-development account to ADMIN after explicit confirmation."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlalchemy import create_engine, select  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.models.entities import User  # noqa: E402


def main() -> int:
    if settings.app_env != "development":
        print("Refusing to change roles outside APP_ENV=development.")
        return 2
    email = input("Existing account email to promote: ").strip().casefold()
    if not email:
        print("An email is required.")
        return 2
    print(f"This will grant ADMIN privileges to {email} in the configured local database.")
    if input(f"Type the exact email to confirm ({email}): ").strip().casefold() != email:
        print("Confirmation did not match; no changes made.")
        return 1
    connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
    engine = create_engine(settings.database_url, connect_args=connect_args)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    try:
        with SessionLocal() as db:
            user = db.scalar(select(User).where(User.email == email))
            if user is None:
                print("No account with that email exists. Register or log in first.")
                return 1
            if user.role.upper() == "ADMIN":
                print("This account is already an ADMIN.")
                return 0
            user.role = "ADMIN"
            db.commit()
            print(f"Promoted {email} to ADMIN. Existing password and account data were not changed.")
            return 0
    finally:
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
