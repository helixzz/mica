# pyright: reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnusedCallResult=false
"""API-level tests for the delivery address book endpoints.

These exercise the real router — auth guard, query parsing, status codes and
response serialisation — against the service layer, on the savepoint-rolled-back
``seeded_db_session`` so nothing leaks between tests.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any
from uuid import uuid4

from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.security import create_access_token
from app.db import get_db
from app.main import app
from app.models import User


def _auth_headers(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(subject=str(user.id))}"}


@asynccontextmanager
async def _client(db):
    """HTTP client bound to *db*, restoring the override on exit.

    Leaving ``app.dependency_overrides`` populated leaks a closed session into
    every later test module.
    """

    async def _override_get_db():
        yield db

    app.dependency_overrides[get_db] = _override_get_db
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            yield client
    finally:
        app.dependency_overrides.pop(get_db, None)


async def _user(db, username: str) -> User:
    return (await db.execute(select(User).where(User.username == username))).scalar_one()


def _payload(**over: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "contact_name": "张伟",
        "contact_phone": "138 0000 0000",
        "detail": "上海市浦东新区张江高科技园区 88 号 5 层机房",
    }
    base.update(over)
    return base


async def test_full_lifecycle_over_http(seeded_db_session):
    db = seeded_db_session
    alice = await _user(db, "alice")

    async with _client(db) as client:
        created = await client.post(
            "/api/v1/delivery-addresses",
            json=_payload(label="我的地址"),
            headers=_auth_headers(alice),
        )
        assert created.status_code == 201, created.text
        body = created.json()
        assert body["contact_name"] == "张伟"
        assert body["label"] == "我的地址"
        assert body["is_shared"] is False
        assert body["usage_count"] == 0
        address_id = body["id"]

        listed = await client.get("/api/v1/delivery-addresses", headers=_auth_headers(alice))
        assert listed.status_code == 200
        assert [a["id"] for a in listed.json()] == [address_id]

        patched = await client.patch(
            f"/api/v1/delivery-addresses/{address_id}",
            json={"detail": "北京市海淀区中关村大街 1 号"},
            headers=_auth_headers(alice),
        )
        assert patched.status_code == 200
        assert patched.json()["detail"] == "北京市海淀区中关村大街 1 号"
        # ``label`` was absent from the payload, so it survives the update.
        assert patched.json()["label"] == "我的地址"

        removed = await client.delete(
            f"/api/v1/delivery-addresses/{address_id}", headers=_auth_headers(alice)
        )
        assert removed.status_code == 204

        after = await client.get("/api/v1/delivery-addresses", headers=_auth_headers(alice))
        assert after.json() == []


async def test_plain_user_cannot_create_a_shared_entry(seeded_db_session):
    db = seeded_db_session
    alice = await _user(db, "alice")

    async with _client(db) as client:
        resp = await client.post(
            "/api/v1/delivery-addresses",
            json=_payload(is_shared=True),
            headers=_auth_headers(alice),
        )

    assert resp.status_code == 403
    assert resp.json()["code"] == "address.shared_requires_role"


async def test_procurement_manager_creates_a_shared_entry_everyone_can_read(seeded_db_session):
    db = seeded_db_session
    dave = await _user(db, "dave")
    alice = await _user(db, "alice")

    async with _client(db) as client:
        created = await client.post(
            "/api/v1/delivery-addresses",
            json=_payload(label="张江机房", is_shared=True),
            headers=_auth_headers(dave),
        )
        assert created.status_code == 201, created.text
        assert created.json()["is_shared"] is True
        assert created.json()["owner_id"] is None

        listed = await client.get("/api/v1/delivery-addresses", headers=_auth_headers(alice))
        assert listed.status_code == 200
        assert [a["id"] for a in listed.json()] == [created.json()["id"]]


async def test_a_private_entry_stays_invisible_to_other_users(seeded_db_session):
    db = seeded_db_session
    alice = await _user(db, "alice")
    bob = await _user(db, "bob")

    async with _client(db) as client:
        created = await client.post(
            "/api/v1/delivery-addresses", json=_payload(), headers=_auth_headers(alice)
        )
        address_id = created.json()["id"]

        listed = await client.get("/api/v1/delivery-addresses", headers=_auth_headers(bob))
        assert listed.json() == []

        # Bob cannot even learn that the id exists.
        touched = await client.patch(
            f"/api/v1/delivery-addresses/{address_id}",
            json={"detail": "x"},
            headers=_auth_headers(bob),
        )

    assert touched.status_code == 404
    assert touched.json()["code"] == "address.not_found"


async def test_unknown_entry_returns_404(seeded_db_session):
    db = seeded_db_session
    alice = await _user(db, "alice")

    async with _client(db) as client:
        resp = await client.patch(
            f"/api/v1/delivery-addresses/{uuid4()}",
            json={"detail": "x"},
            headers=_auth_headers(alice),
        )

    assert resp.status_code == 404
    assert resp.json()["code"] == "address.not_found"


async def test_unauthenticated_requests_are_rejected(seeded_db_session):
    db = seeded_db_session

    async with _client(db) as client:
        listed = await client.get("/api/v1/delivery-addresses")
        created = await client.post("/api/v1/delivery-addresses", json=_payload())

    assert listed.status_code == 401
    assert created.status_code == 401
