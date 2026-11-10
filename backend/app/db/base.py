from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from app.core.config import settings


class Base(DeclarativeBase):
    pass


def normalize_database_url(raw_url: str):
    """Normalize Neon URLs for psycopg and drop Prisma-only pgbouncer metadata."""
    if raw_url.startswith("postgresql://"):
        raw_url = raw_url.replace("postgresql://", "postgresql+psycopg://", 1)
    elif raw_url.startswith("postgres://"):
        raw_url = raw_url.replace("postgres://", "postgresql+psycopg://", 1)
    parsed_url = make_url(raw_url)
    query = dict(parsed_url.query)
    query.pop("pgbouncer", None)
    return parsed_url.set(query=query)


database_url = normalize_database_url(settings.database_url)
engine = create_engine(database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db():
    with SessionLocal() as session:
        yield session
