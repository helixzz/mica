from __future__ import annotations

# pyright: reportUnknownParameterType=false, reportMissingParameterType=false, reportExplicitAny=false
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    AuditLog,
    JSONValue,
    POItem,
    POStatus,
    PRItem,
    PRStatus,
    PurchaseOrder,
    PurchaseRequisition,
    User,
    UserRole,
)
from app.schemas import PRCreateIn, PRDecisionIn, PRUpdateIn
from app.services import approval as approval_svc


def _as_decimal(v: Decimal | int | float | str) -> Decimal:
    return v if isinstance(v, Decimal) else Decimal(str(v))


def _compute_line_amount(qty: Decimal, unit_price: Decimal) -> Decimal:
    return (_as_decimal(qty) * _as_decimal(unit_price)).quantize(Decimal("0.0001"))


async def _next_pr_number(db: AsyncSession) -> str:
    year = datetime.now(UTC).year
    prefix = f"PR-{year}-"
    result = await db.execute(
        select(func.count(PurchaseRequisition.id)).where(
            PurchaseRequisition.pr_number.startswith(prefix)
        )
    )
    n = (result.scalar_one() or 0) + 1
    return f"{prefix}{n:04d}"


async def _next_po_number(db: AsyncSession) -> str:
    year = datetime.now(UTC).year
    prefix = f"PO-{year}-"
    result = await db.execute(
        select(func.count(PurchaseOrder.id)).where(PurchaseOrder.po_number.startswith(prefix))
    )
    n = (result.scalar_one() or 0) + 1
    return f"{prefix}{n:04d}"


async def _audit(
    db: AsyncSession,
    actor: User,
    event_type: str,
    resource_type: str,
    resource_id: str,
    comment: str | None = None,
    metadata: dict[str, JSONValue] | None = None,
) -> None:
    db.add(
        AuditLog(
            actor_id=actor.id,
            actor_name=actor.display_name,
            event_type=event_type,
            resource_type=resource_type,
            resource_id=resource_id,
            comment=comment,
            metadata_json=metadata,
        )
    )


async def create_pr(db: AsyncSession, actor: User, payload: PRCreateIn) -> PurchaseRequisition:
    pr_number = await _next_pr_number(db)
    pr = PurchaseRequisition(
        pr_number=pr_number,
        title=payload.title,
        business_reason=payload.business_reason,
        status=PRStatus.DRAFT.value,
        requester_id=actor.id,
        company_id=actor.company_id,
        department_id=payload.department_id or actor.department_id,
        currency=payload.currency,
        required_date=payload.required_date,
    )
    db.add(pr)
    await db.flush()

    total = Decimal("0")
    for i, item_in in enumerate(payload.items, start=1):
        amount = _compute_line_amount(item_in.qty, item_in.unit_price)
        total += amount
        db.add(
            PRItem(
                pr_id=pr.id,
                line_no=item_in.line_no or i,
                item_id=item_in.item_id,
                item_name=item_in.item_name,
                specification=item_in.specification,
                supplier_id=item_in.supplier_id,
                qty=_as_decimal(item_in.qty),
                uom=item_in.uom,
                unit_price=_as_decimal(item_in.unit_price),
                amount=amount,
            )
        )
    pr.total_amount = total
    await _audit(
        db,
        actor,
        "pr.created",
        "purchase_requisition",
        str(pr.id),
        metadata={"pr_number": pr.pr_number},
    )
    await db.commit()
    await db.refresh(pr)
    result = await _load_pr(db, pr.id)
    if result is None:
        raise HTTPException(404, "pr.not_found")
    return result


async def update_pr(
    db: AsyncSession, actor: User, pr_id: UUID, payload: PRUpdateIn
) -> PurchaseRequisition:
    pr = await _load_pr(db, pr_id)
    if pr is None:
        raise HTTPException(404, "pr.not_found")
    if pr.requester_id != actor.id and actor.role not in (
        UserRole.ADMIN.value,
        UserRole.IT_BUYER.value,
        UserRole.PROCUREMENT_MGR.value,
    ):
        raise HTTPException(403, "insufficient_role")
    if pr.status == PRStatus.DRAFT.value:
        pass
    elif pr.status == "approved" and actor.role in (
        UserRole.IT_BUYER.value,
        UserRole.PROCUREMENT_MGR.value,
        UserRole.ADMIN.value,
    ):
        pass
    else:
        raise HTTPException(409, "pr.cannot_edit_submitted")

    if payload.title is not None:
        pr.title = payload.title
    if payload.business_reason is not None:
        pr.business_reason = payload.business_reason
    if payload.department_id is not None:
        pr.department_id = payload.department_id
    if payload.currency is not None:
        pr.currency = payload.currency
    if payload.required_date is not None:
        pr.required_date = payload.required_date

    if payload.items is not None:
        for old in list(pr.items):
            await db.delete(old)
        await db.flush()
        total = Decimal("0")
        for i, item_in in enumerate(payload.items, start=1):
            amount = _compute_line_amount(item_in.qty, item_in.unit_price)
            total += amount
            db.add(
                PRItem(
                    pr_id=pr.id,
                    line_no=item_in.line_no or i,
                    item_id=item_in.item_id,
                    item_name=item_in.item_name,
                    specification=item_in.specification,
                    supplier_id=item_in.supplier_id,
                    qty=_as_decimal(item_in.qty),
                    uom=item_in.uom,
                    unit_price=_as_decimal(item_in.unit_price),
                    amount=amount,
                )
            )
        pr.total_amount = total

    await _audit(db, actor, "pr.updated", "purchase_requisition", str(pr.id))
    await db.commit()
    result = await _load_pr(db, pr.id)
    if result is None:
        raise HTTPException(404, "pr.not_found")
    return result


async def submit_pr(db: AsyncSession, actor: User, pr_id: UUID) -> PurchaseRequisition:
    pr = await _load_pr(db, pr_id)
    if pr is None:
        raise HTTPException(404, "pr.not_found")
    if pr.requester_id != actor.id and actor.role != UserRole.ADMIN.value:
        raise HTTPException(403, "insufficient_role")
    if pr.status != PRStatus.DRAFT.value:
        raise HTTPException(409, "pr.cannot_submit_non_draft")
    if not pr.items:
        raise HTTPException(422, "pr.no_items")

    pr.status = PRStatus.SUBMITTED.value
    pr.submitted_at = datetime.now(UTC)

    _ = await approval_svc.create_instance_for_pr(
        db,
        submitter=actor,
        biz_type="purchase_requisition",
        biz_id=pr.id,
        biz_number=pr.pr_number,
        title=pr.title,
        amount=pr.total_amount,
    )
    await _audit(db, actor, "pr.submitted", "purchase_requisition", str(pr.id))
    await db.commit()
    result = await _load_pr(db, pr.id)
    if result is None:
        raise HTTPException(404, "pr.not_found")
    return result


async def decide_pr(
    db: AsyncSession, actor: User, pr_id: UUID, payload: PRDecisionIn
) -> PurchaseRequisition:
    pr = await _load_pr(db, pr_id)
    if pr is None:
        raise HTTPException(404, "pr.not_found")
    if pr.status != PRStatus.SUBMITTED.value:
        raise HTTPException(409, "pr.cannot_decide_non_submitted")

    instance = await approval_svc.get_instance_for_biz(db, "purchase_requisition", pr.id)
    if instance is None:
        raise HTTPException(404, "pr.approval_not_found")
    instance = await approval_svc.act_on_task(
        db, actor, instance.id, payload.action, payload.comment
    )

    if instance.status == "approved":
        pr.status = PRStatus.APPROVED.value
        pr.decided_at = datetime.now(UTC)
        pr.decided_by_id = actor.id
        pr.decision_comment = payload.comment
    elif instance.status == "rejected":
        pr.status = PRStatus.REJECTED.value
        pr.decided_at = datetime.now(UTC)
        pr.decided_by_id = actor.id
        pr.decision_comment = payload.comment
    elif instance.status == "returned":
        pr.status = PRStatus.RETURNED.value
        pr.decided_at = datetime.now(UTC)
        pr.decided_by_id = actor.id
        pr.decision_comment = payload.comment
    await _audit(
        db,
        actor,
        f"pr.{payload.action}",
        "purchase_requisition",
        str(pr.id),
        comment=payload.comment,
    )
    await db.commit()
    result = await _load_pr(db, pr.id)
    if result is None:
        raise HTTPException(404, "pr.not_found")
    return result


async def convert_pr_to_po(db: AsyncSession, actor: User, pr_id: UUID) -> PurchaseOrder:
    pr = await _load_pr(db, pr_id)
    if pr is None:
        raise HTTPException(404, "pr.not_found")
    if pr.status != PRStatus.APPROVED.value:
        raise HTTPException(409, "pr.must_be_approved_to_convert")

    supplier_ids = {i.supplier_id for i in pr.items if i.supplier_id}
    if len(supplier_ids) != 1:
        raise HTTPException(422, "pr.multiple_suppliers_not_supported_in_skeleton")
    (supplier_id,) = supplier_ids

    po_number = await _next_po_number(db)
    po = PurchaseOrder(
        po_number=po_number,
        pr_id=pr.id,
        supplier_id=supplier_id,
        company_id=pr.company_id,
        status=POStatus.CONFIRMED.value,
        currency=pr.currency,
        total_amount=pr.total_amount,
        source_type="manual",
        created_by_id=actor.id,
    )
    db.add(po)
    await db.flush()
    for i, pr_item in enumerate(pr.items, start=1):
        db.add(
            POItem(
                po_id=po.id,
                pr_item_id=pr_item.id,
                line_no=i,
                item_id=pr_item.item_id,
                item_name=pr_item.item_name,
                specification=pr_item.specification,
                qty=pr_item.qty,
                uom=pr_item.uom,
                unit_price=pr_item.unit_price,
                amount=pr_item.amount,
            )
        )

    pr.status = PRStatus.CONVERTED.value
    await _audit(
        db,
        actor,
        "po.created_from_pr",
        "purchase_order",
        str(po.id),
        metadata={"pr_id": str(pr.id), "pr_number": pr.pr_number, "po_number": po.po_number},
    )
    await db.commit()
    result = await _load_po(db, po.id)
    if result is None:
        raise HTTPException(404, "po.not_found")
    return result


async def _load_pr(db: AsyncSession, pr_id: UUID) -> PurchaseRequisition | None:
    result = await db.execute(
        select(PurchaseRequisition)
        .where(PurchaseRequisition.id == pr_id)
        .options(selectinload(PurchaseRequisition.items))
    )
    return result.scalar_one_or_none()


async def _load_po(db: AsyncSession, po_id: UUID) -> PurchaseOrder | None:
    result = await db.execute(
        select(PurchaseOrder)
        .where(PurchaseOrder.id == po_id)
        .options(selectinload(PurchaseOrder.items))
    )
    return result.scalar_one_or_none()


async def list_prs_for_user(db: AsyncSession, actor: User) -> list[PurchaseRequisition]:
    stmt = select(PurchaseRequisition).order_by(PurchaseRequisition.created_at.desc())
    if actor.role in {UserRole.IT_BUYER.value}:
        stmt = stmt.where(PurchaseRequisition.requester_id == actor.id)
    elif actor.role == UserRole.DEPT_MANAGER.value and actor.department_id:
        stmt = stmt.where(PurchaseRequisition.department_id == actor.department_id)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_pr(db: AsyncSession, actor: User, pr_id: UUID) -> PurchaseRequisition:
    pr = await _load_pr(db, pr_id)
    if pr is None:
        raise HTTPException(404, "pr.not_found")
    if actor.role == UserRole.IT_BUYER.value and pr.requester_id != actor.id:
        raise HTTPException(403, "insufficient_role")
    if (
        actor.role == UserRole.DEPT_MANAGER.value
        and actor.department_id
        and pr.department_id != actor.department_id
        and pr.requester_id != actor.id
    ):
        raise HTTPException(403, "insufficient_role")
    return pr


async def list_pos(db: AsyncSession, actor: User) -> list[PurchaseOrder]:
    _ = actor
    stmt = select(PurchaseOrder).order_by(PurchaseOrder.created_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_po(db: AsyncSession, po_id: UUID) -> PurchaseOrder:
    po = await _load_po(db, po_id)
    if po is None:
        raise HTTPException(404, "po.not_found")
    return po
