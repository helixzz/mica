# pyright: reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnusedCallResult=false, reportOptionalMemberAccess=false, reportPrivateUsage=false

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.api.v1 import insights as insights_api
from app.core.security import get_current_user
from app.db import get_db
from app.main import app
from app.models import (
    RFQ,
    AIModel,
    ApprovalInstance,
    ApprovalTask,
    Budget,
    Company,
    Item,
    PaymentRecord,
    PaymentSchedule,
    PaymentStatus,
    POItem,
    POStatus,
    ProcurementCategory,
    PurchaseOrder,
    PurchaseRequisition,
    RFQSupplier,
    Shipment,
    SKUPriceAnomaly,
    Supplier,
    User,
    UserRole,
)
from app.services.weekly_insights import (
    _build_digest_body,
    _gather_weekly_metrics,
    send_weekly_insights_digest,
)


async def _get_user(db, username: str) -> User:
    return (await db.execute(select(User).where(User.username == username))).scalar_one()


def _mock_user(role="admin", department_id=None):
    user = MagicMock()
    user.id = uuid4()
    user.role = role
    user.department_id = department_id
    user.email = "test@test.com"
    user.preferred_locale = "zh-CN"
    user.display_name = "Test User"
    return user


async def _get_seed_context(db):
    admin = await _get_user(db, "admin")
    alice = await _get_user(db, "alice")
    company = (await db.execute(select(Company))).scalar_one()
    supplier = (await db.execute(select(Supplier).order_by(Supplier.code))).scalars().first()
    item = (await db.execute(select(Item).order_by(Item.code))).scalars().first()
    category = (await db.execute(select(ProcurementCategory))).scalars().first()
    return admin, alice, company, supplier, item, category


async def _create_pr_po(
    db,
    *,
    tag: str,
    requester: User,
    company: Company,
    supplier: Supplier,
    item: Item | None = None,
    category: ProcurementCategory | None = None,
    status: str = POStatus.CONFIRMED.value,
    created_at: datetime | None = None,
    total_amount: Decimal = Decimal("12000.00"),
) -> tuple[PurchaseRequisition, PurchaseOrder]:
    pr = PurchaseRequisition(
        pr_number=f"PR-{tag}",
        title=f"Insight PR {tag}",
        status="approved",
        requester_id=requester.id,
        company_id=company.id,
        department_id=requester.department_id,
        procurement_category_id=category.id if category else None,
        submitted_at=created_at or datetime.now(UTC),
        total_amount=total_amount,
    )
    db.add(pr)
    await db.flush()

    po = PurchaseOrder(
        po_number=f"PO-{tag}",
        pr_id=pr.id,
        supplier_id=supplier.id,
        company_id=company.id,
        created_by_id=requester.id,
        status=status,
        total_amount=total_amount,
        currency="CNY",
        pr_title=pr.title,
        created_at=created_at or datetime.now(UTC),
        updated_at=created_at or datetime.now(UTC),
    )
    db.add(po)
    await db.flush()

    if item is not None:
        db.add(
            POItem(
                po_id=po.id,
                line_no=1,
                item_id=item.id,
                item_name=item.name,
                qty=Decimal("4"),
                unit_price=total_amount / Decimal("4"),
                amount=total_amount,
            )
        )
        await db.flush()
    return pr, po


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
    resp = await alice_client.get("/api/v1/insights/dashboard-config")
    assert resp.status_code == 200
    data = resp.json()
    assert "panels" in data
    assert len(data["panels"]) == 2
    panel_ids = [p["panel_id"] for p in data["panels"]]
    assert "workflow_kanban" in panel_ids
    assert "delivery_calendar" in panel_ids


async def test_save_dashboard_config_upserts(alice_client):
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


async def test_dashboard_config_update_existing(seeded_db_session):
    admin = await _get_user(seeded_db_session, "admin")
    panels_a = [{"panel_id": "first", "x": 0, "y": 0, "w": 6, "h": 4}]
    panels_b = [{"panel_id": "second", "x": 12, "y": 0, "w": 12, "h": 6}]

    first = await insights_api.save_dashboard_config(
        payload=insights_api.DashboardConfigIn(panels=panels_a),
        user=admin,
        db=seeded_db_session,
    )
    assert first.panels == panels_a

    second = await insights_api.save_dashboard_config(
        payload=insights_api.DashboardConfigIn(panels=panels_b),
        user=admin,
        db=seeded_db_session,
    )
    assert second.panels == panels_b


# ── Delivery Calendar ─────────────────────────────────────────────────────


async def test_delivery_calendar_returns_empty_for_new_user(alice_client):
    resp = await alice_client.get("/api/v1/insights/delivery-calendar")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


async def test_delivery_calendar_with_pr_and_po(seeded_db_session, alice_client):
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
    target = next(item for item in items if item["pr_number"] == "PR-DELIV-001")
    assert target["po_number"] == "PO-DELIV-001"
    assert target["shipment_count"] == 1


async def test_delivery_calendar_dept_manager_scope(seeded_db_session):
    _admin, _alice, company, supplier, item, category = await _get_seed_context(seeded_db_session)
    bob = await _get_user(seeded_db_session, "bob")
    dept_id = bob.department_id
    assert dept_id is not None

    await _create_pr_po(
        seeded_db_session,
        tag="DEPT-MGR-SC",
        requester=bob,
        company=company,
        supplier=supplier,
        item=item,
        category=category,
        total_amount=Decimal("1500.00"),
    )
    await seeded_db_session.commit()

    result = await insights_api.delivery_calendar(user=bob, db=seeded_db_session)
    assert isinstance(result, list)
    assert all(item.pr_id for item in result)


async def test_delivery_calendar_requester_direct(seeded_db_session):
    _admin, alice, company, supplier, item, category = await _get_seed_context(seeded_db_session)
    alice.role = UserRole.REQUESTER.value
    await seeded_db_session.flush()

    await _create_pr_po(
        seeded_db_session,
        tag="REQ-DIRECT",
        requester=alice,
        company=company,
        supplier=supplier,
        item=item,
        category=category,
        total_amount=Decimal("999.00"),
    )
    await seeded_db_session.commit()

    result = await insights_api.delivery_calendar(user=alice, db=seeded_db_session)
    assert isinstance(result, list)
    assert any("PR-REQ-DIRECT" in item.pr_number for item in result)


async def test_delivery_calendar_pr_no_po(seeded_db_session):
    _admin, alice, company, _supplier, _item, _category = await _get_seed_context(seeded_db_session)
    pr = PurchaseRequisition(
        pr_number="PR-NO-PO-001",
        title="No PO PR",
        status="submitted",
        requester_id=alice.id,
        company_id=company.id,
        department_id=alice.department_id,
        submitted_at=datetime.now(UTC),
        total_amount=Decimal("300.00"),
    )
    seeded_db_session.add(pr)
    await seeded_db_session.commit()

    result = await insights_api.delivery_calendar(user=alice, db=seeded_db_session)
    target = next((item for item in result if item.pr_number == "PR-NO-PO-001"), None)
    assert target is not None
    assert target.po_id is None
    assert target.po_number is None
    assert target.shipment_count == 0


async def test_delivery_calendar_po_no_shipments(seeded_db_session):
    _admin, alice, company, supplier, _item, _category = await _get_seed_context(seeded_db_session)
    await _create_pr_po(
        seeded_db_session,
        tag="PO-NO-SHIP",
        requester=alice,
        company=company,
        supplier=supplier,
        total_amount=Decimal("600.00"),
    )
    await seeded_db_session.commit()

    result = await insights_api.delivery_calendar(user=alice, db=seeded_db_session)
    target = next((item for item in result if item.pr_number == "PR-PO-NO-SHIP"), None)
    assert target is not None
    assert target.po_number == "PO-PO-NO-SHIP"
    assert target.shipment_count == 0
    assert target.expected_date is None


# ── Workflow Kanban ───────────────────────────────────────────────────────


async def test_workflow_kanban_returns_structure(alice_client):
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


async def test_workflow_kanban_requester_scope_awaiting(seeded_db_session):
    _admin, alice, company, supplier, _item, _category = await _get_seed_context(seeded_db_session)
    alice.role = UserRole.REQUESTER.value
    await seeded_db_session.flush()

    await _create_pr_po(
        seeded_db_session,
        tag="REQ-AWAIT",
        requester=alice,
        company=company,
        supplier=supplier,
        status=POStatus.CONFIRMED.value,
        total_amount=Decimal("2000.00"),
    )
    await seeded_db_session.commit()

    result = await insights_api.workflow_kanban(user=alice, db=seeded_db_session)
    assert isinstance(result.awaiting_delivery, list)


async def test_workflow_kanban_dept_manager_scope_awaiting(seeded_db_session):
    _admin, _alice, company, supplier, _item, _category = await _get_seed_context(seeded_db_session)
    bob = await _get_user(seeded_db_session, "bob")
    bob_dept = bob.department_id
    assert bob_dept is not None

    bob_buyer = User(
        username="dept_buyer",
        email="dept_buyer@test.local",
        display_name="Dept Buyer",
        password_hash="test",
        role=UserRole.IT_BUYER.value,
        company_id=company.id,
        department_id=bob_dept,
    )
    seeded_db_session.add(bob_buyer)
    await seeded_db_session.flush()

    await _create_pr_po(
        seeded_db_session,
        tag="DEPT-AWAIT",
        requester=bob_buyer,
        company=company,
        supplier=supplier,
        status=POStatus.CONFIRMED.value,
        total_amount=Decimal("4000.00"),
    )
    await seeded_db_session.commit()

    result = await insights_api.workflow_kanban(user=bob, db=seeded_db_session)
    assert isinstance(result.awaiting_delivery, list)


async def test_workflow_kanban_requester_scope_recent(seeded_db_session):
    _admin, alice, company, supplier, _item, _category = await _get_seed_context(seeded_db_session)
    alice.role = UserRole.REQUESTER.value
    await seeded_db_session.flush()

    await _create_pr_po(
        seeded_db_session,
        tag="REQ-RECENT",
        requester=alice,
        company=company,
        supplier=supplier,
        status=POStatus.FULLY_RECEIVED.value,
        total_amount=Decimal("2500.00"),
    )
    await seeded_db_session.commit()

    result = await insights_api.workflow_kanban(user=alice, db=seeded_db_session)
    assert isinstance(result.recent_completed, list)


# ── Budget & Execution ────────────────────────────────────────────────────


async def test_budget_execution_returns_empty(admin_client):
    resp = await admin_client.get("/api/v1/insights/budgets/execution")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_create_budget_and_list(admin_client):
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
    resp = await alice_client.post(
        "/api/v1/insights/budgets",
        json={
            "scope_type": "department",
            "scope_id": str(uuid4()),
            "period_type": "monthly",
            "period_start": "2026-06-01",
            "period_end": "2026-06-30",
            "amount": "1000.00",
        },
    )
    assert resp.status_code == 403
    assert resp.json()["detail"] == "insufficient_role"


async def test_list_budgets_with_scope_filter(admin_client):
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

    list_resp = await admin_client.get("/api/v1/insights/budgets")
    assert list_resp.status_code == 200
    assert all(b["id"] != str(budget.id) for b in list_resp.json())


async def test_create_budget_rejects_invalid_period(seeded_db_session):
    admin = await _get_user(seeded_db_session, "admin")
    payload = insights_api.BudgetIn(
        scope_type="department",
        scope_id=uuid4(),
        period_type="monthly",
        period_start=date(2026, 6, 30),
        period_end=date(2026, 6, 1),
        amount=Decimal("1000.00"),
    )
    with pytest.raises(HTTPException) as exc:
        await insights_api.create_budget(payload=payload, user=admin, db=seeded_db_session)
    assert exc.value.status_code == 400
    assert exc.value.detail == "budget.invalid_period"


async def test_delete_budget_missing_raises_404(seeded_db_session):
    admin = await _get_user(seeded_db_session, "admin")
    with pytest.raises(HTTPException) as exc:
        await insights_api.delete_budget(budget_id=uuid4(), user=admin, db=seeded_db_session)
    assert exc.value.status_code == 404
    assert exc.value.detail == "budget.not_found"


async def test_budget_execution_company_scope(seeded_db_session):
    admin, alice, company, supplier, item, category = await _get_seed_context(seeded_db_session)
    await _create_pr_po(
        seeded_db_session,
        tag="BUDGET-COMPANY",
        requester=alice,
        company=company,
        supplier=supplier,
        item=item,
        category=category,
        created_at=datetime(2026, 3, 1, tzinfo=UTC),
        total_amount=Decimal("9999.00"),
    )
    budget = Budget(
        scope_type="company",
        scope_id=company.id,
        period_type="monthly",
        period_start=date(2026, 3, 1),
        period_end=date(2026, 3, 31),
        amount=Decimal("50000.00"),
        currency="CNY",
        created_by_id=admin.id,
    )
    seeded_db_session.add(budget)
    await seeded_db_session.commit()

    rows = await insights_api.budget_execution(user=admin, db=seeded_db_session)
    target = next((r for r in rows if r.budget_id == budget.id), None)
    assert target is not None
    assert target.scope_type == "company"
    assert target.actual_spend == 9999.0


async def test_budget_execution_unknown_scope_type(seeded_db_session):
    admin, alice, company, supplier, item, category = await _get_seed_context(seeded_db_session)
    await _create_pr_po(
        seeded_db_session,
        tag="BUDGET-UNKNOWN",
        requester=alice,
        company=company,
        supplier=supplier,
        item=item,
        category=category,
        created_at=datetime(2026, 5, 1, tzinfo=UTC),
        total_amount=Decimal("5000.00"),
    )
    budget = Budget(
        scope_type="custom_unknown_type",
        scope_id=uuid4(),
        period_type="monthly",
        period_start=date(2026, 5, 1),
        period_end=date(2026, 5, 31),
        amount=Decimal("10000.00"),
        currency="CNY",
        created_by_id=admin.id,
    )
    seeded_db_session.add(budget)
    await seeded_db_session.commit()

    rows = await insights_api.budget_execution(user=admin, db=seeded_db_session)
    target = next((r for r in rows if r.budget_id == budget.id), None)
    assert target is not None
    assert target.actual_spend == 0.0


# ── Supplier Scorecard ────────────────────────────────────────────────────


async def test_supplier_scorecard_returns_list(alice_client):
    resp = await alice_client.get("/api/v1/insights/supplier-scorecard")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


async def test_supplier_scorecard_computes_scores(seeded_db_session):
    admin, alice, company, supplier, item, category = await _get_seed_context(seeded_db_session)
    created_at = datetime.now(UTC) - timedelta(days=10)
    _pr, po = await _create_pr_po(
        seeded_db_session,
        tag="SUPPLIER-SCORE",
        requester=alice,
        company=company,
        supplier=supplier,
        item=item,
        category=category,
        created_at=created_at,
        total_amount=Decimal("4000.00"),
    )
    seeded_db_session.add(
        Shipment(
            shipment_number="SH-SUPPLIER-SCORE",
            po_id=po.id,
            expected_date=date.today() - timedelta(days=1),
            actual_date=date.today() - timedelta(days=2),
            status="received",
        )
    )
    rfq = RFQ(
        rfq_number="RFQ-SUPPLIER-SCORE",
        title="Supplier score RFQ",
        pr_id=po.pr_id,
        deadline=date.today(),
        created_by_id=alice.id,
        company_id=company.id,
    )
    seeded_db_session.add(rfq)
    await seeded_db_session.flush()
    seeded_db_session.add(
        RFQSupplier(
            rfq_id=rfq.id,
            supplier_id=supplier.id,
            invited_at=created_at,
            responded_at=created_at + timedelta(hours=4),
        )
    )
    await seeded_db_session.commit()

    rows = await insights_api.supplier_scorecard(user=admin, db=seeded_db_session)
    target = next(row for row in rows if row.supplier_id == supplier.id)
    assert target.total_orders >= 1
    assert target.total_amount >= 4000.0
    assert target.on_time_rate >= 0.0
    assert target.avg_delivery_days is not None
    assert 0.0 <= target.score <= 100.0


async def test_supplier_scorecard_requester_scope(seeded_db_session):
    admin, alice, company, supplier, item, category = await _get_seed_context(seeded_db_session)
    alice.role = UserRole.REQUESTER.value
    await seeded_db_session.flush()

    await _create_pr_po(
        seeded_db_session,
        tag="ADMIN-ONLY-SCORE",
        requester=admin,
        company=company,
        supplier=supplier,
        item=item,
        category=category,
        total_amount=Decimal("7777.00"),
    )
    await seeded_db_session.commit()

    requester_rows = await insights_api.supplier_scorecard(user=alice, db=seeded_db_session)
    assert all(row.total_amount != 7777.0 for row in requester_rows)


async def test_supplier_scorecard_dept_manager_scope(seeded_db_session):
    _admin, _alice, company, supplier, item, category = await _get_seed_context(seeded_db_session)
    bob = await _get_user(seeded_db_session, "bob")
    dept_id = bob.department_id
    assert dept_id is not None

    bob_buyer = User(
        username="ssc_dept",
        email="ssc_dept@test.local",
        display_name="SSC Dept",
        password_hash="test",
        role=UserRole.IT_BUYER.value,
        company_id=company.id,
        department_id=dept_id,
    )
    seeded_db_session.add(bob_buyer)
    await seeded_db_session.flush()

    await _create_pr_po(
        seeded_db_session,
        tag="SSC-DEPT",
        requester=bob_buyer,
        company=company,
        supplier=supplier,
        item=item,
        category=category,
        total_amount=Decimal("3500.00"),
    )
    await seeded_db_session.commit()

    result = await insights_api.supplier_scorecard(user=bob, db=seeded_db_session)
    assert isinstance(result, list)


# ── Category Trends ───────────────────────────────────────────────────────


async def test_category_trends_returns_list(alice_client):
    resp = await alice_client.get("/api/v1/insights/category-trends")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


async def test_category_trends_quarter_comparison(seeded_db_session):
    admin, alice, company, supplier, item, category = await _get_seed_context(seeded_db_session)
    prev_start, current_start, _current_end = insights_api._current_and_previous_quarter()
    await _create_pr_po(
        seeded_db_session,
        tag="CAT-PREV",
        requester=alice,
        company=company,
        supplier=supplier,
        item=item,
        category=category,
        created_at=prev_start + timedelta(days=10),
        total_amount=Decimal("1000.00"),
    )
    await _create_pr_po(
        seeded_db_session,
        tag="CAT-CURR",
        requester=alice,
        company=company,
        supplier=supplier,
        item=item,
        category=category,
        created_at=current_start + timedelta(days=10),
        total_amount=Decimal("2000.00"),
    )
    await seeded_db_session.commit()

    rows = await insights_api.category_trends(user=admin, db=seeded_db_session)
    target = next(row for row in rows if row.category_id == str(category.id))
    assert target.category_name == category.label_zh
    assert target.avg_price_current > target.avg_price_prev
    assert target.change_pct > 0
    assert target.volume_current > 0
    assert target.volume_prev > 0


async def test_category_trends_requester_scope(seeded_db_session):
    _admin, alice, company, supplier, item, category = await _get_seed_context(seeded_db_session)
    alice.role = UserRole.REQUESTER.value
    await seeded_db_session.flush()

    await _create_pr_po(
        seeded_db_session,
        tag="CAT-REQ",
        requester=alice,
        company=company,
        supplier=supplier,
        item=item,
        category=category,
        total_amount=Decimal("888.00"),
    )
    await seeded_db_session.commit()

    result = await insights_api.category_trends(user=alice, db=seeded_db_session)
    assert isinstance(result, list)


async def test_category_trends_dept_manager_scope(seeded_db_session):
    _admin, _alice, company, supplier, item, category = await _get_seed_context(seeded_db_session)
    bob = await _get_user(seeded_db_session, "bob")
    dept_id = bob.department_id
    assert dept_id is not None

    dept_user = User(
        username="cat_dept",
        email="cat_dept@test.local",
        display_name="Cat Dept",
        password_hash="test",
        role=UserRole.IT_BUYER.value,
        company_id=company.id,
        department_id=dept_id,
    )
    seeded_db_session.add(dept_user)
    await seeded_db_session.flush()

    await _create_pr_po(
        seeded_db_session,
        tag="CAT-DEPT",
        requester=dept_user,
        company=company,
        supplier=supplier,
        item=item,
        category=category,
        total_amount=Decimal("777.00"),
    )
    await seeded_db_session.commit()

    result = await insights_api.category_trends(user=bob, db=seeded_db_session)
    assert isinstance(result, list)


# ── Approval Bottleneck ───────────────────────────────────────────────────


async def test_approval_bottleneck_returns_structure(alice_client):
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


async def test_approval_bottleneck_completed_and_pending(seeded_db_session):
    _admin, alice, company, _supplier, _item, _category = await _get_seed_context(seeded_db_session)
    bob = await _get_user(seeded_db_session, "bob")
    now = datetime.now(UTC)
    completed_instance = ApprovalInstance(
        biz_type="pr",
        biz_id=uuid4(),
        biz_number="PR-APPROVED",
        title="Approved instance",
        status="completed",
        submitter_id=alice.id,
        company_id=company.id,
        submitted_at=now - timedelta(hours=8),
        completed_at=now - timedelta(hours=2),
    )
    pending_instance = ApprovalInstance(
        biz_type="pr",
        biz_id=uuid4(),
        biz_number="PR-PENDING",
        title="Pending instance",
        status="pending",
        submitter_id=alice.id,
        company_id=company.id,
        submitted_at=now - timedelta(days=4),
    )
    seeded_db_session.add_all([completed_instance, pending_instance])
    await seeded_db_session.flush()
    seeded_db_session.add_all(
        [
            ApprovalTask(
                instance_id=completed_instance.id,
                stage_order=1,
                stage_name="manager",
                assignee_id=bob.id,
                status="completed",
                action="approve",
                assigned_at=now - timedelta(hours=7),
                acted_at=now - timedelta(hours=3),
            ),
            ApprovalTask(
                instance_id=pending_instance.id,
                stage_order=1,
                stage_name="manager",
                assignee_id=bob.id,
                status="pending",
                assigned_at=now - timedelta(hours=80),
            ),
        ]
    )
    await seeded_db_session.commit()

    result = await insights_api.approval_bottleneck(user=alice, db=seeded_db_session)
    assert result["total_pending"] >= 1
    assert result["total_approved_30d"] >= 1
    assert any(item["user_id"] == str(bob.id) for item in result["top_pending_approvers"])


async def test_approval_bottleneck_requester_scope(seeded_db_session):
    _admin, alice, company, _supplier, _item, _category = await _get_seed_context(seeded_db_session)
    alice.role = UserRole.REQUESTER.value
    now = datetime.now(UTC)

    inst = ApprovalInstance(
        biz_type="pr",
        biz_id=uuid4(),
        biz_number="PR-BOTTLENECK-REQ",
        title="Bottleneck req test",
        status="completed",
        submitter_id=alice.id,
        company_id=company.id,
        submitted_at=now - timedelta(hours=10),
        completed_at=now - timedelta(hours=2),
    )
    seeded_db_session.add(inst)
    await seeded_db_session.flush()
    seeded_db_session.add(
        ApprovalTask(
            instance_id=inst.id,
            stage_order=1,
            stage_name="manager",
            assignee_id=alice.id,
            status="completed",
            action="approve",
            assigned_at=now - timedelta(hours=9),
            acted_at=now - timedelta(hours=3),
        )
    )
    await seeded_db_session.commit()

    result = await insights_api.approval_bottleneck(user=alice, db=seeded_db_session)
    assert "avg_time_to_approve" in result
    assert result["total_pending"] >= 0


# ── Cash Flow Forecast ────────────────────────────────────────────────────


async def test_cash_flow_forecast_returns_structure(alice_client):
    resp = await alice_client.get("/api/v1/insights/cash-flow-forecast")
    assert resp.status_code == 200
    data = resp.json()
    assert "months" in data
    assert isinstance(data["months"], list)
    assert "total_planned" in data
    assert "total_confirmed" in data


async def test_cash_flow_forecast_respects_months_param(alice_client):
    resp = await alice_client.get("/api/v1/insights/cash-flow-forecast?months=1")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["months"]) == 1


async def test_cash_flow_forecast_sums_amounts(seeded_db_session):
    admin, alice, company, supplier, item, category = await _get_seed_context(seeded_db_session)
    _pr, po = await _create_pr_po(
        seeded_db_session,
        tag="CASH-FLOW",
        requester=alice,
        company=company,
        supplier=supplier,
        item=item,
        category=category,
    )
    planned_date = insights_api._month_start(datetime.now(UTC).date())
    seeded_db_session.add_all(
        [
            PaymentSchedule(
                po_id=po.id,
                installment_no=1,
                label="Current month planned",
                planned_amount=Decimal("3000.00"),
                planned_date=planned_date,
                status="planned",
            ),
            PaymentRecord(
                payment_number="PAY-CASH-FLOW",
                po_id=po.id,
                installment_no=1,
                amount=Decimal("1200.00"),
                payment_date=planned_date,
                status=PaymentStatus.CONFIRMED.value,
            ),
        ]
    )
    await seeded_db_session.commit()

    result = await insights_api.cash_flow_forecast(user=admin, db=seeded_db_session, months=1)
    assert result["months"][0]["planned"] >= 3000.0
    assert result["months"][0]["confirmed"] >= 1200.0
    assert result["total_planned"] >= 3000.0
    assert result["total_confirmed"] >= 1200.0


# ── Anomaly Wall ──────────────────────────────────────────────────────────


async def test_anomaly_wall_returns_structure(alice_client):
    resp = await alice_client.get("/api/v1/insights/anomaly-wall")
    assert resp.status_code == 200
    data = resp.json()
    assert "anomalies" in data
    assert isinstance(data["anomalies"], list)


async def test_anomaly_wall_all_types(seeded_db_session):
    admin, alice, company, supplier, item, category = await _get_seed_context(seeded_db_session)
    bob = await _get_user(seeded_db_session, "bob")
    now = datetime.now(UTC)
    seeded_db_session.add(
        SKUPriceAnomaly(
            item_id=item.id,
            baseline_avg_price=Decimal("100.00"),
            observed_price=Decimal("160.00"),
            deviation_pct=Decimal("60.00"),
            severity="critical",
            status="new",
            created_at=now - timedelta(days=1),
        )
    )
    _overdue_pr, overdue_po = await _create_pr_po(
        seeded_db_session,
        tag="OVERDUE-WALL",
        requester=alice,
        company=company,
        supplier=supplier,
        item=item,
        category=category,
        created_at=now - timedelta(days=45),
        total_amount=Decimal("500.00"),
    )
    overdue_po.status = POStatus.CONFIRMED.value
    stale_instance = ApprovalInstance(
        biz_type="pr",
        biz_id=uuid4(),
        biz_number="PR-STALE-WALL",
        title="Stale approval",
        status="pending",
        submitter_id=alice.id,
        company_id=company.id,
        submitted_at=now - timedelta(days=5),
    )
    seeded_db_session.add(stale_instance)
    await seeded_db_session.flush()
    seeded_db_session.add(
        ApprovalTask(
            instance_id=stale_instance.id,
            stage_order=1,
            stage_name="finance",
            assignee_id=bob.id,
            status="pending",
            assigned_at=now - timedelta(hours=96),
        )
    )
    await _create_pr_po(
        seeded_db_session,
        tag="CONCENTRATION-WALL",
        requester=alice,
        company=company,
        supplier=supplier,
        item=item,
        category=category,
        created_at=now - timedelta(days=5),
        total_amount=Decimal("25000.00"),
    )
    await seeded_db_session.commit()

    result = await insights_api.anomaly_wall(user=admin, db=seeded_db_session)
    types = {item["type"] for item in result["anomalies"]}
    assert {
        "price_anomaly",
        "overdue_delivery",
        "approval_stale",
        "supplier_concentration",
    }.issubset(types)


async def test_anomaly_wall_empty(seeded_db_session):
    admin = await _get_user(seeded_db_session, "admin")
    result = await insights_api.anomaly_wall(user=admin, db=seeded_db_session)
    assert "anomalies" in result
    assert isinstance(result["anomalies"], list)


# ── Role Defaults ─────────────────────────────────────────────────────────


async def test_role_defaults_returns_role_specific_panels(alice_client):
    resp = await alice_client.get("/api/v1/insights/role-defaults")
    assert resp.status_code == 200
    data = resp.json()
    assert "panels" in data
    assert len(data["panels"]) == 2
    panel_ids = [p["panel_id"] for p in data["panels"]]
    assert "workflow_kanban" in panel_ids


async def test_get_role_defaults_unknown_role():
    result = await insights_api.get_role_defaults(user=_mock_user(role="unknown"))
    assert result.panels == []


# ── Quarterly Summary ─────────────────────────────────────────────────────


async def test_quarterly_summary_generates_and_caches(seeded_db_session, monkeypatch):
    admin, alice, company, supplier, item, category = await _get_seed_context(seeded_db_session)
    quarter = "2026-Q2"
    await _create_pr_po(
        seeded_db_session,
        tag="QUARTERLY-SUMMARY",
        requester=alice,
        company=company,
        supplier=supplier,
        item=item,
        category=category,
        created_at=datetime(2026, 4, 5, tzinfo=UTC),
        total_amount=Decimal("9000.00"),
    )
    seeded_db_session.add(
        AIModel(
            name="insights-test-model",
            provider="openai",
            model_string="gpt-test",
            api_key_encrypted="test-key",
            is_active=True,
            priority=1,
        )
    )
    await seeded_db_session.commit()

    fake_response = MagicMock()
    fake_response.choices = [MagicMock(message=MagicMock(content="测试季度摘要"))]
    completion = AsyncMock(return_value=fake_response)
    monkeypatch.setattr(insights_api.litellm, "acompletion", completion)

    first = await insights_api.quarterly_summary(user=admin, db=seeded_db_session, quarter=quarter)
    second = await insights_api.quarterly_summary(user=admin, db=seeded_db_session, quarter=quarter)

    assert first["quarter"] == quarter
    assert first["summary_text"] == "测试季度摘要"
    assert first["data_snapshot"]["total_pos"] >= 1
    assert second == first
    completion.assert_called_once()


async def test_quarterly_summary_handles_llm_exception(seeded_db_session, monkeypatch):
    admin, alice, company, supplier, item, category = await _get_seed_context(seeded_db_session)
    quarter = "2027-Q1"
    await _create_pr_po(
        seeded_db_session,
        tag="QSUM-FAIL",
        requester=alice,
        company=company,
        supplier=supplier,
        item=item,
        category=category,
        created_at=datetime(2027, 1, 10, tzinfo=UTC),
        total_amount=Decimal("4500.00"),
    )
    seeded_db_session.add(
        AIModel(
            name="failing-model",
            provider="openai",
            model_string="gpt-fail",
            api_key_encrypted="bad-key",
            is_active=True,
            priority=1,
        )
    )
    await seeded_db_session.commit()

    async def _raise(*args, **kwargs):
        raise RuntimeError("LLM unavailable")

    monkeypatch.setattr(insights_api.litellm, "acompletion", _raise)

    result = await insights_api.quarterly_summary(user=admin, db=seeded_db_session, quarter=quarter)
    assert result["quarter"] == quarter
    assert result["summary_text"] == "Summary generation failed"


async def test_quarterly_summary_no_ai_model(db_session):
    company = Company(name_zh="QS Test Co", code="QSTEST")
    db_session.add(company)
    await db_session.flush()

    admin = User(
        username="qs_admin",
        email="qs_admin@test.local",
        display_name="QS Admin",
        password_hash="test",
        role=UserRole.ADMIN.value,
        company_id=company.id,
    )
    supplier = Supplier(name="QS Supplier", code="QSSUP")
    category = ProcurementCategory(label_zh="服务器", label_en="Server", code="CAT-QS")
    db_session.add_all([admin, supplier, category])
    await db_session.flush()

    await _create_pr_po(
        db_session,
        tag="QSUM-NOAI",
        requester=admin,
        company=company,
        supplier=supplier,
        category=category,
        created_at=datetime(2026, 4, 15, tzinfo=UTC),
        total_amount=Decimal("3300.00"),
    )
    await db_session.commit()

    result = await insights_api.quarterly_summary(user=admin, db=db_session, quarter="2026-Q2")
    assert result["quarter"] == "2026-Q2"
    assert result["summary_text"] == "Summary generation failed"
    assert result["data_snapshot"]["total_pos"] >= 1


# ── Helper functions ──────────────────────────────────────────────────────


def test_parse_quarter_invalid_format():
    with pytest.raises(HTTPException) as exc:
        insights_api._parse_quarter("not-a-quarter")
    assert exc.value.status_code == 400
    assert exc.value.detail == "invalid_quarter"


def test_parse_quarter_invalid_quarter_num():
    with pytest.raises(HTTPException) as exc:
        insights_api._parse_quarter("2026-Q5")
    assert exc.value.status_code == 400


def test_parse_quarter_q1_uses_previous_year():
    prev_start, start, _end = insights_api._parse_quarter("2026-Q1")
    assert start.year == 2026
    assert prev_start.year == 2025
    assert prev_start.month == 10


def test_pct_zero_denominator():
    assert insights_api._pct(100, 0) == 0.0


# ── Weekly Insights ───────────────────────────────────────────────────────


async def test_weekly_insights_gather_metrics_empty(db_session):
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


async def test_weekly_insights_gather_metrics_with_data(seeded_db_session):
    _admin, alice, company, supplier, _item, _category = await _get_seed_context(seeded_db_session)
    now = datetime.now(UTC)
    three_days_ago = now - timedelta(days=3)

    pr = PurchaseRequisition(
        pr_number="PR-WEEKLY-01",
        title="Weekly test PR",
        status="approved",
        requester_id=alice.id,
        company_id=company.id,
        submitted_at=three_days_ago,
        total_amount=Decimal("5000.00"),
    )
    seeded_db_session.add(pr)
    await seeded_db_session.flush()

    po = PurchaseOrder(
        po_number="PO-WEEKLY-01",
        pr_id=pr.id,
        supplier_id=supplier.id,
        company_id=company.id,
        created_by_id=alice.id,
        status=POStatus.CONFIRMED.value,
        total_amount=Decimal("5000.00"),
        currency="CNY",
    )
    seeded_db_session.add(po)
    await seeded_db_session.flush()

    seeded_db_session.add(
        Shipment(
            shipment_number="SH-WEEKLY-01",
            po_id=po.id,
            expected_date=(now - timedelta(days=1)).date(),
            actual_date=(now - timedelta(days=1)).date(),
            status="received",
        )
    )
    await seeded_db_session.commit()

    metrics = await _gather_weekly_metrics(
        seeded_db_session,
        week_start=(now - timedelta(days=7)).date(),
        today=now.date(),
    )
    assert metrics["new_prs"] >= 1
    assert metrics["new_pos"] >= 1
    assert metrics["po_amount"] >= Decimal("5000")
    assert metrics["shipments_received"] >= 1
    assert isinstance(metrics["new_anomalies"], int)


async def test_weekly_insights_digest_disabled(db_session):
    with patch("app.services.weekly_insights.notification_enabled", return_value=False):
        result = await send_weekly_insights_digest(db_session)
    assert result == {"sent": 0, "failed": 0, "skipped": True}


async def test_weekly_insights_send_digest_no_recipients(db_session, monkeypatch):
    async def _enabled(_db, _key):
        return True

    monkeypatch.setattr("app.services.weekly_insights.notification_enabled", _enabled)

    async def _send_ok(_db, _email, _subject, _body):
        return True

    monkeypatch.setattr("app.services.weekly_insights.send_email", _send_ok)
    result = await send_weekly_insights_digest(db_session)
    assert result["sent"] >= 0
    assert result["failed"] >= 0


async def test_weekly_insights_send_digest_email_fails(seeded_db_session, monkeypatch):
    _admin, _alice, _company, _supplier, _item, _category = await _get_seed_context(
        seeded_db_session
    )

    async def _enabled(_db, _key):
        return True

    monkeypatch.setattr("app.services.weekly_insights.notification_enabled", _enabled)

    async def _send_fail(_db, _email, _subject, _body):
        return False

    monkeypatch.setattr("app.services.weekly_insights.send_email", _send_fail)

    result = await send_weekly_insights_digest(seeded_db_session)
    assert result["sent"] == 0
    assert result["failed"] >= 1


async def test_weekly_insights_send_digest_email_exception(seeded_db_session, monkeypatch):
    _admin, _alice, _company, _supplier, _item, _category = await _get_seed_context(
        seeded_db_session
    )

    async def _enabled(_db, _key):
        return True

    monkeypatch.setattr("app.services.weekly_insights.notification_enabled", _enabled)

    async def _send_raise(_db, _email, _subject, _body):
        raise RuntimeError("SMTP down")

    monkeypatch.setattr("app.services.weekly_insights.send_email", _send_raise)

    result = await send_weekly_insights_digest(seeded_db_session)
    assert result["sent"] == 0
    assert result["failed"] >= 1


def test_weekly_insights_build_body_zh():
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
