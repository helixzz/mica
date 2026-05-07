"""API contract tests for key endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


async def _login(seeded_client, username="admin"):
    r = await seeded_client.post(
        "/api/v1/auth/login/json",
        json={"username": username, "password": "MicaDev2026!"},
    )
    assert r.status_code == 200, f"Login failed: {r.text}"
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.mark.asyncio
async def test_items_endpoint_returns_paginated(seeded_client):
    auth = await _login(seeded_client)
    r = await seeded_client.get("/api/v1/items?page=1&page_size=10", headers=auth)
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert isinstance(data["items"], list)


@pytest.mark.asyncio
async def test_delivery_plans_endpoint(seeded_client):
    auth = await _login(seeded_client)
    r = await seeded_client.get("/api/v1/delivery-plans", headers=auth)
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_health_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] in ("healthy", "degraded")
        assert "app" in data
        assert "checks" in data


@pytest.mark.asyncio
async def test_suppliers_endpoint_returns_paginated(seeded_client):
    auth = await _login(seeded_client)
    r = await seeded_client.get("/api/v1/suppliers?page_size=10", headers=auth)
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert isinstance(data["items"], list)
