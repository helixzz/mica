from __future__ import annotations

import json
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from typing import Annotated
from uuid import UUID

import litellm
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.litellm_helpers import resolve_litellm_model
from app.core.security import CurrentUser
from app.db import get_db
from app.models import (
    AIModel,
    ApprovalInstance,
    ApprovalTask,
    Budget,
    InsightCache,
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
    UserDashboardConfig,
    UserRole,
)

router = APIRouter(prefix="/insights", tags=["insights"])


ROLE_DEFAULTS: dict[str, list[dict]] = {
    UserRole.REQUESTER.value: [
        {"panel_id": "delivery_calendar", "x": 0, "y": 0, "w": 12, "h": 6},
    ],
    UserRole.IT_BUYER.value: [
        {"panel_id": "workflow_kanban", "x": 0, "y": 0, "w": 12, "h": 6},
        {"panel_id": "delivery_calendar", "x": 0, "y": 6, "w": 12, "h": 6},
    ],
    UserRole.DEPT_MANAGER.value: [
        {"panel_id": "workflow_kanban", "x": 0, "y": 0, "w": 12, "h": 6},
    ],
    UserRole.PROCUREMENT_MGR.value: [
        {"panel_id": "workflow_kanban", "x": 0, "y": 0, "w": 12, "h": 6},
        {"panel_id": "delivery_calendar", "x": 0, "y": 6, "w": 12, "h": 6},
    ],
    UserRole.FINANCE_AUDITOR.value: [
        {"panel_id": "delivery_calendar", "x": 0, "y": 0, "w": 12, "h": 6},
    ],
    UserRole.ADMIN.value: [
        {"panel_id": "workflow_kanban", "x": 0, "y": 0, "w": 12, "h": 6},
        {"panel_id": "delivery_calendar", "x": 0, "y": 6, "w": 12, "h": 6},
    ],
}


class DashboardConfigOut(BaseModel):
    panels: list[dict]


class DashboardConfigIn(BaseModel):
    panels: list[dict]


@router.get("/dashboard-config", response_model=DashboardConfigOut)
async def get_dashboard_config(
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DashboardConfigOut:
    row = (
        await db.execute(select(UserDashboardConfig).where(UserDashboardConfig.user_id == user.id))
    ).scalar_one_or_none()
    if row is not None:
        return DashboardConfigOut(panels=row.panels)
    return DashboardConfigOut(panels=ROLE_DEFAULTS.get(user.role, []))


@router.put("/dashboard-config", response_model=DashboardConfigOut)
async def save_dashboard_config(
    payload: DashboardConfigIn,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DashboardConfigOut:
    row = (
        await db.execute(select(UserDashboardConfig).where(UserDashboardConfig.user_id == user.id))
    ).scalar_one_or_none()
    if row is None:
        row = UserDashboardConfig(user_id=user.id, panels=payload.panels)
        db.add(row)
    else:
        row.panels = payload.panels
    await db.commit()
    return DashboardConfigOut(panels=row.panels)


@router.get("/role-defaults")
async def get_role_defaults(user: CurrentUser) -> DashboardConfigOut:
    return DashboardConfigOut(panels=ROLE_DEFAULTS.get(user.role, []))


class DeliveryItem(BaseModel):
    pr_id: str
    pr_number: str
    pr_title: str
    pr_status: str
    submitted_at: str | None
    po_id: str | None
    po_number: str | None
    po_status: str | None
    po_created_at: str | None
    expected_date: str | None
    actual_date: str | None
    shipment_count: int


@router.get("/delivery-calendar", response_model=list[DeliveryItem])
async def delivery_calendar(
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[DeliveryItem]:
    pr_query = (
        select(PurchaseRequisition)
        .options(selectinload(PurchaseRequisition.items))
        .order_by(PurchaseRequisition.created_at.desc())
        .limit(50)
    )
    if user.role == UserRole.REQUESTER.value:
        pr_query = pr_query.where(PurchaseRequisition.requester_id == user.id)
    elif user.role == UserRole.DEPT_MANAGER.value and user.department_id:
        pr_query = pr_query.where(PurchaseRequisition.department_id == user.department_id)

    prs = (await db.execute(pr_query)).scalars().all()
    pr_ids = [pr.id for pr in prs]
    if not pr_ids:
        return []

    pos = (
        (await db.execute(select(PurchaseOrder).where(PurchaseOrder.pr_id.in_(pr_ids))))
        .scalars()
        .all()
    )
    po_by_pr: dict[UUID, PurchaseOrder] = {po.pr_id: po for po in pos}

    po_ids = [po.id for po in pos]
    shipments: list[Shipment] = []
    if po_ids:
        shipments = list(
            (
                await db.execute(
                    select(Shipment)
                    .where(Shipment.po_id.in_(po_ids))
                    .order_by(Shipment.expected_date)
                )
            )
            .scalars()
            .all()
        )
    shipments_by_po: dict[UUID, list[Shipment]] = {}
    for s in shipments:
        shipments_by_po.setdefault(s.po_id, []).append(s)

    results: list[DeliveryItem] = []
    for pr in prs:
        po = po_by_pr.get(pr.id)
        po_shipments = shipments_by_po.get(po.id, []) if po else []
        latest = po_shipments[-1] if po_shipments else None
        results.append(
            DeliveryItem(
                pr_id=str(pr.id),
                pr_number=pr.pr_number,
                pr_title=pr.title,
                pr_status=pr.status,
                submitted_at=pr.submitted_at.isoformat() if pr.submitted_at else None,
                po_id=str(po.id) if po else None,
                po_number=po.po_number if po else None,
                po_status=po.status if po else None,
                po_created_at=po.created_at.isoformat() if po else None,
                expected_date=str(latest.expected_date)
                if latest and latest.expected_date
                else None,
                actual_date=str(latest.actual_date) if latest and latest.actual_date else None,
                shipment_count=len(po_shipments),
            )
        )
    return results


class KanbanOut(BaseModel):
    pending_approvals: list[dict]
    my_draft_prs: list[dict]
    awaiting_delivery: list[dict]
    recent_completed: list[dict]


@router.get("/workflow-kanban", response_model=KanbanOut)
async def workflow_kanban(
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> KanbanOut:
    pending_approvals: list[dict] = []
    pending_filter = ApprovalTask.status == "pending"
    if user.role != UserRole.ADMIN.value:
        pending_filter = and_(
            pending_filter,
            ApprovalTask.assignee_id == user.id,
        )
    tasks = (
        (
            await db.execute(
                select(ApprovalTask)
                .where(pending_filter)
                .order_by(ApprovalTask.created_at.desc())
                .limit(20)
            )
        )
        .scalars()
        .all()
    )
    for t in tasks:
        pending_approvals.append(
            {
                "id": str(t.id),
                "type": "approval",
                "title": t.stage_label or "Approval",
                "created_at": t.created_at.isoformat(),
            }
        )

    draft_prs = (
        (
            await db.execute(
                select(PurchaseRequisition)
                .where(
                    PurchaseRequisition.requester_id == user.id,
                    PurchaseRequisition.status == "draft",
                )
                .order_by(PurchaseRequisition.created_at.desc())
                .limit(10)
            )
        )
        .scalars()
        .all()
    )
    my_drafts = [
        {
            "id": str(pr.id),
            "type": "pr",
            "number": pr.pr_number,
            "title": pr.title,
            "created_at": pr.created_at.isoformat(),
        }
        for pr in draft_prs
    ]

    awaiting_q = (
        select(PurchaseOrder)
        .where(
            PurchaseOrder.status.in_(
                [
                    POStatus.CONFIRMED.value,
                    POStatus.PARTIALLY_RECEIVED.value,
                ]
            )
        )
        .order_by(PurchaseOrder.created_at.desc())
        .limit(20)
    )
    if user.role == UserRole.REQUESTER.value:
        awaiting_q = awaiting_q.join(
            PurchaseRequisition, PurchaseOrder.pr_id == PurchaseRequisition.id
        ).where(PurchaseRequisition.requester_id == user.id)
    elif user.role == UserRole.DEPT_MANAGER.value and user.department_id:
        awaiting_q = awaiting_q.join(
            PurchaseRequisition, PurchaseOrder.pr_id == PurchaseRequisition.id
        ).where(PurchaseRequisition.department_id == user.department_id)

    awaiting_pos = (await db.execute(awaiting_q)).scalars().all()
    awaiting = [
        {
            "id": str(po.id),
            "type": "po",
            "number": po.po_number,
            "title": po.pr_title or po.po_number,
            "status": po.status,
            "created_at": po.created_at.isoformat(),
        }
        for po in awaiting_pos
    ]

    seven_days_ago = datetime.now(UTC) - timedelta(days=7)
    recent_q = (
        select(PurchaseOrder)
        .where(
            PurchaseOrder.status.in_(
                [
                    POStatus.FULLY_RECEIVED.value,
                    POStatus.CLOSED.value,
                ]
            ),
            PurchaseOrder.updated_at >= seven_days_ago,
        )
        .order_by(PurchaseOrder.updated_at.desc())
        .limit(10)
    )
    if user.role == UserRole.REQUESTER.value:
        recent_q = recent_q.join(
            PurchaseRequisition, PurchaseOrder.pr_id == PurchaseRequisition.id
        ).where(PurchaseRequisition.requester_id == user.id)

    recent_pos = (await db.execute(recent_q)).scalars().all()
    recent = [
        {
            "id": str(po.id),
            "type": "po",
            "number": po.po_number,
            "title": po.pr_title or po.po_number,
            "status": po.status,
            "created_at": po.created_at.isoformat(),
        }
        for po in recent_pos
    ]

    return KanbanOut(
        pending_approvals=pending_approvals,
        my_draft_prs=my_drafts,
        awaiting_delivery=awaiting,
        recent_completed=recent,
    )


MANAGER_ROLES = {UserRole.ADMIN.value, UserRole.PROCUREMENT_MGR.value}


def _require_insights_manager(user: CurrentUser) -> None:
    if user.role not in MANAGER_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="insufficient_role",
        )


def _start_of_day(value: date) -> datetime:
    return datetime.combine(value, time.min, tzinfo=UTC)


def _end_of_day(value: date) -> datetime:
    return datetime.combine(value, time.max, tzinfo=UTC)


def _month_start(value: date) -> date:
    return value.replace(day=1)


def _add_months(value: date, months: int) -> date:
    month = value.month - 1 + months
    year = value.year + month // 12
    month = month % 12 + 1
    return date(year, month, 1)


def _quarter_window(year: int, quarter: int) -> tuple[datetime, datetime]:
    start_month = (quarter - 1) * 3 + 1
    start = datetime(year, start_month, 1, tzinfo=UTC)
    end_year = year + (1 if start_month == 10 else 0)
    end_month = 1 if start_month == 10 else start_month + 3
    return start, datetime(end_year, end_month, 1, tzinfo=UTC)


def _current_and_previous_quarter() -> tuple[datetime, datetime, datetime]:
    now = datetime.now(UTC)
    quarter = (now.month - 1) // 3 + 1
    current_start, current_end = _quarter_window(now.year, quarter)
    if quarter == 1:
        prev_start, _ = _quarter_window(now.year - 1, 4)
    else:
        prev_start, _ = _quarter_window(now.year, quarter - 1)
    return prev_start, current_start, current_end


def _parse_quarter(value: str) -> tuple[datetime, datetime, datetime]:
    try:
        year_s, quarter_s = value.upper().split("-Q", 1)
        year = int(year_s)
        quarter = int(quarter_s)
        if quarter not in {1, 2, 3, 4}:
            raise ValueError
    except ValueError as e:
        raise HTTPException(status_code=400, detail="invalid_quarter") from e
    start, end = _quarter_window(year, quarter)
    if quarter == 1:
        prev_start, _ = _quarter_window(year - 1, 4)
    else:
        prev_start, _ = _quarter_window(year, quarter - 1)
    return prev_start, start, end


def _pct(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return round(numerator / denominator * 100, 2)


def _money(value: Decimal | int | float | None) -> float:
    return float(value or 0)


def _po_scoped_stmt(stmt, user: CurrentUser):
    if user.role == UserRole.REQUESTER.value:
        return stmt.join(PurchaseRequisition, PurchaseOrder.pr_id == PurchaseRequisition.id).where(
            PurchaseRequisition.requester_id == user.id
        )
    if user.role == UserRole.DEPT_MANAGER.value and user.department_id:
        return stmt.join(PurchaseRequisition, PurchaseOrder.pr_id == PurchaseRequisition.id).where(
            PurchaseRequisition.department_id == user.department_id
        )
    return stmt


class BudgetIn(BaseModel):
    scope_type: str
    scope_id: UUID
    period_type: str
    period_start: date
    period_end: date
    amount: Decimal
    currency: str = "CNY"
    notes: str | None = None


class BudgetOut(BaseModel):
    id: UUID
    scope_type: str
    scope_id: UUID
    period_type: str
    period_start: date
    period_end: date
    amount: Decimal
    currency: str | None
    notes: str | None

    model_config = {"from_attributes": True}


class BudgetExecutionItem(BaseModel):
    budget_id: UUID
    scope_type: str
    scope_id: UUID
    period_start: date
    period_end: date
    budget_amount: float
    actual_spend: float
    execution_pct: float
    remaining: float


@router.post("/budgets", response_model=BudgetOut)
async def create_budget(
    payload: BudgetIn,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BudgetOut:
    _require_insights_manager(user)
    if payload.period_end < payload.period_start:
        raise HTTPException(status_code=400, detail="budget.invalid_period")
    budget = Budget(
        scope_type=payload.scope_type,
        scope_id=payload.scope_id,
        period_type=payload.period_type,
        period_start=payload.period_start,
        period_end=payload.period_end,
        amount=payload.amount,
        currency=payload.currency,
        notes=payload.notes,
        created_by_id=user.id,
    )
    db.add(budget)
    await db.commit()
    await db.refresh(budget)
    return BudgetOut.model_validate(budget)


@router.get("/budgets", response_model=list[BudgetOut])
async def list_budgets(
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    scope_type: Annotated[str | None, Query()] = None,
    period: Annotated[date | None, Query()] = None,
) -> list[BudgetOut]:
    _require_insights_manager(user)
    stmt = select(Budget).order_by(Budget.period_start.desc(), Budget.created_at.desc())
    if scope_type:
        stmt = stmt.where(Budget.scope_type == scope_type)
    if period:
        stmt = stmt.where(Budget.period_start <= period, Budget.period_end >= period)
    rows = (await db.execute(stmt)).scalars().all()
    return [BudgetOut.model_validate(row) for row in rows]


@router.get("/budgets/execution", response_model=list[BudgetExecutionItem])
async def budget_execution(
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    scope_type: Annotated[str | None, Query()] = None,
    period: Annotated[date | None, Query()] = None,
) -> list[BudgetExecutionItem]:
    _require_insights_manager(user)
    stmt = select(Budget).order_by(Budget.period_start.desc())
    if scope_type:
        stmt = stmt.where(Budget.scope_type == scope_type)
    if period:
        stmt = stmt.where(Budget.period_start <= period, Budget.period_end >= period)
    budgets = (await db.execute(stmt)).scalars().all()

    results: list[BudgetExecutionItem] = []
    for budget in budgets:
        po_stmt = (
            select(func.coalesce(func.sum(PurchaseOrder.total_amount), 0))
            .join(PurchaseRequisition, PurchaseOrder.pr_id == PurchaseRequisition.id)
            .where(
                PurchaseOrder.created_at >= _start_of_day(budget.period_start),
                PurchaseOrder.created_at <= _end_of_day(budget.period_end),
            )
        )
        if budget.scope_type == "department":
            po_stmt = po_stmt.where(PurchaseRequisition.department_id == budget.scope_id)
        elif budget.scope_type == "company":
            po_stmt = po_stmt.where(PurchaseRequisition.company_id == budget.scope_id)
        elif budget.scope_type == "category":
            po_stmt = po_stmt.where(PurchaseRequisition.procurement_category_id == budget.scope_id)
        else:
            po_stmt = po_stmt.where(False)
        actual = _money((await db.execute(po_stmt)).scalar())
        budget_amount = _money(budget.amount)
        results.append(
            BudgetExecutionItem(
                budget_id=budget.id,
                scope_type=budget.scope_type,
                scope_id=budget.scope_id,
                period_start=budget.period_start,
                period_end=budget.period_end,
                budget_amount=budget_amount,
                actual_spend=actual,
                execution_pct=_pct(actual, budget_amount),
                remaining=round(budget_amount - actual, 2),
            )
        )
    return results


@router.delete("/budgets/{budget_id}")
async def delete_budget(
    budget_id: UUID,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, bool]:
    _require_insights_manager(user)
    budget = await db.get(Budget, budget_id)
    if budget is None:
        raise HTTPException(status_code=404, detail="budget.not_found")
    await db.delete(budget)
    await db.commit()
    return {"deleted": True}


class SupplierScorecardItem(BaseModel):
    supplier_id: UUID
    supplier_name: str
    total_orders: int
    total_amount: float
    on_time_rate: float
    avg_delivery_days: float | None
    price_stability: float
    score: float


@router.get("/supplier-scorecard", response_model=list[SupplierScorecardItem])
async def supplier_scorecard(
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[SupplierScorecardItem]:
    top_stmt = (
        select(
            Supplier.id,
            Supplier.name,
            func.count(PurchaseOrder.id).label("total_orders"),
            func.coalesce(func.sum(PurchaseOrder.total_amount), 0).label("total_amount"),
        )
        .join(PurchaseOrder, PurchaseOrder.supplier_id == Supplier.id)
        .where(Supplier.is_enabled.is_(True), Supplier.is_deleted.is_(False))
        .group_by(Supplier.id, Supplier.name)
        .order_by(desc("total_amount"))
        .limit(20)
    )
    top_stmt = _po_scoped_stmt(top_stmt, user)
    rows = (await db.execute(top_stmt)).all()
    out: list[SupplierScorecardItem] = []
    for supplier_id, supplier_name, total_orders, total_amount in rows:
        shipment_rows = (
            await db.execute(
                select(Shipment.expected_date, Shipment.actual_date, PurchaseOrder.created_at)
                .join(PurchaseOrder, Shipment.po_id == PurchaseOrder.id)
                .where(PurchaseOrder.supplier_id == supplier_id)
            )
        ).all()
        completed_shipments = [r for r in shipment_rows if r.actual_date is not None]
        on_time = [
            r for r in completed_shipments if r.expected_date and r.actual_date <= r.expected_date
        ]
        delivery_days = [
            (datetime.combine(r.actual_date, time.min, tzinfo=UTC) - r.created_at).days
            for r in completed_shipments
        ]
        on_time_rate = _pct(len(on_time), len(completed_shipments))
        avg_delivery_days = (
            round(sum(delivery_days) / len(delivery_days), 2) if delivery_days else None
        )
        price_stability = _money(
            (
                await db.execute(
                    select(func.coalesce(func.stddev_pop(POItem.unit_price), 0))
                    .join(PurchaseOrder, POItem.po_id == PurchaseOrder.id)
                    .where(PurchaseOrder.supplier_id == supplier_id)
                )
            ).scalar()
        )
        response_rows = (
            await db.execute(
                select(RFQSupplier.invited_at, RFQSupplier.responded_at).where(
                    RFQSupplier.supplier_id == supplier_id,
                    RFQSupplier.responded_at.isnot(None),
                )
            )
        ).all()
        response_hours = [
            (r.responded_at - r.invited_at).total_seconds() / 3600 for r in response_rows
        ]
        response_score = 100.0
        if response_hours:
            response_score = max(0.0, 100.0 - min(sum(response_hours) / len(response_hours), 100.0))
        stability_score = max(0.0, 100.0 - min(price_stability, 100.0))
        score = round(on_time_rate * 0.4 + stability_score * 0.3 + response_score * 0.3, 2)
        out.append(
            SupplierScorecardItem(
                supplier_id=supplier_id,
                supplier_name=supplier_name,
                total_orders=int(total_orders or 0),
                total_amount=_money(total_amount),
                on_time_rate=on_time_rate,
                avg_delivery_days=avg_delivery_days,
                price_stability=round(price_stability, 4),
                score=score,
            )
        )
    return out


class CategoryTrendItem(BaseModel):
    category_id: str | None
    category_name: str
    avg_price_current: float
    avg_price_prev: float
    change_pct: float
    volume_current: float
    volume_prev: float


async def _category_rows(
    db: AsyncSession, start: datetime, end: datetime, user: CurrentUser
) -> dict[UUID | None, tuple[str, float, float]]:
    stmt = (
        select(
            PurchaseRequisition.procurement_category_id,
            ProcurementCategory.label_zh,
            func.coalesce(func.avg(POItem.unit_price), 0),
            func.coalesce(func.sum(POItem.qty), 0),
        )
        .select_from(POItem)
        .join(PurchaseOrder, POItem.po_id == PurchaseOrder.id)
        .join(PurchaseRequisition, PurchaseOrder.pr_id == PurchaseRequisition.id)
        .outerjoin(
            ProcurementCategory,
            PurchaseRequisition.procurement_category_id == ProcurementCategory.id,
        )
        .where(PurchaseOrder.created_at >= start, PurchaseOrder.created_at < end)
        .group_by(PurchaseRequisition.procurement_category_id, ProcurementCategory.label_zh)
    )
    if user.role == UserRole.REQUESTER.value:
        stmt = stmt.where(PurchaseRequisition.requester_id == user.id)
    elif user.role == UserRole.DEPT_MANAGER.value and user.department_id:
        stmt = stmt.where(PurchaseRequisition.department_id == user.department_id)
    rows = (await db.execute(stmt)).all()
    return {row[0]: (row[1] or "未分类", _money(row[2]), _money(row[3])) for row in rows}


@router.get("/category-trends", response_model=list[CategoryTrendItem])
async def category_trends(
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[CategoryTrendItem]:
    prev_start, current_start, current_end = _current_and_previous_quarter()
    current = await _category_rows(db, current_start, current_end, user)
    previous = await _category_rows(db, prev_start, current_start, user)
    items: list[CategoryTrendItem] = []
    for category_id in set(current) | set(previous):
        current_name, current_price, current_volume = current.get(
            category_id, (previous.get(category_id, ("未分类", 0.0, 0.0))[0], 0.0, 0.0)
        )
        _prev_name, prev_price, prev_volume = previous.get(category_id, (current_name, 0.0, 0.0))
        change_pct = (
            0.0 if prev_price == 0 else round((current_price - prev_price) / prev_price * 100, 2)
        )
        items.append(
            CategoryTrendItem(
                category_id=str(category_id) if category_id else None,
                category_name=current_name,
                avg_price_current=round(current_price, 4),
                avg_price_prev=round(prev_price, 4),
                change_pct=change_pct,
                volume_current=round(current_volume, 4),
                volume_prev=round(prev_volume, 4),
            )
        )
    return sorted(items, key=lambda item: abs(item.change_pct), reverse=True)


@router.get("/approval-bottleneck")
async def approval_bottleneck(
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    instance_stmt = select(ApprovalInstance)
    if user.role == UserRole.REQUESTER.value:
        instance_stmt = instance_stmt.where(ApprovalInstance.submitter_id == user.id)
    instances = (await db.execute(instance_stmt)).scalars().all()
    completed = [i for i in instances if i.submitted_at and i.completed_at]
    avg_time = None
    if completed:
        avg_time = round(
            sum((i.completed_at - i.submitted_at).total_seconds() / 3600 for i in completed)
            / len(completed),
            2,
        )

    task_stmt = select(ApprovalTask)
    if user.role == UserRole.REQUESTER.value:
        task_stmt = task_stmt.join(ApprovalInstance).where(ApprovalInstance.submitter_id == user.id)
    tasks = (await db.execute(task_stmt)).scalars().all()
    stages_by_name: dict[str, list[ApprovalTask]] = {}
    for task in tasks:
        stages_by_name.setdefault(task.stage_name, []).append(task)
    stages = []
    for label, stage_tasks in stages_by_name.items():
        acted = [t for t in stage_tasks if t.acted_at]
        avg_hours = 0.0
        if acted:
            avg_hours = round(
                sum((t.acted_at - t.assigned_at).total_seconds() / 3600 for t in acted)
                / len(acted),
                2,
            )
        stages.append(
            {
                "stage_label": label,
                "avg_hours": avg_hours,
                "pending_count": len([t for t in stage_tasks if t.status == "pending"]),
                "completed_count": len([t for t in stage_tasks if t.status != "pending"]),
            }
        )

    now = datetime.now(UTC)
    approver_rows = (
        await db.execute(
            select(User.id, User.display_name, ApprovalTask.assigned_at)
            .join(ApprovalTask, ApprovalTask.assignee_id == User.id)
            .where(ApprovalTask.status == "pending")
        )
    ).all()
    approvers: dict[UUID, dict] = {}
    for user_id, display_name, assigned_at in approver_rows:
        item = approvers.setdefault(
            user_id,
            {"user_id": str(user_id), "display_name": display_name, "ages": []},
        )
        item["ages"].append((now - assigned_at).total_seconds() / 3600)
    top_pending = sorted(approvers.values(), key=lambda item: len(item["ages"]), reverse=True)[:5]
    top_pending_approvers = [
        {
            "user_id": item["user_id"],
            "display_name": item["display_name"],
            "pending_count": len(item["ages"]),
            "avg_age_hours": round(sum(item["ages"]) / len(item["ages"]), 2),
        }
        for item in top_pending
    ]
    since_30d = now - timedelta(days=30)
    return {
        "avg_time_to_approve": avg_time,
        "stages": sorted(stages, key=lambda s: s["stage_label"]),
        "top_pending_approvers": top_pending_approvers,
        "total_pending": len([t for t in tasks if t.status == "pending"]),
        "total_approved_30d": len(
            [
                t
                for t in tasks
                if t.status == "completed"
                and t.action == "approve"
                and t.acted_at
                and t.acted_at >= since_30d
            ]
        ),
        "total_rejected_30d": len(
            [t for t in tasks if t.action == "reject" and t.acted_at and t.acted_at >= since_30d]
        ),
    }


@router.get("/cash-flow-forecast")
async def cash_flow_forecast(
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    months: Annotated[int, Query(ge=1, le=12)] = 3,
) -> dict:
    _ = user
    start = _month_start(datetime.now(UTC).date())
    buckets = {
        _add_months(start, i).strftime("%Y-%m"): {"planned": 0.0, "confirmed": 0.0}
        for i in range(months)
    }
    end = _add_months(start, months)
    planned_rows = (
        await db.execute(
            select(PaymentSchedule.planned_date, PaymentSchedule.planned_amount).where(
                PaymentSchedule.planned_date.isnot(None),
                PaymentSchedule.planned_date >= start,
                PaymentSchedule.planned_date < end,
                PaymentSchedule.status != "paid",
            )
        )
    ).all()
    for planned_date, amount in planned_rows:
        buckets[planned_date.strftime("%Y-%m")]["planned"] += _money(amount)
    confirmed_rows = (
        await db.execute(
            select(PaymentRecord.payment_date, PaymentRecord.amount).where(
                PaymentRecord.payment_date.isnot(None),
                PaymentRecord.payment_date >= start,
                PaymentRecord.payment_date < end,
                PaymentRecord.status == PaymentStatus.CONFIRMED.value,
            )
        )
    ).all()
    for payment_date, amount in confirmed_rows:
        buckets[payment_date.strftime("%Y-%m")]["confirmed"] += _money(amount)
    month_items = [
        {
            "month": month,
            "planned": round(values["planned"], 2),
            "confirmed": round(values["confirmed"], 2),
            "net_outflow": round(values["planned"] - values["confirmed"], 2),
        }
        for month, values in buckets.items()
    ]
    return {
        "months": month_items,
        "total_planned": round(sum(item["planned"] for item in month_items), 2),
        "total_confirmed": round(sum(item["confirmed"] for item in month_items), 2),
    }


async def _quarter_snapshot(
    db: AsyncSession, user: CurrentUser, quarter: str
) -> tuple[dict, datetime, datetime, datetime]:
    prev_start, start, end = _parse_quarter(quarter)
    po_stmt = select(PurchaseOrder).where(
        PurchaseOrder.created_at >= start, PurchaseOrder.created_at < end
    )
    po_stmt = _po_scoped_stmt(po_stmt, user)
    pos = (await db.execute(po_stmt)).scalars().all()
    prev_stmt = select(
        func.coalesce(func.sum(PurchaseOrder.total_amount), 0), func.count(PurchaseOrder.id)
    ).where(
        PurchaseOrder.created_at >= prev_start,
        PurchaseOrder.created_at < start,
    )
    prev_stmt = _po_scoped_stmt(prev_stmt, user)
    prev_amount, prev_count = (await db.execute(prev_stmt)).one()
    top_suppliers = sorted(
        [
            {"supplier_id": str(row[0]), "supplier_name": row[1], "amount": _money(row[2])}
            for row in (
                await db.execute(
                    select(
                        Supplier.id,
                        Supplier.name,
                        func.coalesce(func.sum(PurchaseOrder.total_amount), 0),
                    )
                    .join(PurchaseOrder, PurchaseOrder.supplier_id == Supplier.id)
                    .where(PurchaseOrder.created_at >= start, PurchaseOrder.created_at < end)
                    .group_by(Supplier.id, Supplier.name)
                )
            ).all()
        ],
        key=lambda item: item["amount"],
        reverse=True,
    )[:5]
    top_categories = sorted(
        [
            {
                "category_id": str(row[0]) if row[0] else None,
                "category_name": row[1] or "未分类",
                "amount": _money(row[2]),
            }
            for row in (
                await db.execute(
                    select(
                        PurchaseRequisition.procurement_category_id,
                        ProcurementCategory.label_zh,
                        func.coalesce(func.sum(PurchaseOrder.total_amount), 0),
                    )
                    .join(PurchaseRequisition, PurchaseOrder.pr_id == PurchaseRequisition.id)
                    .outerjoin(
                        ProcurementCategory,
                        PurchaseRequisition.procurement_category_id == ProcurementCategory.id,
                    )
                    .where(PurchaseOrder.created_at >= start, PurchaseOrder.created_at < end)
                    .group_by(
                        PurchaseRequisition.procurement_category_id, ProcurementCategory.label_zh
                    )
                )
            ).all()
        ],
        key=lambda item: item["amount"],
        reverse=True,
    )[:5]
    anomaly_count = int(
        (
            await db.execute(
                select(func.count(SKUPriceAnomaly.id)).where(
                    SKUPriceAnomaly.created_at >= start,
                    SKUPriceAnomaly.created_at < end,
                )
            )
        ).scalar()
        or 0
    )
    snapshot = {
        "total_pos": len(pos),
        "total_amount": round(sum(_money(po.total_amount) for po in pos), 2),
        "previous_quarter_pos": int(prev_count or 0),
        "previous_quarter_amount": _money(prev_amount),
        "top_suppliers": top_suppliers,
        "top_categories": top_categories,
        "anomaly_count": anomaly_count,
    }
    return snapshot, prev_start, start, end


@router.get("/quarterly-summary")
async def quarterly_summary(
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    quarter: Annotated[str, Query(pattern=r"^\d{4}-Q[1-4]$")],
) -> dict:
    cache_key = f"quarterly_summary:{quarter}"
    now = datetime.now(UTC)
    cached = (
        await db.execute(
            select(InsightCache).where(
                InsightCache.cache_key == cache_key,
                InsightCache.expires_at > now,
            )
        )
    ).scalar_one_or_none()
    if cached:
        return cached.content

    snapshot, _prev_start, _start, _end = await _quarter_snapshot(db, user, quarter)
    prompt = (
        "You are a procurement analyst. Summarize this quarter's procurement activity "
        "in 3-4 concise paragraphs in Chinese. Include: total volume/amount, comparison "
        "to last quarter, notable trends, and any concerns.\n\nData:\n"
        f"{json.dumps(snapshot, ensure_ascii=False)}"
    )
    summary_text = "Summary generation failed"
    try:
        model = (
            await db.execute(
                select(AIModel)
                .where(AIModel.is_active.is_(True))
                .order_by(AIModel.priority)
                .limit(1)
            )
        ).scalar_one_or_none()
        if model is not None:
            response = await litellm.acompletion(
                model=resolve_litellm_model(model.provider, model.model_string),
                messages=[{"role": "user", "content": prompt}],
                api_base=model.api_base or None,
                api_key=model.api_key_encrypted or None,
                timeout=60,
            )
            summary_text = response.choices[0].message.content or summary_text
    except Exception:
        summary_text = "Summary generation failed"
    generated_at = datetime.now(UTC)
    content = {
        "quarter": quarter,
        "summary_text": summary_text,
        "generated_at": generated_at.isoformat(),
        "data_snapshot": snapshot,
    }
    if cached is None:
        db.add(
            InsightCache(
                cache_key=cache_key,
                content=content,
                generated_at=generated_at,
                expires_at=generated_at + timedelta(hours=24),
            )
        )
    else:
        cached.content = content
        cached.generated_at = generated_at
        cached.expires_at = generated_at + timedelta(hours=24)
    await db.commit()
    return content


@router.get("/anomaly-wall")
async def anomaly_wall(
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    _ = user
    now = datetime.now(UTC)
    anomalies: list[dict] = []
    price_rows = (
        await db.execute(
            select(SKUPriceAnomaly, Item.name)
            .join(Item, SKUPriceAnomaly.item_id == Item.id)
            .where(
                SKUPriceAnomaly.status == "new",
                SKUPriceAnomaly.created_at >= now - timedelta(days=30),
            )
            .order_by(SKUPriceAnomaly.created_at.desc())
            .limit(30)
        )
    ).all()
    for anomaly, item_name in price_rows:
        anomalies.append(
            {
                "type": "price_anomaly",
                "severity": anomaly.severity,
                "title": f"SKU price anomaly: {item_name}",
                "description": f"Observed price deviates {anomaly.deviation_pct}% from benchmark.",
                "link": f"/sku/anomalies/{anomaly.id}",
                "created_at": anomaly.created_at.isoformat(),
            }
        )

    overdue_rows = (
        await db.execute(
            select(
                PurchaseOrder.id,
                PurchaseOrder.po_number,
                PurchaseOrder.pr_title,
                PurchaseOrder.created_at,
            )
            .outerjoin(Shipment, Shipment.po_id == PurchaseOrder.id)
            .where(
                PurchaseOrder.status == POStatus.CONFIRMED.value,
                PurchaseOrder.created_at <= now - timedelta(days=30),
                Shipment.id.is_(None),
            )
            .order_by(PurchaseOrder.created_at)
            .limit(30)
        )
    ).all()
    for po_id, po_number, title, created_at in overdue_rows:
        anomalies.append(
            {
                "type": "overdue_delivery",
                "severity": "warning",
                "title": f"Overdue PO delivery: {po_number}",
                "description": f"{title or po_number} has no shipment after 30 days.",
                "link": f"/purchase-orders/{po_id}",
                "created_at": created_at.isoformat(),
            }
        )

    stale_rows = (
        await db.execute(
            select(ApprovalTask, User.display_name)
            .join(User, ApprovalTask.assignee_id == User.id)
            .where(
                ApprovalTask.status == "pending",
                ApprovalTask.assigned_at <= now - timedelta(hours=72),
            )
            .order_by(ApprovalTask.assigned_at)
            .limit(30)
        )
    ).all()
    for task, display_name in stale_rows:
        age = int((now - task.assigned_at).total_seconds() // 3600)
        anomalies.append(
            {
                "type": "approval_stale",
                "severity": "warning",
                "title": f"Approval pending over 72h: {task.stage_name}",
                "description": f"Pending with {display_name} for {age} hours.",
                "link": f"/approval/{task.instance_id}",
                "created_at": task.assigned_at.isoformat(),
            }
        )

    concentration_rows = (
        await db.execute(
            select(
                PurchaseRequisition.procurement_category_id,
                ProcurementCategory.label_zh,
                PurchaseOrder.supplier_id,
                Supplier.name,
                func.coalesce(func.sum(PurchaseOrder.total_amount), 0),
            )
            .join(PurchaseRequisition, PurchaseOrder.pr_id == PurchaseRequisition.id)
            .join(Supplier, PurchaseOrder.supplier_id == Supplier.id)
            .outerjoin(
                ProcurementCategory,
                PurchaseRequisition.procurement_category_id == ProcurementCategory.id,
            )
            .where(PurchaseOrder.created_at >= now - timedelta(days=90))
            .group_by(
                PurchaseRequisition.procurement_category_id,
                ProcurementCategory.label_zh,
                PurchaseOrder.supplier_id,
                Supplier.name,
            )
        )
    ).all()
    category_totals: dict[UUID | None, float] = {}
    for category_id, _category_name, _supplier_id, _supplier_name, amount in concentration_rows:
        category_totals[category_id] = category_totals.get(category_id, 0.0) + _money(amount)
    for category_id, category_name, supplier_id, supplier_name, amount in concentration_rows:
        total = category_totals.get(category_id, 0.0)
        share = _pct(_money(amount), total)
        if total > 0 and share > 80:
            anomalies.append(
                {
                    "type": "supplier_concentration",
                    "severity": "critical" if share >= 95 else "warning",
                    "title": f"Supplier concentration: {category_name or '未分类'}",
                    "description": f"{supplier_name} accounts for {share}% of category spend in 90 days.",
                    "link": f"/suppliers/{supplier_id}",
                    "created_at": now.isoformat(),
                }
            )
    anomalies.sort(key=lambda item: item["created_at"], reverse=True)
    return {"anomalies": anomalies[:100]}
