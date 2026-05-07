"""API contract tests for key endpoints."""

from httpx import ASGITransport, AsyncClient

import pytest

from app.main import app


@pytest.mark.asyncio
async def test_health_returns_structured_status():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "healthy"
        assert "db" in data["checks"]


@pytest.mark.asyncio
async def test_items_endpoint_returns_paginated(seeded_client):
    r = await seeded_client.get("/api/v1/items?page=1&page_size=10")
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert "total" in data


@pytest.mark.asyncio
async def test_delivery_plans_endpoint(seeded_client):
    r = await seeded_client.get("/api/v1/delivery-plans")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_delivery_plans_overview(seeded_client):
    r = await seeded_client.get("/api/v1/delivery-plans/overview")
    assert r.status_code == 200
    data = r.json()
    assert "plans" in data


@pytest.mark.asyncio
async def test_suppliers_endpoint_returns_paginated(seeded_client):
    r = await seeded_client.get("/api/v1/suppliers?page_size=10")
    assert r.status_code == 200
    data = r.json()
    assert "items" in data


@pytest.mark.asyncio
async def test_dashboard_metrics(seeded_client):
    r = await seeded_client.get("/api/v1/dashboard/metrics")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_analytics_available(seeded_client):
    r = await seeded_client.get("/api/v1/dashboard/analytics")
    assert r.status_code == 200
