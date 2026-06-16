from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser
from app.db import get_db
from app.models import (
    RFQ,
    AuditLog,
    Contract,
)

router = APIRouter(tags=["activity-logs"])


_ALLOWED_RESOURCE_TYPES = {
    "purchase_requisition",
    "purchase_order",
    "po_item",
    "contract",
    "rfq",
    "invoice",
    "payment_record",
    "shipment",
    "pr_fulfillment_link",
}

_BLOCKED_EVENT_PREFIXES = (
    "auth.",
    "admin.",
    "notification.",
)


class ActivityLogOut(BaseModel):
    id: UUID
    occurred_at: datetime
    actor_name: str | None
    event_type: str
    resource_type: str | None
    resource_id: str | None
    comment: str | None
    metadata: dict[str, Any] | None


async def _check_resource_access(
    db: AsyncSession, user, resource_type: str, resource_id: str
) -> None:
    from app.core.scoping import (
        has_full_access,
    )
    from app.services import purchase as purchase_svc

    if has_full_access(user):
        return

    try:
        resource_uuid = UUID(resource_id)
    except (ValueError, TypeError) as exc:
        raise HTTPException(404, "activity.resource_not_found") from exc

    if resource_type == "purchase_requisition":
        await purchase_svc.get_pr(db, user, resource_uuid)
        return

    if resource_type == "purchase_order":
        await purchase_svc.get_po(db, resource_uuid, actor=user)
        return

    if resource_type == "po_item":
        from app.models import POItem

        po_item = await db.get(POItem, resource_uuid)
        if po_item is None:
            raise HTTPException(404, "activity.resource_not_found")
        await purchase_svc.get_po(db, po_item.po_id, actor=user)
        return

    if resource_type == "contract":
        contract = await db.get(Contract, resource_uuid)
        if contract is None:
            raise HTTPException(404, "activity.resource_not_found")
        if contract.po_id:
            await purchase_svc.get_po(db, contract.po_id, actor=user)
        return

    if resource_type == "rfq":
        rfq = await db.get(RFQ, resource_uuid)
        if rfq is None:
            raise HTTPException(404, "activity.resource_not_found")
        if rfq.pr_id:
            await purchase_svc.get_pr(db, user, rfq.pr_id)
        return

    if resource_type == "shipment":
        from app.models import Shipment

        sh = await db.get(Shipment, resource_uuid)
        if sh is None:
            raise HTTPException(404, "activity.resource_not_found")
        await purchase_svc.get_po(db, sh.po_id, actor=user)
        return

    if resource_type == "invoice":
        from app.models import Invoice, InvoiceLine, POItem

        inv = await db.get(Invoice, resource_uuid)
        if inv is None:
            raise HTTPException(404, "activity.resource_not_found")
        line_po_ids = (
            await db.execute(
                select(POItem.po_id)
                .join(InvoiceLine, InvoiceLine.po_item_id == POItem.id)
                .where(InvoiceLine.invoice_id == inv.id)
                .limit(1)
            )
        ).scalar_one_or_none()
        if line_po_ids is not None:
            await purchase_svc.get_po(db, line_po_ids, actor=user)
        return

    if resource_type == "payment_record":
        from app.models import PaymentRecord

        p = await db.get(PaymentRecord, resource_uuid)
        if p is None:
            raise HTTPException(404, "activity.resource_not_found")
        if p.po_id:
            await purchase_svc.get_po(db, p.po_id, actor=user)
        return

    if resource_type == "pr_fulfillment_link":
        from app.models import PRFulfillmentLink, PRItem

        link = await db.get(PRFulfillmentLink, resource_uuid)
        if link is None:
            raise HTTPException(404, "activity.resource_not_found")
        pr_item = await db.get(PRItem, link.pr_item_id)
        if pr_item is None:
            raise HTTPException(404, "activity.resource_not_found")
        await purchase_svc.get_pr(db, user, pr_item.pr_id)
        return

    raise HTTPException(403, "activity.access_denied")


@router.get(
    "/resource-activity-logs",
    response_model=list[ActivityLogOut],
)
async def list_resource_activity_logs(
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    resource_type: str = Query(..., description="Resource type (e.g. purchase_requisition)"),
    resource_id: str = Query(..., description="Resource UUID"),
    page_size: int = Query(50, ge=1, le=200),
):
    if resource_type not in _ALLOWED_RESOURCE_TYPES:
        raise HTTPException(400, "activity.unsupported_resource_type")

    await _check_resource_access(db, user, resource_type, resource_id)

    stmt = (
        select(AuditLog)
        .where(
            AuditLog.resource_type == resource_type,
            AuditLog.resource_id == resource_id,
        )
        .order_by(AuditLog.occurred_at.desc())
        .limit(page_size)
    )
    rows = (await db.execute(stmt)).scalars().all()

    out: list[ActivityLogOut] = []
    for row in rows:
        if any(row.event_type.startswith(p) for p in _BLOCKED_EVENT_PREFIXES):
            continue
        out.append(
            ActivityLogOut(
                id=row.id,
                occurred_at=row.occurred_at,
                actor_name=row.actor_name,
                event_type=row.event_type,
                resource_type=row.resource_type,
                resource_id=row.resource_id,
                comment=row.comment,
                metadata=row.metadata_json,
            )
        )
    return out
