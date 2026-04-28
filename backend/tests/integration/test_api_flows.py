"""Integration tests: exercise the HTTP layer with a real database.

These tests complement unit tests by covering the full request→response cycle,
including FastAPI middleware, Pydantic response_model validation, Cerbos
authorization, and Alembic-seeded system parameters.

Uses pytest-asyncio with seeded_client (uses test_walking_skeleton fixture).
"""

from decimal import Decimal

import pytest


async def _login_as(seeded_client, username: str) -> dict:
    """Return {Authorization, headers} for the given seed user."""
    r = await seeded_client.post(
        "/api/v1/auth/login/json",
        json={"username": username, "password": "MicaDev2026!"},
    )
    assert r.status_code == 200, f"Login failed: {r.text}"
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_health_returns_structured_status(seeded_client):
    r = await seeded_client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] in ("healthy", "degraded")
    assert data["app"] == "Mica"
    assert isinstance(data["checks"], dict)
    assert "db" in data["checks"]


@pytest.mark.asyncio
async def test_dashboard_metrics_includes_invoice_counts(seeded_client):
    auth = await _login_as(seeded_client, "admin")
    r = await seeded_client.get("/api/v1/dashboard/metrics", headers=auth)
    assert r.status_code == 200
    data = r.json()
    assert "invoices_pending_match" in data
    assert "invoices_mismatched" in data
    assert isinstance(data["invoices_pending_match"], int)
    assert isinstance(data["invoices_mismatched"], int)


@pytest.mark.asyncio
async def test_pr_convert_single_supplier(seeded_client):
    """Create PR, convert if already approved, else verify preview works."""
    auth = await _login_as(seeded_client, "alice")

    r = await seeded_client.get("/api/v1/suppliers", headers=auth)
    suppliers = r.json()
    assert len(suppliers) > 0
    supplier_id = suppliers[0]["id"]

    pr_payload = {
        "title": "Integration test PR",
        "business_reason": "Integration test",
        "currency": "CNY",
        "items": [
            {
                "line_no": 1,
                "item_name": "Integration test item",
                "qty": "2",
                "unit_price": "100",
                "supplier_id": supplier_id,
            }
        ],
    }
    r = await seeded_client.post(
        "/api/v1/purchase-requisitions", json=pr_payload, headers=auth
    )
    assert r.status_code == 201, f"Create PR failed: {r.text}"
    pr = r.json()
    pr_id = pr["id"]

    r = await seeded_client.get(
        f"/api/v1/purchase-requisitions/{pr_id}/conversion-preview", headers=auth
    )

    if r.status_code == 200:
        preview = r.json()
        assert isinstance(preview, list)
        assert len(preview) == 1
        r = await seeded_client.post(
            f"/api/v1/purchase-requisitions/{pr_id}/convert-to-po", headers=auth
        )
        if r.status_code == 201:
            pos = r.json()
            assert isinstance(pos, list)
            assert len(pos) >= 1
            assert pos[0]["po_number"].startswith("PO-")
    else:
        assert r.status_code in (409,)


@pytest.mark.asyncio
async def test_save_invalid_company_code_rejected(seeded_client):
    """v0.9.26 regression: admin cannot save a non-existent company code."""
    auth = await _login_as(seeded_client, "admin")

    r = await seeded_client.put(
        "/api/v1/admin/system-params/auth.saml.jit.default_company_code",
        json={"value": "DOES-NOT-EXIST"},
        headers=auth,
    )
    assert r.status_code == 400, f"Expected 400, got {r.status_code}: {r.text}"


@pytest.mark.asyncio
async def test_payment_forecast_returns_monthly_data(seeded_client):
    auth = await _login_as(seeded_client, "admin")
    r = await seeded_client.get(
        "/api/v1/dashboard/payment-forecast?months=3", headers=auth
    )
    assert r.status_code == 200
    data = r.json()
    assert "months" in data
    assert isinstance(data["months"], list)
    assert "grand_planned" in data
    assert "grand_paid" in data


@pytest.mark.asyncio
async def test_invoice_forecast_returns_monthly_data(seeded_client):
    auth = await _login_as(seeded_client, "admin")
    r = await seeded_client.get(
        "/api/v1/dashboard/invoice-forecast?months=3", headers=auth
    )
    assert r.status_code == 200
    data = r.json()
    assert "months" in data
    assert isinstance(data["months"], list)
    assert "grand_invoiceable_to_date" in data
    assert "grand_invoiced_to_date" in data
    assert "grand_pending_to_date" in data


@pytest.mark.asyncio
async def test_po_list_includes_supplier_fields(seeded_client):
    auth = await _login_as(seeded_client, "admin")
    r = await seeded_client.get("/api/v1/purchase-orders", headers=auth)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    if len(data) > 0:
        po = data[0]
        assert "pr_number" in po
        assert "supplier_name" in po
        assert "created_at" in po


@pytest.mark.asyncio
async def test_user_crud_with_cost_center_ids(seeded_client):
    auth = await _login_as(seeded_client, "admin")

    r = await seeded_client.get("/api/v1/companies?include_disabled=false", headers=auth)
    companies = r.json()
    company_id = companies[0]["id"]

    r = await seeded_client.get("/api/v1/departments", headers=auth)
    departments = r.json()

    user_payload = {
        "username": "ittest_ccuser2",
        "email": "ittest_cc2@test.local",
        "display_name": "CC Test User 2",
        "password": "Test123456789!",
        "role": "requester",
        "company_id": company_id,
        "preferred_locale": "zh-CN",
        "cost_center_ids": [],
        "department_ids": [d["id"] for d in departments[:1]] if departments else [],
    }
    r = await seeded_client.post(
        "/api/v1/admin/users", json=user_payload, headers=auth
    )
    assert r.status_code == 201, f"Create user failed: {r.text}"
    user = r.json()
    assert "cost_center_ids" in user
    assert isinstance(user["cost_center_ids"], list)
    assert "department_ids" in user
    assert isinstance(user["department_ids"], list)
