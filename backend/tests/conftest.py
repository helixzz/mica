import os
import subprocess
import sys
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

import app.db as db_module
from app.config import get_settings
from app.db import get_db
from app.main import app
from app.services.seed import seed_dev_data

TEST_DB_URL = "postgresql+asyncpg://mica:mica@localhost:5432/mica_test"

BACKEND_ROOT = Path(__file__).parent.parent


def _run_alembic_upgrade(db_url: str) -> None:
    """Run ``alembic upgrade head`` against the given database URL.

    Migrations include inline seed data (e.g. 0003 seeds system_parameters,
    0005 seeds approval_rules). Tests that exercise services reading those
    tables MUST run migrations rather than ``Base.metadata.create_all``.

    Uses a subprocess to avoid the ``asyncio.run()`` nested-loop error that
    surfaces when alembic's async env.py runs inside pytest-asyncio's event
    loop.
    """
    env = os.environ.copy()
    env["DATABASE_URL"] = db_url
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=str(BACKEND_ROOT),
        env=env,
        check=True,
    )


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def test_engine():
    engine: AsyncEngine = create_async_engine(TEST_DB_URL, echo=False)
    from sqlalchemy import text

    async with engine.begin() as conn:
        await conn.execute(text("DROP SCHEMA public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))
    _run_alembic_upgrade(TEST_DB_URL)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(loop_scope="session")
async def db_session(test_engine):
    """Per-test session wrapped in an outer transaction with savepoint rollback.

    Any ``session.commit()`` made inside the service code becomes a SAVEPOINT
    release rather than a real commit; the outer transaction is always rolled
    back at teardown, guaranteeing zero state leakage between tests.
    """
    async with test_engine.connect() as conn:
        await conn.begin()
        factory = async_sessionmaker(
            bind=conn,
            expire_on_commit=False,
            class_=AsyncSession,
            join_transaction_mode="create_savepoint",
        )
        async with factory() as session:
            yield session
        await conn.rollback()


@pytest_asyncio.fixture(loop_scope="session")
async def seeded_db_session(test_engine):
    """Like ``db_session`` but with ``seed_dev_data`` applied.

    Needed by service tests that query seed users (alice/bob/...) or
    seeded master data. Still rolls back via savepoint pattern → no
    leakage between tests.

    Also purges tables polluted by the legacy ``seeded_client`` fixture
    (which monkeypatches the global engine and truly commits rows).
    """
    from sqlalchemy import text as sql_text

    async with test_engine.begin() as conn:
        await conn.execute(sql_text("DELETE FROM notifications"))
        await conn.execute(sql_text("DELETE FROM notification_subscriptions"))

    async with test_engine.connect() as conn:
        await conn.begin()
        factory = async_sessionmaker(
            bind=conn,
            expire_on_commit=False,
            class_=AsyncSession,
            join_transaction_mode="create_savepoint",
        )
        async with factory() as session:
            await seed_dev_data(session)
            yield session
        await conn.rollback()


@pytest_asyncio.fixture(loop_scope="session")
async def client(db_session):
    """Bare HTTP client with an empty DB (schema created, no seed data).

    Uses FastAPI dependency_overrides (canonical pattern) instead of
    monkeypatching global engine references.
    """

    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as c:
            yield c
    finally:
        app.dependency_overrides.clear()


@pytest_asyncio.fixture(loop_scope="session")
async def seeded_client(test_engine, monkeypatch):
    """Legacy fixture: seeded HTTP client using monkeypatched engine.

    Kept for backward compatibility with tests written before the
    dependency_overrides pattern. Prefer the ``client`` + explicit seed
    fixtures in new tests. State IS persisted across tests using this
    fixture because seed data is committed before the client yields.
    """
    session_factory = async_sessionmaker(test_engine, expire_on_commit=False)
    async with session_factory() as session:
        await seed_dev_data(session)

    monkeypatch.setattr(db_module, "engine", test_engine)
    monkeypatch.setattr(db_module, "AsyncSessionLocal", session_factory)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as c:
        yield c


@pytest.fixture
def settings():
    return get_settings()
