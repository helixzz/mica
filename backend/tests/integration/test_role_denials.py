"""Integration tests: verify requester role is denied on protected endpoints."""

import pytest


async def _login_as(seeded_client, username: str) -> dict:
    r = await seeded_client.post(
        "/api/v1/auth/login/json",
        json={"username": username, "password": "MicaDev2026!"},
    )
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.mark.asyncio
async def test_requester_denied_on_shipment_create(seeded_client):
    auth = await _login_as(seeded_client, "bob")
    r = await seeded_client.post(
        "/api/v1/shipments",
        json={"po_id": "00000000-0000-0000-0000-000000000001", "items": []},
        headers=auth,
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_requester_denied_on_payment_create(seeded_client):
    auth = await _login_as(seeded_client, "bob")
    r = await seeded_client.post(
        "/api/v1/payments",
        json={"po_id": "00000000-0000-0000-0000-000000000001", "amount": "100"},
        headers=auth,
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_requester_denied_on_invoice_create(seeded_client):
    auth = await _login_as(seeded_client, "bob")
    r = await seeded_client.post(
        "/api/v1/invoices",
        json={
            "supplier_id": "00000000-0000-0000-0000-000000000001",
            "invoice_number": "TEST-INV",
            "invoice_date": "2026-04-01",
            "lines": [],
        },
        headers=auth,
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_requester_denied_on_approval_action(seeded_client):
    auth = await _login_as(seeded_client, "bob")
    r = await seeded_client.post(
        "/api/v1/approval/tasks/00000000-0000-0000-0000-000000000001/action",
        json={"decision": "approved", "comment": "test denial"},
        headers=auth,
    )
    assert r.status_code in (403, 404, 422)


@pytest.mark.asyncio
async def test_admin_can_create_payment(seeded_client):
    auth = await _login_as(seeded_client, "admin")
    r = await seeded_client.get("/api/v1/suppliers", headers=auth)
    suppliers = r.json()
    assert len(suppliers) > 0

    r = await seeded_client.get("/api/v1/purchase-orders", headers=auth)
    pos = r.json()
    if not pos:
        pytest.skip("No POs in seed — cannot test payment creation")

    po_id = pos[0]["id"]
    r = await seeded_client.post(
        "/api/v1/payments",
        json={"po_id": po_id, "amount": "10", "contract_id": None},
        headers=auth,
    )
    assert r.status_code == 201, f"Payment create failed: {r.text}"


@pytest.mark.asyncio
async def test_requester_denied_on_shipment_list(seeded_client):
    auth = await _login_as(seeded_client, "bob")
    r = await seeded_client.get("/api/v1/shipments", headers=auth)
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_requester_denied_on_contract_edit(seeded_client):
    auth = await _login_as(seeded_client, "bob")
    r = await seeded_client.patch(
        "/api/v1/contracts/00000000-0000-0000-0000-000000000001",
        json={"title": "hack"},
        headers=auth,
    )
    assert r.status_code == 403
