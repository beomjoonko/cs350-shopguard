"""Shared pytest fixtures — SQLite in-memory database for full isolation.

All test files share this conftest. The `reset_db` fixture is autouse so
every test gets a clean schema. Use the `client` fixture to make HTTP
requests and the `db` fixture to set up data directly.
"""
import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient


def _ensure_test_cors_origins() -> None:
    """TC-64 (SEC-2): local .env often has HTTP-only; append HTTPS for pytest."""
    raw = os.environ.get(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:3000,https://localhost:3000",
    )
    origins = [o.strip() for o in raw.split(",") if o.strip()]
    if not any(o.startswith("https://") for o in origins):
        origins.append("https://localhost:3000")
        os.environ["CORS_ALLOWED_ORIGINS"] = ",".join(origins)


_ensure_test_cors_origins()

from app.config import get_settings

get_settings.cache_clear()

from app.main import app
from app.core.database import Base, get_db
from app.models.user import UserRole, UserStatus

# Trigger app/models/__init__.py so every ORM table is registered in Base.metadata.
# Use 'from app import models' (not 'import app.models') to avoid shadowing the
# FastAPI `app` instance imported above.
from app import models as _models  # noqa: F401

from tests.helpers import make_user, get_token

# One in-memory SQLite database shared across the entire test session.
_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
_Session = sessionmaker(bind=_engine, autocommit=False, autoflush=False)


def _override_get_db():
    db = _Session()
    try:
        yield db
    finally:
        db.close()


_SQLITE_SKIP_TABLES = {"crawl_snapshots"}  # uses MySQL LONGTEXT, not needed by any tested endpoint


@pytest.fixture(autouse=True)
def reset_db():
    """Drop and recreate all tables before each test for full isolation."""
    testable = [t for name, t in Base.metadata.tables.items() if name not in _SQLITE_SKIP_TABLES]
    Base.metadata.drop_all(bind=_engine, tables=testable)
    Base.metadata.create_all(bind=_engine, tables=testable)
    yield
    Base.metadata.drop_all(bind=_engine, tables=testable)


@pytest.fixture
def db(reset_db):  # noqa: F811 — reset_db is a pytest fixture, not a redeclaration
    """Direct SQLAlchemy session — use to seed test data."""
    session = _Session()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(reset_db):  # noqa: F811
    """FastAPI TestClient wired to the SQLite database."""
    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


# ── User / token fixtures ──────────────────────────────────────────────────

@pytest.fixture
def regular_user(db):
    return make_user(db, "user@example.com", "Passw0rd!")


@pytest.fixture
def admin_user(db):
    return make_user(db, "admin@example.com", "adminpass1", role=UserRole.ADMIN)


@pytest.fixture
def user_token(regular_user):
    return get_token(regular_user)


@pytest.fixture
def admin_token(admin_user):
    return get_token(admin_user)


@pytest.fixture
def auth_headers(user_token):
    return {"Authorization": f"Bearer {user_token}"}


@pytest.fixture
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}
