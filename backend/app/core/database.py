"""
SQLAlchemy database setup.

Provides:
  - `engine`: SQLAlchemy engine bound to Supabase PostgreSQL (per SRS §2.4)
  - `SessionLocal`: factory for short-lived sessions
  - `Base`: declarative base for all ORM models
  - `get_db()`: FastAPI dependency that yields a session per request
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=settings.DEBUG,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()


def get_db():
    """FastAPI dependency. Yields a DB session and closes it on completion."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
