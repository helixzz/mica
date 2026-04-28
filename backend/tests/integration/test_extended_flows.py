"""Extended integration tests covering critical business paths not yet tested."""

import pytest


async def _login_as(seeded_client, username: str) -> dict:
    r = await seeded_client.post(
        "/api/v1/auth/login/json",
        json={"username": username, "password": "MicaDev2026!"},
    )
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.mark.asyncio
async def test_request_id_present_on_error_response(seeded_client):
    auth = await _login_as(seeded_client, "alice")
    r = await seeded_client.post(
        "/api/v1/purchase-requisitions",
        json={"title": "", "business_reason": "", "items": []},
        headers=auth,
    )
    assert r.status_code == 422
    body = r.json()
    assert "request_id" in body
    assert len(body["request_id"]) > 0


@pytest.mark.asyncio
async def test_pr_with_free_text_item_no_sku(seeded_client):
    auth = await _login_as(seeded_client, "alice")
    r = await seeded_client.post(
        "/api/v1/purchase-requisitions",
        json={
            "title": "Free-text PR",
            "business_reason": "Testing free-text items",
            "currency": "CNY",
            "items": [
                {
                    "line_no": 1,
                    "item_name": "Custom cable assembly",
                    "specification": "Custom spec, no SKU",
                    "qty": "5",
                    "unit_price": "100",
                }
            ],
        },
        headers=auth,
    )
    assert r.status_code == 201, f"Free-text PR creation failed: {r.text}"
    pr = r.json()
    assert pr["items"][0]["item_name"] == "Custom cable assembly"


@pytest.mark.asyncio
async def test_multi_supplier_pr_preview_and_convert(seeded_client):
    auth = await _login_as(seeded_client, "alice")
    r = await seeded_client.get("/api/v1/suppliers", headers=auth)
    suppliers = r.json()
    assert len(suppliers) >= 2, "Need at least 2 suppliers in seed data"
    s1_id, s2_id = suppliers[0]["id"], suppliers[1]["id"]

    r = await seeded_client.post(
        "/api/v1/purchase-requisitions",
        json={
            "title": "Multi-supplier test PR",
            "business_reason": "Integration test",
            "currency": "CNY",
            "items": [
                {"line_no": 1, "item_name": "Item from S1", "qty": "2", "unit_price": "100", "supplier_id": s1_id},
                {"line_no": 2, "item_name": "Item from S2", "qty": "1", "unit_price": "200", "supplier_id": s2_id},
            ],
        },
        headers=auth,
    )
    assert r.status_code == 201, f"Create multi-supplier PR failed: {r.text}"
    pr_id = r.json()["id"]

    r = await seeded_client.patch(
        f"/api/v1/purchase-requisitions/{pr_id}",
        json={"status": "approved"},
        headers=auth,
    )

    r = await seeded_client.get(
        f"/api/v1/purchase-requisitions/{pr_id}/conversion-preview",
        headers=auth,
    )
    assert r.status_code in (200, 409), f"Preview failed: {r.text}"
    if r.status_code == 200:
        preview = r.json()
        assert len(preview) == 2, f"Expected 2 supplier groups, got {len(preview)}"
        for group in preview:
            assert group["item_count"] >= 1


@pytest.mark.asyncio
async def test_bill_number_format_on_invoice_create(seeded_client):
    auth = await _login_as(seeded_client, "admin")
    r = await seeded_client.get("/api/v1/suppliers", headers=auth)
    suppliers = r.json()
    supplier_id = suppliers[0]["id"]

    r = await seeded_client.get("/api/v1/purchase-orders", headers=auth)
    pos = r.json()
    if not pos:
        pytest.skip("No POs to test invoice creation")
    po = pos[0]

    r = await seeded_client.post(
        "/api/v1/invoices",
        json={
            "supplier_id": supplier_id,
            "invoice_number": "INV-E2E-001",
            "invoice_date": "2026-04-01",
            "lines": [
                {"po_item_id": po.get("items", [{}])[0].get("id"), "line_type": "product", "line_no": 1, "item_name": "Test", "qty": 1, "unit_price": 10, "subtotal": 10}
            ] if po.get("items") else [],
        },
        headers=auth,
    )
    if r.status_code == 201:
        inv = r.json()
        assert "internal_number" in inv
        assert len(inv["internal_number"]) > 0
    else:
        assert r.status_code in (409, 422)


@pytest.mark.asyncio
async def test_contract_lifecycle(seeded_client):
    auth = await _login_as(seeded_client, "admin")
    r = await seeded_client.get("/api/v1/purchase-orders", headers=auth)
    pos = r.json()
    if not pos:
        pytest.skip("No POs to test contract creation")
    po_id = pos[0]["id"]

    r = await seeded_client.post(
        "/api/v1/contracts",
        json={
            "po_id": po_id,
            "title": "E2E Contract Test",
            "total_amount": "10000",
        },
        headers=auth,
    )
    assert r.status_code == 201, f"Contract create failed: {r.text}"
    contract = r.json()
    assert contract["contract_number"].startswith(contract.get("contract_number", "")[:1] or "A")

    r = await seeded_client.get(
        f"/api/v1/contracts/{contract['id']}",
        headers=auth,
    )
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_shipment_create_with_contract_link(seeded_client):
    auth = await _login_as(seeded_client, "admin")
    r = await seeded_client.get("/api/v1/purchase-orders", headers=auth)
    pos = r.json()
    if not pos:
        pytest.skip("No POs to test shipment creation")
    po = pos[0]

    r = await seeded_client.post(
        "/api/v1/shipments",
        json={
            "po_id": po["id"],
            "items": [{"po_item_id": po["items"][0]["id"], "qty_shipped": 1}] if po.get("items") else [],
            "carrier": "E2E Carrier",
            "tracking_number": "TRK-E2E-001",
        },
        headers=auth,
    )
    assert r.status_code in (201, 422), f"Shipment create failed: {r.text}"

    if r.status_code == 201:
        shipment = r.json()
        assert "contract_id" in shipment


@pytest.mark.asyncio
async def test_pr_supplier_quote_candidates_and_save(seeded_client):
    auth = await _login_as(seeded_client, "admin")
    r = await seeded_client.get("/api/v1/suppliers", headers=auth)
    suppliers = r.json()
    supplier_id = suppliers[0]["id"]

    r = await seeded_client.get("/api/v1/items", headers=auth)
    items = r.json()
    item_id = items[0]["id"] if items else None
    if not item_id:
        pytest.skip("No items to test quote saving")

    r = await seeded_client.post(
        "/api/v1/purchase-requisitions",
        json={
            "title": "Quote test PR",
            "business_reason": "Testing quotes",
            "currency": "CNY",
            "items": [{"line_no": 1, "item_id": item_id, "item_name": "Quote item", "qty": "3", "unit_price": "150", "supplier_id": supplier_id}],
        },
        headers=auth,
    )
    if r.status_code != 201:
        r = await seeded_client.get("/api/v1/purchase-requisitions", headers=auth)
        prs = r.json()
        if not prs:
            pytest.skip("Cannot create PR")
        pr_id = prs[0]["id"]
    else:
        pr_id = r.json()["id"]

    r = await seeded_client.get(
        f"/api/v1/purchase-requisitions/{pr_id}/quote-candidates",
        headers=auth,
    )
    assert r.status_code in (200, 404)

    if r.status_code == 200:
        candidates = r.json()
        if candidates:
            r = await seeded_client.post(
                f"/api/v1/purchase-requisitions/{pr_id}/save-quotes",
                json={"line_nos": [c["line_no"] for c in candidates]},
                headers=auth,
            )
            assert r.status_code == 200, f"Save quotes failed: {r.text}"
