from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import CurrentUser
from app.db import get_db
from app.models import (
    ApprovalTask,
    POStatus,
    PurchaseOrder,
    PurchaseRequisition,
    Shipment,
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
        await db.execute(
            select(UserDashboardConfig).where(
                UserDashboardConfig.user_id == user.id
            )
        )
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
        await db.execute(
            select(UserDashboardConfig).where(
                UserDashboardConfig.user_id == user.id
            )
        )
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
        pr_query = pr_query.where(
            PurchaseRequisition.department_id == user.department_id
        )

    prs = (await db.execute(pr_query)).scalars().all()
    pr_ids = [pr.id for pr in prs]
    if not pr_ids:
        return []

    pos = (
        (
            await db.execute(
                select(PurchaseOrder)
                .where(PurchaseOrder.pr_id.in_(pr_ids))
            )
        )
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
                expected_date=str(latest.expected_date) if latest and latest.expected_date else None,
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
    tasks = (
        (
            await db.execute(
                select(ApprovalTask)
                .where(
                    ApprovalTask.assignee_id == user.id,
                    ApprovalTask.status == "pending",
                )
                .order_by(ApprovalTask.created_at.desc())
                .limit(20)
            )
        )
        .scalars()
        .all()
    )
    for t in tasks:
        pending_approvals.append({
            "id": str(t.id),
            "type": "approval",
            "title": t.stage_label or "Approval",
            "created_at": t.created_at.isoformat(),
        })

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
            PurchaseOrder.status.in_([
                POStatus.CONFIRMED.value,
                POStatus.PARTIALLY_RECEIVED.value,
            ])
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
            PurchaseOrder.status.in_([
                POStatus.FULLY_RECEIVED.value,
                POStatus.CLOSED.value,
            ]),
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
