"""
SQLAlchemy database setup for EchoFrame France Subrental.

SQLite for the MVP — file lives at the path in DATABASE_URL. The schema
maps cleanly to Postgres so the move-up is a URL change plus an
alembic migration. Sessions are dependency-injected through FastAPI.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from config import settings


# SQLite needs check_same_thread=False because FastAPI's threaded
# request handlers create sessions on demand. For Postgres this kwarg
# is silently ignored.
_engine_kwargs: dict = {"future": True}
if settings.database_url.startswith("sqlite"):
    _engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(settings.database_url, **_engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""

    pass


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a DB session and closes it after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def db_session() -> Generator[Session, None, None]:
    """Standalone context manager for non-request code (seeders, scripts)."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db() -> None:
    """Create all tables. Called once at app startup."""
    from models import db_models  # noqa: F401  (registers models with Base)
    Base.metadata.create_all(bind=engine)
