from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser
from app.db import get_db
from app.models import (
    ApprovalTask,
    Contract,
    CostCenter,
    Invoice,
    InvoiceStatus,
    PaymentRecord,
    PaymentStatus,
    PurchaseOrder,
    PurchaseRequisition,
    SKUPriceAnomaly,
)
from app.services.system_params import system_params

router = APIRouter(tags=["dashboard"])

TrendDirection = Literal["up", "down", "flat"]


class TrendOut(BaseModel):
    current: float
    previous: float
    direction: TrendDirection
    delta_pct: str


class DashboardMetricsOut(BaseModel):
    pr_count: TrendOut
    po_count: TrendOut
    po_total_amount: TrendOut
    pending_approvals: TrendOut
    expiring_contracts_30d: int
    price_anomalies_pending: int
    invoices_pending_match: int
    invoices_mismatched: int


class BudgetSummaryItem(BaseModel):
    cost_center_id: str
    code: str
    label_zh: str
    label_en: str
    annual_budget: float | None
    actual_spend: float
    utilization_pct: float


class BudgetSummaryOut(BaseModel):
    items: list[BudgetSummaryItem]
    total_budget: float
    total_spend: float
    total_utilization_pct: float


@dataclass
class _Window:
    start: datetime
    end: datetime


def _compare_windows(compare_to: str) -> tuple[_Window, _Window]:
    now = datetime.now(UTC)
    if compare_to == "last_month":
        current = _Window(
            start=now.replace(day=1, hour=0, minute=0, second=0, microsecond=0),
            end=now,
        )
        prev_start = (current.start - timedelta(days=1)).replace(day=1)
        prev_end = current.start
        previous = _Window(start=prev_start, end=prev_end)
    else:
        current = _Window(start=now - timedelta(days=7), end=now)
        previous = _Window(start=current.start - timedelta(days=7), end=current.start)
    return current, previous


def _make_trend(current: float, previous: float) -> TrendOut:
    if previous == 0 and current == 0:
        direction: TrendDirection = "flat"
        pct = "0%"
    elif previous == 0:
        direction = "up"
        pct = "+100%"
    else:
        delta = (current - previous) / previous * 100
        if abs(delta) < 0.5:
            direction = "flat"
            pct = "0%"
        elif delta > 0:
            direction = "up"
            pct = f"+{delta:.0f}%"
        else:
            direction = "down"
            pct = f"{delta:.0f}%"
    return TrendOut(
        current=float(current), previous=float(previous), direction=direction, delta_pct=pct
    )


async def _count_in_window(db: AsyncSession, model, start: datetime, end: datetime) -> int:
    stmt = select(func.count(model.id)).where(model.created_at >= start, model.created_at < end)
    return int((await db.execute(stmt)).scalar() or 0)


async def _sum_po_amount_in_window(db: AsyncSession, start: datetime, end: datetime) -> Decimal:
    stmt = select(func.coalesce(func.sum(PurchaseOrder.total_amount), 0)).where(
        PurchaseOrder.created_at >= start, PurchaseOrder.created_at < end
    )
    return Decimal(str((await db.execute(stmt)).scalar() or 0))


async def _count_pending_tasks_in_window(db: AsyncSession, start: datetime, end: datetime) -> int:
    stmt = select(func.count(ApprovalTask.id)).where(
        ApprovalTask.created_at >= start,
        ApprovalTask.created_at < end,
        ApprovalTask.status == "pending",
    )
    return int((await db.execute(stmt)).scalar() or 0)


@router.get("/dashboard/metrics", response_model=DashboardMetricsOut)
async def get_dashboard_metrics(
    _user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    compare_to: Annotated[Literal["last_month", "last_week"], Query()] = "last_month",
) -> DashboardMetricsOut:
    current, previous = _compare_windows(compare_to)

    pr_curr = await _count_in_window(db, PurchaseRequisition, current.start, current.end)
    pr_prev = await _count_in_window(db, PurchaseRequisition, previous.start, previous.end)

    po_curr = await _count_in_window(db, PurchaseOrder, current.start, current.end)
    po_prev = await _count_in_window(db, PurchaseOrder, previous.start, previous.end)

    amt_curr = await _sum_po_amount_in_window(db, current.start, current.end)
    amt_prev = await _sum_po_amount_in_window(db, previous.start, previous.end)

    pend_curr = await _count_pending_tasks_in_window(db, current.start, current.end)
    pend_prev = await _count_pending_tasks_in_window(db, previous.start, previous.end)

    now = datetime.now(UTC)
    today = now.date()
    in_30_days = today + timedelta(days=30)
    expiring_soon = int(
        (
            await db.execute(
                select(func.count(Contract.id)).where(
                    Contract.expiry_date.isnot(None),
                    Contract.expiry_date >= today,
                    Contract.expiry_date <= in_30_days,
                )
            )
        ).scalar()
        or 0
    )

    anomalies_pending = int(
        (
            await db.execute(
                select(func.count(SKUPriceAnomaly.id)).where(
                    SKUPriceAnomaly.status.in_(["new", "pending"])
                )
            )
        ).scalar()
        or 0
    )

    pending_match = int(
        (
            await db.execute(
                select(func.count(Invoice.id)).where(
                    Invoice.status == InvoiceStatus.PENDING_MATCH.value
                )
            )
        ).scalar()
        or 0
    )
    mismatched = int(
        (
            await db.execute(
                select(func.count(Invoice.id)).where(
                    Invoice.status == InvoiceStatus.MISMATCHED.value
                )
            )
        ).scalar()
        or 0
    )

    return DashboardMetricsOut(
        pr_count=_make_trend(pr_curr, pr_prev),
        po_count=_make_trend(po_curr, po_prev),
        po_total_amount=_make_trend(float(amt_curr), float(amt_prev)),
        pending_approvals=_make_trend(pend_curr, pend_prev),
        expiring_contracts_30d=expiring_soon,
        price_anomalies_pending=anomalies_pending,
        invoices_pending_match=pending_match,
        invoices_mismatched=mismatched,
    )


@router.get("/dashboard/budget-summary", response_model=BudgetSummaryOut)
async def get_budget_summary(
    _user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BudgetSummaryOut:
    ccs = (
        (
            await db.execute(
                select(CostCenter)
                .where(
                    CostCenter.is_deleted.is_(False),
                    CostCenter.is_enabled.is_(True),
                )
                .order_by(CostCenter.sort_order)
            )
        )
        .scalars()
        .all()
    )

    items: list[BudgetSummaryItem] = []
    total_budget = 0.0
    total_spend = 0.0

    for cc in ccs:
        budget_start = cc.budget_start_date
        budget_end = cc.budget_end_date
        if budget_start is None:
            budget_start = date(datetime.now(UTC).year, 1, 1)
        if budget_end is None:
            budget_end = date(datetime.now(UTC).year, 12, 31)

        start_dt = datetime.combine(budget_start, datetime.min.time()).replace(tzinfo=UTC)
        end_dt = datetime.combine(budget_end, datetime.max.time()).replace(tzinfo=UTC)

        po_spend = float(
            (
                await db.execute(
                    select(func.coalesce(func.sum(PurchaseOrder.amount_paid), 0)).where(
                        PurchaseOrder.pr.has(
                            PurchaseRequisition.cost_center_id == cc.id,
                        ),
                        PurchaseOrder.created_at >= start_dt,
                        PurchaseOrder.created_at <= end_dt,
                    )
                )
            ).scalar()
            or 0
        )

        pmt_spend = float(
            (
                await db.execute(
                    select(func.coalesce(func.sum(PaymentRecord.amount), 0)).where(
                        PaymentRecord.status == PaymentStatus.CONFIRMED.value,
                        PaymentRecord.po.has(
                            PurchaseOrder.pr.has(
                                PurchaseRequisition.cost_center_id == cc.id,
                            ),
                        ),
                        PaymentRecord.created_at >= start_dt,
                        PaymentRecord.created_at <= end_dt,
                    )
                )
            ).scalar()
            or 0
        )

        actual_spend = po_spend + pmt_spend
        annual_budget = float(cc.annual_budget) if cc.annual_budget is not None else None
        utilization_pct = (
            round((actual_spend / annual_budget * 100), 1)
            if annual_budget and annual_budget > 0
            else 0.0
        )

        items.append(
            BudgetSummaryItem(
                cost_center_id=str(cc.id),
                code=cc.code,
                label_zh=cc.label_zh,
                label_en=cc.label_en,
                annual_budget=annual_budget,
                actual_spend=round(actual_spend, 2),
                utilization_pct=utilization_pct,
            )
        )
        if annual_budget:
            total_budget += annual_budget
        total_spend += actual_spend

    total_utilization_pct = (
        round((total_spend / total_budget * 100), 1) if total_budget > 0 else 0.0
    )

    return BudgetSummaryOut(
        items=items,
        total_budget=round(total_budget, 2),
        total_spend=round(total_spend, 2),
        total_utilization_pct=total_utilization_pct,
    )


class AgingApprovalOut(BaseModel):
    pr_id: str
    pr_number: str
    title: str
    hours_since_submission: float
    is_overdue: bool
    is_approaching: bool


@router.get("/dashboard/aging-approvals", response_model=list[AgingApprovalOut])
async def get_aging_approvals(
    _user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[AgingApprovalOut]:
    sla_hours = await system_params.get_int_or(db, "approval.sla_hours", 24)
    sla_alert_enabled = bool(await system_params.get(db, "approval.sla_alert_enabled", True))

    if not sla_alert_enabled:
        return []

    stmt = (
        select(
            PurchaseRequisition.id,
            PurchaseRequisition.pr_number,
            PurchaseRequisition.title,
            PurchaseRequisition.submitted_at,
            func.extract("epoch", func.now() - PurchaseRequisition.submitted_at).label(
                "age_seconds"
            ),
        )
        .where(
            PurchaseRequisition.status == "submitted",
            PurchaseRequisition.submitted_at.isnot(None),
        )
        .order_by(PurchaseRequisition.submitted_at)
    )
    rows = (await db.execute(stmt)).all()

    results: list[AgingApprovalOut] = []
    for row in rows:
        age_seconds = float(row.age_seconds or 0)
        hours = age_seconds / 3600.0
        results.append(
            AgingApprovalOut(
                pr_id=str(row.id),
                pr_number=row.pr_number,
                title=row.title,
                hours_since_submission=round(hours, 1),
                is_overdue=hours > sla_hours,
                is_approaching=not (hours > sla_hours) and hours > sla_hours * 0.5,
            )
        )

    return results
