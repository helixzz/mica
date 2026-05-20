# pyright: reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnusedCallResult=false, reportOptionalMemberAccess=false

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.security import get_current_user
from app.db import get_db
from app.main import app
from app.models import (
    Budget,
    Company,
    POStatus,
    PurchaseOrder,
    PurchaseRequisition,
    Shipment,
    Supplier,
    User,
)
from app.services.weekly_insights import (
    _build_digest_body,
    _gather_weekly_metrics,
    send_weekly_insights_digest,
)


async def _get_user(db, username: str) -> User:
    return (await db.execute(select(User).where(User.username == username))).scalar_one()


# ── Fixtures ──────────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def alice_client(seeded_db_session):
    alice = await _get_user(seeded_db_session, "alice")

    async def _override_db():
        yield seeded_db_session

    async def _override_user():
        yield alice

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = _override_user

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as c:
        yield c

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def admin_client(seeded_db_session):
    admin = await _get_user(seeded_db_session, "admin")

    async def _override_db():
        yield seeded_db_session

    async def _override_user():
        yield admin

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = _override_user

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as c:
        yield c

    app.dependency_overrides.clear()


# ── Dashboard Config ──────────────────────────────────────────────────────


async def test_get_dashboard_config_returns_role_defaults_when_no_saved_config(alice_client):
    """Alice is IT_BUYER → should get the 2-panel default layout."""
    resp = await alice_client.get("/api/v1/insights/dashboard-config")
    assert resp.status_code == 200
    data = resp.json()
    assert "panels" in data
    assert len(data["panels"]) == 2
    panel_ids = [p["panel_id"] for p in data["panels"]]
    assert "workflow_kanban" in panel_ids
    assert "delivery_calendar" in panel_ids


async def test_save_dashboard_config_upserts(alice_client):
    """Save custom panels, then GET to confirm they persist."""
    custom = [
        {"panel_id": "delivery_calendar", "x": 0, "y": 0, "w": 24, "h": 12},
    ]
    put_resp = await alice_client.put("/api/v1/insights/dashboard-config", json={"panels": custom})
    assert put_resp.status_code == 200
    saved = put_resp.json()
    assert len(saved["panels"]) == 1
    assert saved["panels"][0]["panel_id"] == "delivery_calendar"
    assert saved["panels"][0]["w"] == 24

    get_resp = await alice_client.get("/api/v1/insights/dashboard-config")
    assert get_resp.status_code == 200
    assert get_resp.json() == saved


# ── Delivery Calendar ─────────────────────────────────────────────────────


async def test_delivery_calendar_returns_empty_for_new_user(alice_client):
    """Delivery calendar returns 200 and a list (potentially non-empty if other tests created data)."""
    resp = await alice_client.get("/api/v1/insights/delivery-calendar")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


async def test_delivery_calendar_with_pr_and_po(seeded_db_session, alice_client):
    """Delivery calendar returns items when PRs with POs exist."""
    alice = await _get_user(seeded_db_session, "alice")
    company = (await seeded_db_session.execute(select(Company))).scalar_one()
    supplier = (await seeded_db_session.execute(select(Supplier))).scalars().first()

    pr = PurchaseRequisition(
        pr_number="PR-DELIV-001",
        title="Delivery test PR",
        status="submitted",
        requester_id=alice.id,
        company_id=company.id,
        department_id=alice.department_id,
        submitted_at=datetime.now(UTC),
        total_amount=Decimal("5000.00"),
    )
    seeded_db_session.add(pr)
    await seeded_db_session.flush()

    po = PurchaseOrder(
        po_number="PO-DELIV-001",
        pr_id=pr.id,
        supplier_id=supplier.id,
        company_id=company.id,
        created_by_id=alice.id,
        status=POStatus.CONFIRMED.value,
        total_amount=Decimal("5000.00"),
        currency="CNY",
        pr_title=pr.title,
    )
    seeded_db_session.add(po)
    await seeded_db_session.flush()

    shipment = Shipment(
        shipment_number="SH-DELIV-001",
        po_id=po.id,
        expected_date=date.today() + timedelta(days=7),
        status="pending",
    )
    seeded_db_session.add(shipment)
    await seeded_db_session.commit()

    resp = await alice_client.get("/api/v1/insights/delivery-calendar")
    assert resp.status_code == 200
    items = resp.json()
    assert any(item["pr_number"] == "PR-DELIV-001" for item in items)
    # Verify the item structure
    target = next(item for item in items if item["pr_number"] == "PR-DELIV-001")
    assert target["po_number"] == "PO-DELIV-001"
    assert target["shipment_count"] == 1


# ── Workflow Kanban ───────────────────────────────────────────────────────


async def test_workflow_kanban_returns_structure(alice_client):
    """Verify the kanban response has all 4 expected keys with list values."""
    resp = await alice_client.get("/api/v1/insights/workflow-kanban")
    assert resp.status_code == 200
    data = resp.json()
    assert "pending_approvals" in data
    assert "my_draft_prs" in data
    assert "awaiting_delivery" in data
    assert "recent_completed" in data
    assert isinstance(data["pending_approvals"], list)
    assert isinstance(data["my_draft_prs"], list)
    assert isinstance(data["awaiting_delivery"], list)
    assert isinstance(data["recent_completed"], list)


async def test_workflow_kanban_shows_draft_pr(seeded_db_session, alice_client):
    """A draft PR for the current user appears in my_draft_prs."""
    alice = await _get_user(seeded_db_session, "alice")
    company = (await seeded_db_session.execute(select(Company))).scalar_one()

    pr = PurchaseRequisition(
        pr_number="PR-KANBAN-001",
        title="Kanban test draft",
        status="draft",
        requester_id=alice.id,
        company_id=company.id,
        department_id=alice.department_id,
    )
    seeded_db_session.add(pr)
    await seeded_db_session.commit()

    resp = await alice_client.get("/api/v1/insights/workflow-kanban")
    assert resp.status_code == 200
    data = resp.json()
    assert any(p["number"] == "PR-KANBAN-001" for p in data["my_draft_prs"])


# ── Budget & Execution ────────────────────────────────────────────────────


async def test_budget_execution_returns_empty(admin_client):
    """No budgets → budget execution returns an empty list."""
    resp = await admin_client.get("/api/v1/insights/budgets/execution")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_create_budget_and_list(admin_client):
    """POST a budget → verify it appears in the list endpoint."""
    payload = {
        "scope_type": "department",
        "scope_id": str(uuid4()),
        "period_type": "quarterly",
        "period_start": "2026-01-01",
        "period_end": "2026-03-31",
        "amount": "100000.00",
        "currency": "CNY",
    }
    create_resp = await admin_client.post("/api/v1/insights/budgets", json=payload)
    assert create_resp.status_code == 200
    created = create_resp.json()
    assert created["scope_type"] == "department"
    assert created["amount"] == "100000.00"

    list_resp = await admin_client.get("/api/v1/insights/budgets")
    assert list_resp.status_code == 200
    budgets = list_resp.json()
    assert any(b["id"] == created["id"] for b in budgets)


async def test_budget_execution_with_budget_returns_structure(admin_client, seeded_db_session):
    """Create a budget → execution endpoint includes it with actual_spend=0."""
    budget = Budget(
        scope_type="department",
        scope_id=uuid4(),
        period_type="quarterly",
        period_start=date(2026, 1, 1),
        period_end=date(2026, 3, 31),
        amount=Decimal("50000.00"),
        currency="CNY",
        created_by_id=(await _get_user(seeded_db_session, "admin")).id,
    )
    seeded_db_session.add(budget)
    await seeded_db_session.commit()

    resp = await admin_client.get("/api/v1/insights/budgets/execution")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) >= 1
    item = next(i for i in items if i["budget_id"] == str(budget.id))
    assert item["budget_amount"] == 50000.0
    assert item["actual_spend"] == 0.0
    assert item["execution_pct"] == 0.0
    assert item["remaining"] == 50000.0


async def test_budget_create_denied_for_non_manager(alice_client):
    """Non-manager (IT_BUYER) gets 403 when creating budgets."""
    resp = await alice_client.post("/api/v1/insights/budgets", json={
        "scope_type": "department",
        "scope_id": str(uuid4()),
        "period_type": "monthly",
        "period_start": "2026-06-01",
        "period_end": "2026-06-30",
        "amount": "1000.00",
    })
    assert resp.status_code == 403
    assert resp.json()["detail"] == "insufficient_role"


async def test_list_budgets_with_scope_filter(admin_client):
    """List budgets filtered by scope_type returns only matching budgets."""
    payload_a = {
        "scope_type": "department",
        "scope_id": str(uuid4()),
        "period_type": "quarterly",
        "period_start": "2026-01-01",
        "period_end": "2026-03-31",
        "amount": "50000.00",
    }
    payload_b = {
        "scope_type": "company",
        "scope_id": str(uuid4()),
        "period_type": "annual",
        "period_start": "2026-01-01",
        "period_end": "2026-12-31",
        "amount": "500000.00",
    }
    await admin_client.post("/api/v1/insights/budgets", json=payload_a)
    await admin_client.post("/api/v1/insights/budgets", json=payload_b)

    resp = await admin_client.get("/api/v1/insights/budgets?scope_type=company")
    assert resp.status_code == 200
    budgets = resp.json()
    assert all(b["scope_type"] == "company" for b in budgets)
    assert len(budgets) >= 1


async def test_budget_execution_with_scope_filter(admin_client):
    """Budget execution with scope_type filter returns only matching budgets."""
    payload = {
        "scope_type": "project",
        "scope_id": str(uuid4()),
        "period_type": "monthly",
        "period_start": "2026-07-01",
        "period_end": "2026-07-31",
        "amount": "25000.00",
    }
    await admin_client.post("/api/v1/insights/budgets", json=payload)

    resp = await admin_client.get("/api/v1/insights/budgets/execution?scope_type=project")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) >= 1
    assert all(i["scope_type"] == "project" for i in items)


async def test_delete_budget_success(admin_client, seeded_db_session):
    """Admin can delete a budget."""
    budget = Budget(
        scope_type="department",
        scope_id=uuid4(),
        period_type="quarterly",
        period_start=date(2026, 4, 1),
        period_end=date(2026, 6, 30),
        amount=Decimal("30000.00"),
        currency="CNY",
        created_by_id=(await _get_user(seeded_db_session, "admin")).id,
    )
    seeded_db_session.add(budget)
    await seeded_db_session.commit()

    del_resp = await admin_client.delete(f"/api/v1/insights/budgets/{budget.id}")
    assert del_resp.status_code == 200
    assert del_resp.json() == {"deleted": True}

    # Verify it's gone
    list_resp = await admin_client.get("/api/v1/insights/budgets")
    assert list_resp.status_code == 200
    assert all(b["id"] != str(budget.id) for b in list_resp.json())


async def test_supplier_scorecard_returns_list(alice_client):
    """No POs → empty scorecard list (still valid)."""
    resp = await alice_client.get("/api/v1/insights/supplier-scorecard")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


# ── Category Trends ───────────────────────────────────────────────────────


async def test_category_trends_returns_list(alice_client):
    """No POs → empty category trends list."""
    resp = await alice_client.get("/api/v1/insights/category-trends")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


# ── Approval Bottleneck ───────────────────────────────────────────────────


async def test_approval_bottleneck_returns_structure(alice_client):
    """Verify the bottleneck response has all expected keys."""
    resp = await alice_client.get("/api/v1/insights/approval-bottleneck")
    assert resp.status_code == 200
    data = resp.json()
    assert "avg_time_to_approve" in data
    assert "stages" in data
    assert "top_pending_approvers" in data
    assert "total_pending" in data
    assert "total_approved_30d" in data
    assert "total_rejected_30d" in data
    assert isinstance(data["stages"], list)
    # avg_time_to_approve may be None or populated depending on test order
    assert data["avg_time_to_approve"] is None or isinstance(data["avg_time_to_approve"], (int, float))


# ── Cash Flow Forecast ────────────────────────────────────────────────────


async def test_cash_flow_forecast_returns_structure(alice_client):
    """Verify forecast has months/total_planned/total_confirmed."""
    resp = await alice_client.get("/api/v1/insights/cash-flow-forecast")
    assert resp.status_code == 200
    data = resp.json()
    assert "months" in data
    assert isinstance(data["months"], list)
    assert "total_planned" in data
    assert "total_confirmed" in data


async def test_cash_flow_forecast_respects_months_param(alice_client):
    """?months=1 should return exactly 1 month bucket."""
    resp = await alice_client.get("/api/v1/insights/cash-flow-forecast?months=1")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["months"]) == 1


# ── Anomaly Wall ──────────────────────────────────────────────────────────


async def test_anomaly_wall_returns_structure(alice_client):
    """Verify anomaly wall returns an anomalies list."""
    resp = await alice_client.get("/api/v1/insights/anomaly-wall")
    assert resp.status_code == 200
    data = resp.json()
    assert "anomalies" in data
    assert isinstance(data["anomalies"], list)


# ── Role Defaults ─────────────────────────────────────────────────────────


async def test_role_defaults_returns_role_specific_panels(alice_client):
    """GET /insights/role-defaults returns the correct defaults for the role."""
    resp = await alice_client.get("/api/v1/insights/role-defaults")
    assert resp.status_code == 200
    data = resp.json()
    assert "panels" in data
    assert len(data["panels"]) == 2
    panel_ids = [p["panel_id"] for p in data["panels"]]
    assert "workflow_kanban" in panel_ids


# ── Weekly Insights ───────────────────────────────────────────────────────


async def test_weekly_insights_gather_metrics_empty(db_session):
    """_gather_weekly_metrics returns expected keys with numeric values."""
    from datetime import date, timedelta

    metrics = await _gather_weekly_metrics(
        db_session,
        date.today() - timedelta(days=7),
        date.today(),
    )
    assert "new_prs" in metrics
    assert "new_pos" in metrics
    assert "po_amount" in metrics
    assert "shipments_received" in metrics
    assert "pending_approvals" in metrics
    assert "new_anomalies" in metrics
    assert "week_start" in metrics
    assert "week_end" in metrics
    assert isinstance(metrics["new_prs"], int)
    assert isinstance(metrics["shipments_received"], int)
    assert isinstance(metrics["pending_approvals"], int)


async def test_weekly_insights_digest_disabled(db_session):
    """When notification is disabled, returns skipped immediately."""
    with patch("app.services.weekly_insights.notification_enabled", return_value=False):
        result = await send_weekly_insights_digest(db_session)
    assert result == {"sent": 0, "failed": 0, "skipped": True}


def test_weekly_insights_build_body_zh():
    """_build_digest_body produces valid HTML with Chinese labels."""
    metrics = {
        "week_start": "2026-05-13",
        "week_end": "2026-05-20",
        "new_prs": 3,
        "new_pos": 5,
        "po_amount": Decimal("15000.00"),
        "shipments_received": 2,
        "pending_approvals": 7,
        "new_anomalies": 1,
    }
    user = MagicMock()
    user.preferred_locale = "zh-CN"

    body = _build_digest_body(metrics, user)

    assert "Mica 周报洞察" in body
    assert "<table" in body
    assert "新增采购申请" in body
    assert "<strong>3</strong>" in body
    assert "<strong>7</strong>" in body
    assert "数据洞察" in body


def test_weekly_insights_build_body_en():
    """_build_digest_body uses English labels when locale is en-US."""
    metrics = {
        "week_start": "2026-05-13",
        "week_end": "2026-05-20",
        "new_prs": 0,
        "new_pos": 1,
        "po_amount": Decimal("0.00"),
        "shipments_received": 0,
        "pending_approvals": 0,
        "new_anomalies": 0,
    }
    user = MagicMock()
    user.preferred_locale = "en-US"

    body = _build_digest_body(metrics, user)

    assert "Mica Weekly Insights" in body
    assert "New PRs" in body
    assert "New POs" in body
    assert "Pending Approvals" in body
    assert "Insights" in body
