import os

from sqlalchemy import create_engine

from app.db.base import Base
from app.models import entities  # noqa: F401


database_url = os.environ["DATABASE_URL"]
engine = create_engine(database_url)
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)
engine.dispose()
