from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
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
    PurchaseOrder,
    PurchaseRequisition,
    SKUPriceAnomaly,
)

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

    return DashboardMetricsOut(
        pr_count=_make_trend(pr_curr, pr_prev),
        po_count=_make_trend(po_curr, po_prev),
        po_total_amount=_make_trend(float(amt_curr), float(amt_prev)),
        pending_approvals=_make_trend(pend_curr, pend_prev),
        expiring_contracts_30d=expiring_soon,
        price_anomalies_pending=anomalies_pending,
    )
