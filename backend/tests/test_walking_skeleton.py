import pytest


@pytest.mark.integration
async def test_walking_skeleton_end_to_end(seeded_client):
    """Exercise the full PR -> approve -> PO flow with 3 different users."""
    # Alice (IT buyer) logs in
    r = await seeded_client.post(
        "/api/v1/auth/login/json",
        json={"username": "alice", "password": "MicaDev2026!"},
    )
    assert r.status_code == 200, r.text
    alice_token = r.json()["access_token"]
    alice_headers = {"Authorization": f"Bearer {alice_token}"}

    # fetch masters
    suppliers = (await seeded_client.get("/api/v1/suppliers", headers=alice_headers)).json()
    items = (await seeded_client.get("/api/v1/items", headers=alice_headers)).json()
    assert suppliers and items
    supplier_id = suppliers[0]["id"]
    item = next(i for i in items if i["category"] == "laptop")

    # Alice creates PR
    r = await seeded_client.post(
        "/api/v1/purchase-requisitions",
        headers=alice_headers,
        json={
            "title": "新员工笔记本采购",
            "business_reason": "Q2 入职",
            "currency": "CNY",
            "items": [
                {
                    "line_no": 1,
                    "item_id": item["id"],
                    "item_name": item["name"],
                    "specification": item["specification"],
                    "supplier_id": supplier_id,
                    "qty": 3,
                    "uom": "EA",
                    "unit_price": 16000,
                }
            ],
        },
    )
    assert r.status_code == 201, r.text
    pr = r.json()
    assert pr["status"] == "draft"
    assert float(pr["total_amount"]) == 48000.0
    pr_id = pr["id"]

    # Alice submits
    r = await seeded_client.post(
        f"/api/v1/purchase-requisitions/{pr_id}/submit", headers=alice_headers
    )
    assert r.status_code == 200 and r.json()["status"] == "submitted"

    # Bob (dept_manager) approves
    r = await seeded_client.post(
        "/api/v1/auth/login/json",
        json={"username": "bob", "password": "MicaDev2026!"},
    )
    bob_headers = {"Authorization": f"Bearer {r.json()['access_token']}"}

    r = await seeded_client.post(
        f"/api/v1/purchase-requisitions/{pr_id}/decide",
        headers=bob_headers,
        json={"action": "approve", "comment": "ok"},
    )
    assert r.status_code == 200 and r.json()["status"] == "approved"

    # Alice converts to PO
    r = await seeded_client.post(
        f"/api/v1/purchase-requisitions/{pr_id}/convert-to-po", headers=alice_headers
    )
    assert r.status_code == 201, r.text
    po = r.json()
    assert po["status"] == "confirmed"
    assert float(po["total_amount"]) == 48000.0
    assert po["po_number"].startswith("PO-")

    # PR status should be converted
    r = await seeded_client.get(f"/api/v1/purchase-requisitions/{pr_id}", headers=alice_headers)
    assert r.json()["status"] == "converted"


@pytest.mark.integration
async def test_i18n_accept_language_switches_error_messages(seeded_client):
    r = await seeded_client.post(
        "/api/v1/auth/login/json",
        json={"username": "alice", "password": "wrong"},
        headers={"Accept-Language": "zh-CN"},
    )
    assert r.status_code == 401
    assert "用户名或密码错误" in r.text

    r = await seeded_client.post(
        "/api/v1/auth/login/json",
        json={"username": "alice", "password": "wrong"},
        headers={"Accept-Language": "en-US"},
    )
    assert r.status_code == 401
    assert "Invalid username" in r.text


@pytest.mark.integration
async def test_health_endpoint(seeded_client):
    r = await seeded_client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert data["app"] == "Mica"
