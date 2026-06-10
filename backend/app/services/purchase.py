from __future__ import annotations

# pyright: reportUnknownParameterType=false, reportMissingParameterType=false, reportExplicitAny=false
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.money import fmt_amount
from app.models import (
    AuditLog,
    Contract,
    FulfillmentType,
    JSONValue,
    POContractLink,
    POItem,
    POStatus,
    PRFulfillmentLink,
    PRItem,
    PRStatus,
    PurchaseOrder,
    PurchaseRequisition,
    SKUPriceRecord,
    Supplier,
    User,
    UserRole,
)
from app.schemas import PRCreateIn, PRDecisionIn, PRUpdateIn
from app.services import approval as approval_svc

logger = logging.getLogger("mica.purchase")


def _as_decimal(v: Decimal | int | float | str) -> Decimal:
    return v if isinstance(v, Decimal) else Decimal(str(v))


def _compute_line_amount(qty: Decimal, unit_price: Decimal) -> Decimal:
    return (_as_decimal(qty) * _as_decimal(unit_price)).quantize(Decimal("0.0001"))


async def _next_pr_number(db: AsyncSession) -> str:
    year = datetime.now(UTC).year
    prefix = f"PR-{year}-"
    max_suffix = (
        await db.execute(
            select(func.max(PurchaseRequisition.pr_number)).where(
                PurchaseRequisition.pr_number.startswith(prefix)
            )
        )
    ).scalar_one_or_none()
    n = _next_seq_from_max(max_suffix, prefix)
    return f"{prefix}{n:04d}"


async def _next_rfq_number(db: AsyncSession) -> str:
    from app.models import RFQ

    year = datetime.now(UTC).year
    prefix = f"RFQ-{year}-"
    max_suffix = (
        await db.execute(select(func.max(RFQ.rfq_number)).where(RFQ.rfq_number.startswith(prefix)))
    ).scalar_one_or_none()
    n = _next_seq_from_max(max_suffix, prefix)
    return f"{prefix}{n:04d}"


async def _next_po_number(db: AsyncSession) -> str:
    year = datetime.now(UTC).year
    prefix = f"PO-{year}-"
    max_suffix = (
        await db.execute(
            select(func.max(PurchaseOrder.po_number)).where(
                PurchaseOrder.po_number.startswith(prefix)
            )
        )
    ).scalar_one_or_none()
    n = _next_seq_from_max(max_suffix, prefix)
    return f"{prefix}{n:04d}"


def _next_seq_from_max(max_value: str | None, prefix: str) -> int:
    if not max_value:
        return 1
    suffix = max_value[len(prefix) :]
    try:
        return int(suffix) + 1
    except ValueError:
        return 1


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

    proxy_roles = {
        UserRole.ADMIN.value,
        UserRole.PROCUREMENT_MGR.value,
        UserRole.IT_BUYER.value,
    }
    requester: User = actor
    if payload.requester_id is not None and payload.requester_id != actor.id:
        if actor.role not in proxy_roles:
            raise HTTPException(403, "pr.proxy_not_allowed")
        target = await db.get(User, payload.requester_id)
        if target is None or not target.is_active:
            raise HTTPException(404, "pr.requester_not_found")
        requester = target

    pr = PurchaseRequisition(
        pr_number=pr_number,
        title=payload.title,
        business_reason=payload.business_reason,
        status=PRStatus.DRAFT.value,
        requester_id=requester.id,
        company_id=payload.company_id or requester.company_id,
        department_id=payload.department_id or requester.department_id,
        cost_center_id=payload.cost_center_id,
        expense_type_id=payload.expense_type_id,
        procurement_category_id=payload.procurement_category_id,
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
    audit_meta: dict[str, JSONValue] = {"pr_number": pr.pr_number}
    if requester.id != actor.id:
        audit_meta["proxy_for"] = str(requester.id)
        audit_meta["proxy_for_name"] = requester.display_name
    await _audit(
        db,
        actor,
        "pr.created",
        "purchase_requisition",
        str(pr.id),
        metadata=audit_meta,
    )
    await db.commit()
    await db.refresh(pr)

    try:
        from app.db import AsyncSessionLocal
        from app.models import NotificationCategory
        from app.services.notifications import create_notification
        from app.services.system_params import notification_enabled

        async with AsyncSessionLocal() as notif_db:
            if await notification_enabled(notif_db, "pr_created"):
                notif_pr = await _load_pr(notif_db, pr.id)
                if notif_pr is None:
                    raise LookupError(f"PR not found for notification: {pr.id}")
                recipients: set[str] = {str(actor.id)}
                if notif_pr.requester_id:
                    recipients.add(str(notif_pr.requester_id))
                if notif_pr.department_id:
                    dept_managers = (
                        (
                            await notif_db.execute(
                                select(User.id).where(
                                    User.department_id == notif_pr.department_id,
                                    User.role == UserRole.DEPT_MANAGER.value,
                                    User.is_active.is_(True),
                                )
                            )
                        )
                        .scalars()
                        .all()
                    )
                    recipients.update(str(uid) for uid in dept_managers)

                from uuid import UUID as _UUID

                for uid_str in recipients:
                    await create_notification(
                        notif_db,
                        user_id=_UUID(uid_str),
                        category=NotificationCategory.SYSTEM,
                        title=f"PR {notif_pr.pr_number} created",
                        body=(
                            f"**PR**: {notif_pr.pr_number}\n"
                            f"**Title**: {notif_pr.title}\n"
                            f"**Amount**: {fmt_amount(notif_pr.total_amount, notif_pr.currency)}\n"
                            f"**Required by**: {notif_pr.required_date}\n"
                            f"**Items**: {len(notif_pr.items)} line(s)\n"
                            f"**Created by**: {actor.display_name}"
                        ),
                        link_url=f"/purchase-requisitions/{notif_pr.id}",
                        biz_type="pr",
                        biz_id=notif_pr.id,
                    )
                await notif_db.commit()
    except Exception:
        logger.warning("Failed to send pr_created notification for pr=%s", pr.id, exc_info=True)

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
    if pr.status in (PRStatus.DRAFT.value, PRStatus.RETURNED.value):
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
    if payload.company_id is not None:
        pr.company_id = payload.company_id
    if payload.cost_center_id is not None:
        pr.cost_center_id = payload.cost_center_id
    if payload.expense_type_id is not None:
        pr.expense_type_id = payload.expense_type_id
    if payload.procurement_category_id is not None:
        pr.procurement_category_id = payload.procurement_category_id
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

    try:
        from app.db import AsyncSessionLocal
        from app.models import NotificationCategory
        from app.services.notifications import create_notification
        from app.services.system_params import notification_enabled

        async with AsyncSessionLocal() as notif_db:
            if await notification_enabled(notif_db, "pr_updated"):
                notif_pr = await _load_pr(notif_db, pr.id)
                if notif_pr is None:
                    raise LookupError(f"PR not found for notification: {pr.id}")
                recipients = {actor.id, notif_pr.requester_id}
                if notif_pr.department_id:
                    dept_managers = (
                        (
                            await notif_db.execute(
                                select(User.id).where(
                                    User.department_id == notif_pr.department_id,
                                    User.role == UserRole.DEPT_MANAGER.value,
                                    User.is_active.is_(True),
                                )
                            )
                        )
                        .scalars()
                        .all()
                    )
                    recipients.update(dept_managers)
                admin_rows = (
                    (
                        await notif_db.execute(
                            select(User.id).where(
                                User.role.in_(
                                    [UserRole.ADMIN.value, UserRole.PROCUREMENT_MGR.value]
                                ),
                                User.is_active.is_(True),
                            )
                        )
                    )
                    .scalars()
                    .all()
                )
                recipients.update(admin_rows)
                for uid in recipients:
                    await create_notification(
                        notif_db,
                        user_id=uid,
                        category=NotificationCategory.SYSTEM,
                        title=f"PR {notif_pr.pr_number} updated",
                        body=(
                            f"**PR**: {notif_pr.pr_number}\n"
                            f"**Title**: {notif_pr.title}\n"
                            f"**Amount**: {fmt_amount(notif_pr.total_amount, notif_pr.currency)}\n"
                            f"**Status**: {notif_pr.status}\n"
                            f"**Updated by**: {actor.display_name}"
                        ),
                        link_url=f"/purchase-requisitions/{notif_pr.id}",
                        biz_type="pr",
                        biz_id=notif_pr.id,
                    )
                await notif_db.commit()
    except Exception:
        logger.warning("Failed to send pr_updated notification for pr=%s", pr.id, exc_info=True)

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
    if pr.status not in (PRStatus.DRAFT.value, PRStatus.RETURNED.value):
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


async def _build_supplier_groups(pr: PurchaseRequisition) -> dict[UUID, list[PRItem]]:
    missing = [i for i in pr.items if not i.supplier_id]
    if missing:
        raise HTTPException(422, "pr.items_missing_supplier")
    groups: dict[UUID, list[PRItem]] = {}
    for item in pr.items:
        groups.setdefault(item.supplier_id, []).append(item)
    return groups


async def preview_pr_conversion(db: AsyncSession, actor: User, pr_id: UUID) -> list[dict]:
    pr = await _load_pr(db, pr_id)
    if pr is None:
        raise HTTPException(404, "pr.not_found")
    if pr.status != PRStatus.APPROVED.value:
        raise HTTPException(409, "pr.must_be_approved_to_convert")
    if not pr.items:
        raise HTTPException(422, "pr.no_items")

    groups = await _build_supplier_groups(pr)

    supplier_rows = (
        (await db.execute(select(Supplier).where(Supplier.id.in_(list(groups.keys())))))
        .scalars()
        .all()
    )
    supplier_by_id = {s.id: s for s in supplier_rows}

    out: list[dict] = []
    for supplier_id, items in groups.items():
        supplier = supplier_by_id.get(supplier_id)
        subtotal = sum((Decimal(str(i.amount or 0)) for i in items), Decimal("0"))
        out.append(
            {
                "supplier_id": supplier_id,
                "supplier_name": supplier.name if supplier else None,
                "supplier_code": supplier.code if supplier else None,
                "item_count": len(items),
                "subtotal": subtotal,
                "items": [
                    {
                        "pr_item_id": i.id,
                        "line_no": i.line_no,
                        "item_name": i.item_name,
                        "qty": i.qty,
                        "uom": i.uom,
                        "unit_price": i.unit_price,
                        "amount": i.amount,
                    }
                    for i in items
                ],
            }
        )

    out.sort(key=lambda g: (g["supplier_name"] or "", str(g["supplier_id"])))
    return out


async def _compute_pr_status_after_link_change(
    db: AsyncSession, pr: PurchaseRequisition
) -> str:
    all_fulfilling_types = (
        FulfillmentType.EQUIVALENT.value,
        FulfillmentType.DOWNGRADED.value,
        FulfillmentType.SUBSTITUTE.value,
    )
    fulfilled_qty_by_pr_item: dict[UUID, Decimal] = {}
    pr_item_ids = [i.id for i in pr.items]
    if pr_item_ids:
        rows = (
            await db.execute(
                select(
                    PRFulfillmentLink.pr_item_id,
                    func.coalesce(func.sum(PRFulfillmentLink.qty_contribution), 0),
                )
                .where(
                    PRFulfillmentLink.pr_item_id.in_(pr_item_ids),
                    PRFulfillmentLink.fulfillment_type.in_(all_fulfilling_types),
                )
                .group_by(PRFulfillmentLink.pr_item_id)
            )
        ).all()
        fulfilled_qty_by_pr_item = {row[0]: Decimal(str(row[1])) for row in rows}

    total = len(pr.items)
    fully_fulfilled = 0
    has_any_fulfillment = False
    for pri in pr.items:
        filled = fulfilled_qty_by_pr_item.get(pri.id, Decimal("0"))
        if filled > 0:
            has_any_fulfillment = True
        if filled >= Decimal(str(pri.qty)):
            fully_fulfilled += 1

    if not has_any_fulfillment:
        if pr.status in (
            PRStatus.PARTIALLY_CONVERTED.value,
            PRStatus.CONVERTED.value,
        ):
            return PRStatus.APPROVED.value
        return pr.status
    if fully_fulfilled < total:
        return PRStatus.PARTIALLY_CONVERTED.value
    return PRStatus.CONVERTED.value


async def convert_pr_to_po(db: AsyncSession, actor: User, pr_id: UUID) -> list[PurchaseOrder]:
    pr = await _load_pr(db, pr_id)
    if pr is None:
        raise HTTPException(404, "pr.not_found")
    if pr.status not in (
        PRStatus.APPROVED.value,
        PRStatus.PARTIALLY_CONVERTED.value,
        PRStatus.CONVERTED.value,
    ):
        raise HTTPException(409, "pr.must_be_approved_to_convert")
    if not pr.items:
        raise HTTPException(422, "pr.no_items")

    unconverted = await _unconverted_pr_items(db, pr)
    if not unconverted:
        raise HTTPException(409, "pr.already_fully_converted")

    return await _create_pos_for_pr_items(db, actor, pr, unconverted)


async def convert_pr_to_po_partial(
    db: AsyncSession, actor: User, pr_id: UUID, pr_item_ids: list[UUID]
) -> list[PurchaseOrder]:
    if not pr_item_ids:
        raise HTTPException(422, "pr.partial_no_items")

    pr = await _load_pr(db, pr_id)
    if pr is None:
        raise HTTPException(404, "pr.not_found")
    if pr.status not in (
        PRStatus.APPROVED.value,
        PRStatus.PARTIALLY_CONVERTED.value,
        PRStatus.CONVERTED.value,
    ):
        raise HTTPException(409, "pr.must_be_approved_to_convert")

    requested_ids = set(pr_item_ids)
    pr_items_by_id = {i.id: i for i in pr.items}
    unknown = requested_ids - pr_items_by_id.keys()
    if unknown:
        raise HTTPException(422, "pr.partial_unknown_item")

    existing_link_rows = (
        await db.execute(
            select(PRFulfillmentLink.pr_item_id).where(
                PRFulfillmentLink.pr_item_id.in_(requested_ids)
            )
        )
    ).all()
    if existing_link_rows:
        raise HTTPException(409, "pr.partial_already_converted")

    selected = [pr_items_by_id[pid] for pid in requested_ids]
    return await _create_pos_for_pr_items(db, actor, pr, selected)


@dataclass(frozen=True)
class PRConvertSpec:
    pr_item_id: UUID
    qty: Decimal
    fulfillment_type: str
    deviation_note: str | None = None
    unit_price: Decimal | None = None
    supplier_id: UUID | None = None
    item_id: UUID | None = None
    item_name: str | None = None
    specification: str | None = None
    uom: str | None = None


async def convert_pr_to_po_with_specs(
    db: AsyncSession,
    actor: User,
    pr_id: UUID,
    specs: list[PRConvertSpec],
) -> list[PurchaseOrder]:
    if not specs:
        raise HTTPException(422, "pr.partial_no_items")

    pr = await _load_pr(db, pr_id)
    if pr is None:
        raise HTTPException(404, "pr.not_found")
    if pr.status not in (
        PRStatus.APPROVED.value,
        PRStatus.PARTIALLY_CONVERTED.value,
        PRStatus.CONVERTED.value,
    ):
        raise HTTPException(409, "pr.must_be_approved_to_convert")

    pr_items_by_id = {i.id: i for i in pr.items}
    pr_item_ids_in_specs = {s.pr_item_id for s in specs}
    unknown = pr_item_ids_in_specs - pr_items_by_id.keys()
    if unknown:
        raise HTTPException(422, "pr.partial_unknown_item")

    for spec in specs:
        if spec.qty <= 0:
            raise HTTPException(422, "fulfillment.qty_must_be_positive")
        if spec.fulfillment_type not in (
            FulfillmentType.EQUIVALENT.value,
            FulfillmentType.DOWNGRADED.value,
            FulfillmentType.SUBSTITUTE.value,
            FulfillmentType.SUPPLEMENTARY.value,
        ):
            raise HTTPException(422, "fulfillment.invalid_type")

    existing_links_by_pr_item: dict[UUID, Decimal] = {}
    if pr_item_ids_in_specs:
        rows = (
            await db.execute(
                select(
                    PRFulfillmentLink.pr_item_id,
                    func.coalesce(func.sum(PRFulfillmentLink.qty_contribution), 0),
                )
                .where(
                    PRFulfillmentLink.pr_item_id.in_(pr_item_ids_in_specs),
                    PRFulfillmentLink.fulfillment_type.in_(_FULFILLING_TYPES),
                )
                .group_by(PRFulfillmentLink.pr_item_id)
            )
        ).all()
        existing_links_by_pr_item = {
            row[0]: Decimal(str(row[1])) for row in rows
        }

    requested_qty_per_pr_item: dict[UUID, Decimal] = {}
    for spec in specs:
        if spec.fulfillment_type == FulfillmentType.SUPPLEMENTARY.value:
            continue
        requested_qty_per_pr_item[spec.pr_item_id] = (
            requested_qty_per_pr_item.get(spec.pr_item_id, Decimal("0"))
            + Decimal(str(spec.qty))
        )

    for pr_item_id, requested_qty in requested_qty_per_pr_item.items():
        pr_item = pr_items_by_id[pr_item_id]
        already = existing_links_by_pr_item.get(pr_item_id, Decimal("0"))
        projected = already + requested_qty
        soft_limit = Decimal(str(pr_item.qty)) * Decimal("1.5")
        if projected > soft_limit:
            raise HTTPException(422, "fulfillment.qty_exceeds_soft_limit")

    return await _create_pos_for_specs(db, actor, pr, specs, pr_items_by_id)


async def _create_pos_for_specs(
    db: AsyncSession,
    actor: User,
    pr: PurchaseRequisition,
    specs: list[PRConvertSpec],
    pr_items_by_id: dict[UUID, PRItem],
) -> list[PurchaseOrder]:
    def _resolve_supplier(spec: PRConvertSpec) -> UUID | None:
        if spec.supplier_id is not None:
            return spec.supplier_id
        return pr_items_by_id[spec.pr_item_id].supplier_id

    missing_supplier = [s for s in specs if _resolve_supplier(s) is None]
    if missing_supplier:
        raise HTTPException(422, "pr.items_missing_supplier")

    groups: dict[UUID, list[PRConvertSpec]] = {}
    for spec in specs:
        supplier_id = _resolve_supplier(spec)
        assert supplier_id is not None
        groups.setdefault(supplier_id, []).append(spec)

    created_pos: list[PurchaseOrder] = []
    for supplier_id, group_specs in groups.items():
        po_number = await _next_po_number(db)
        subtotal = Decimal("0")
        for spec in group_specs:
            pr_item = pr_items_by_id[spec.pr_item_id]
            spec_unit_price = (
                Decimal(str(spec.unit_price))
                if spec.unit_price is not None
                else Decimal(str(pr_item.unit_price or 0))
            )
            subtotal += Decimal(str(spec.qty)) * spec_unit_price

        po = PurchaseOrder(
            po_number=po_number,
            pr_id=pr.id,
            pr_title=pr.title,
            supplier_id=supplier_id,
            company_id=pr.company_id,
            status=POStatus.CONFIRMED.value,
            currency=pr.currency,
            total_amount=subtotal,
            source_type="manual",
            created_by_id=actor.id,
        )
        db.add(po)
        await db.flush()

        line_no = 0
        for spec in group_specs:
            line_no += 1
            pr_item = pr_items_by_id[spec.pr_item_id]
            spec_unit_price = (
                Decimal(str(spec.unit_price))
                if spec.unit_price is not None
                else Decimal(str(pr_item.unit_price or 0))
            )
            line_qty = Decimal(str(spec.qty))
            amount = line_qty * spec_unit_price

            resolved_item_id = spec.item_id if spec.item_id is not None else pr_item.item_id
            resolved_item_name = (
                spec.item_name.strip()
                if spec.item_name and spec.item_name.strip()
                else pr_item.item_name
            )
            resolved_specification = (
                spec.specification
                if spec.specification is not None
                else pr_item.specification
            )
            resolved_uom = (
                spec.uom.strip()
                if spec.uom and spec.uom.strip()
                else pr_item.uom
            )

            po_item = POItem(
                po_id=po.id,
                pr_item_id=pr_item.id,
                line_no=line_no,
                item_id=resolved_item_id,
                item_name=resolved_item_name,
                specification=resolved_specification,
                qty=line_qty,
                uom=resolved_uom,
                unit_price=spec_unit_price,
                amount=amount,
            )
            db.add(po_item)
            await db.flush()

            db.add(
                PRFulfillmentLink(
                    pr_item_id=pr_item.id,
                    po_item_id=po_item.id,
                    qty_contribution=line_qty,
                    fulfillment_type=spec.fulfillment_type,
                    deviation_note=spec.deviation_note,
                    created_by_id=actor.id,
                )
            )

            if resolved_item_id and spec_unit_price > 0:
                db.add(
                    SKUPriceRecord(
                        item_id=resolved_item_id,
                        supplier_id=supplier_id,
                        price=spec_unit_price,
                        currency=pr.currency or "CNY",
                        quotation_date=datetime.now(UTC).date(),
                        source_type="actual_po",
                        source_ref=po_number,
                        entered_by_id=actor.id,
                    )
                )

        await _audit(
            db,
            actor,
            "po.created_from_pr",
            "purchase_order",
            str(po.id),
            metadata={
                "pr_id": str(pr.id),
                "pr_number": pr.pr_number,
                "po_number": po.po_number,
                "supplier_id": str(supplier_id),
                "split_count": len(groups),
                "lines_in_this_po": len(group_specs),
                "with_specs": True,
            },
        )
        created_pos.append(po)

    pr.status = await _compute_pr_status_after_link_change(db, pr)
    await db.commit()

    refreshed: list[PurchaseOrder] = []
    for po in created_pos:
        loaded = await _load_po(db, po.id)
        if loaded is None:
            raise HTTPException(404, "po.not_found")
        refreshed.append(loaded)
    refreshed.sort(key=lambda p: p.po_number)
    return refreshed


async def _unconverted_pr_items(
    db: AsyncSession, pr: PurchaseRequisition
) -> list[PRItem]:
    if not pr.items:
        return []
    pr_item_ids = [i.id for i in pr.items]
    rows = (
        await db.execute(
            select(PRFulfillmentLink.pr_item_id).where(
                PRFulfillmentLink.pr_item_id.in_(pr_item_ids)
            )
        )
    ).all()
    converted_ids = {row[0] for row in rows}
    return [i for i in pr.items if i.id not in converted_ids]


async def _create_pos_for_pr_items(
    db: AsyncSession,
    actor: User,
    pr: PurchaseRequisition,
    pr_items: list[PRItem],
) -> list[PurchaseOrder]:
    if not pr_items:
        raise HTTPException(422, "pr.no_items")

    missing = [i for i in pr_items if not i.supplier_id]
    if missing:
        raise HTTPException(422, "pr.items_missing_supplier")

    groups: dict[UUID, list[PRItem]] = {}
    for item in pr_items:
        groups.setdefault(item.supplier_id, []).append(item)

    created_pos: list[PurchaseOrder] = []
    for supplier_id, items in groups.items():
        po_number = await _next_po_number(db)
        subtotal = sum((Decimal(str(i.amount or 0)) for i in items), Decimal("0"))
        po = PurchaseOrder(
            po_number=po_number,
            pr_id=pr.id,
            pr_title=pr.title,
            supplier_id=supplier_id,
            company_id=pr.company_id,
            status=POStatus.CONFIRMED.value,
            currency=pr.currency,
            total_amount=subtotal,
            source_type="manual",
            created_by_id=actor.id,
        )
        db.add(po)
        await db.flush()

        for i, pr_item in enumerate(items, start=1):
            po_item = POItem(
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
            db.add(po_item)
            await db.flush()

            db.add(
                PRFulfillmentLink(
                    pr_item_id=pr_item.id,
                    po_item_id=po_item.id,
                    qty_contribution=pr_item.qty,
                    fulfillment_type=FulfillmentType.EQUIVALENT.value,
                    created_by_id=actor.id,
                )
            )

            if pr_item.item_id and pr_item.unit_price and pr_item.unit_price > 0:
                db.add(
                    SKUPriceRecord(
                        item_id=pr_item.item_id,
                        supplier_id=supplier_id,
                        price=pr_item.unit_price,
                        currency=pr.currency or "CNY",
                        quotation_date=datetime.now(UTC).date(),
                        source_type="actual_po",
                        source_ref=po_number,
                        entered_by_id=actor.id,
                    )
                )

        await _audit(
            db,
            actor,
            "po.created_from_pr",
            "purchase_order",
            str(po.id),
            metadata={
                "pr_id": str(pr.id),
                "pr_number": pr.pr_number,
                "po_number": po.po_number,
                "supplier_id": str(supplier_id),
                "split_count": len(groups),
                "pr_items_in_this_po": len(items),
            },
        )
        created_pos.append(po)

    pr.status = await _compute_pr_status_after_link_change(db, pr)
    await db.commit()

    refreshed: list[PurchaseOrder] = []
    for po in created_pos:
        loaded = await _load_po(db, po.id)
        if loaded is None:
            raise HTTPException(404, "po.not_found")
        refreshed.append(loaded)
    refreshed.sort(key=lambda p: p.po_number)

    try:
        from app.db import AsyncSessionLocal
        from app.models import NotificationCategory
        from app.services.notifications import create_notification
        from app.services.system_params import notification_enabled

        async with AsyncSessionLocal() as notif_db:
            if await notification_enabled(notif_db, "po_created"):
                notif_pr = await _load_pr(notif_db, pr.id)
                if notif_pr is None:
                    raise LookupError(f"PR not found for notification: {pr.id}")
                notif_pos: list[PurchaseOrder] = []
                for po in refreshed:
                    loaded = await _load_po(notif_db, po.id)
                    if loaded is not None:
                        notif_pos.append(loaded)

                supplier_ids = {po.supplier_id for po in notif_pos}
                supplier_rows = (
                    (await notif_db.execute(select(Supplier).where(Supplier.id.in_(supplier_ids))))
                    .scalars()
                    .all()
                )
                supplier_names = {s.id: s.name for s in supplier_rows}

                recipients = {actor.id}
                if notif_pr.requester_id:
                    recipients.add(notif_pr.requester_id)
                admin_rows = (
                    (
                        await notif_db.execute(
                            select(User.id).where(
                                User.role.in_(
                                    [
                                        UserRole.ADMIN.value,
                                        UserRole.PROCUREMENT_MGR.value,
                                        UserRole.FINANCE_AUDITOR.value,
                                    ]
                                ),
                                User.is_active.is_(True),
                            )
                        )
                    )
                    .scalars()
                    .all()
                )
                recipients.update(admin_rows)

                for po in notif_pos:
                    supplier_name = supplier_names.get(po.supplier_id, "Unknown")
                    items_count = len(po.items)
                    for uid in recipients:
                        await create_notification(
                            notif_db,
                            user_id=uid,
                            category=NotificationCategory.PO_CREATED,
                            title=f"PO {po.po_number} created",
                            body=(
                                f"**PO**: {po.po_number}\n"
                                f"**PR**: {po.pr_title or '—'}\n"
                                f"**Source PR**: {notif_pr.pr_number} — {notif_pr.title}\n"
                                f"**Supplier**: {supplier_name}\n"
                                f"**Amount**: {fmt_amount(po.total_amount, po.currency)}\n"
                                f"**Items**: {items_count} line(s)\n"
                                f"**Created by**: {actor.display_name}"
                            ),
                            link_url=f"/purchase-orders/{po.id}",
                            biz_type="po",
                            biz_id=po.id,
                        )
                await notif_db.commit()
    except Exception:
        logger.warning("Failed to send po_created notification for pr=%s", pr.id, exc_info=True)

    return refreshed


_FULFILLING_TYPES: tuple[str, ...] = (
    FulfillmentType.EQUIVALENT.value,
    FulfillmentType.DOWNGRADED.value,
    FulfillmentType.SUBSTITUTE.value,
)

_DEVIATION_TYPES: tuple[str, ...] = (
    FulfillmentType.DOWNGRADED.value,
    FulfillmentType.SUBSTITUTE.value,
)


async def _maybe_trigger_deviation_approval(
    db: AsyncSession,
    actor: User,
    link: PRFulfillmentLink,
) -> None:
    if link.fulfillment_type not in _DEVIATION_TYPES:
        return

    from app.services.system_params import system_params

    threshold = await system_params.get_int(
        db, "fulfillment.deviation_approval_threshold"
    )
    if threshold is None or threshold <= 0:
        return

    po_item = await db.get(POItem, link.po_item_id)
    if po_item is None:
        return
    deviation_amount = (
        Decimal(str(link.qty_contribution)) * Decimal(str(po_item.unit_price))
    )
    if deviation_amount < Decimal(str(threshold)):
        return

    pr_item = link.pr_item
    pr_number = pr_item.pr.pr_number if pr_item.pr else "unknown"
    title = f"Deviation review: {link.fulfillment_type} on {pr_number}/L{pr_item.line_no}"
    try:
        await approval_svc.create_instance_for_pr(
            db,
            actor,
            biz_type="fulfillment_deviation",
            biz_id=link.id,
            biz_number=str(link.id)[:8],
            title=title,
            amount=deviation_amount,
        )
    except Exception:
        logger.warning(
            "Failed to create deviation approval for link %s", link.id, exc_info=True
        )


async def _load_link(db: AsyncSession, link_id: UUID) -> PRFulfillmentLink | None:
    return (
        await db.execute(
            select(PRFulfillmentLink)
            .where(PRFulfillmentLink.id == link_id)
            .options(
                selectinload(PRFulfillmentLink.pr_item).selectinload(PRItem.pr),
                selectinload(PRFulfillmentLink.po_item),
            )
        )
    ).scalar_one_or_none()


async def _validate_fulfillment_type(value: str) -> str:
    try:
        return FulfillmentType(value).value
    except ValueError as exc:
        raise HTTPException(422, "fulfillment.invalid_type") from exc


async def _ensure_link_qty_under_limit(
    db: AsyncSession,
    pr_item: PRItem,
    additional_qty: Decimal,
    excluding_link_id: UUID | None = None,
) -> None:
    stmt = select(func.coalesce(func.sum(PRFulfillmentLink.qty_contribution), 0)).where(
        PRFulfillmentLink.pr_item_id == pr_item.id,
        PRFulfillmentLink.fulfillment_type.in_(_FULFILLING_TYPES),
    )
    if excluding_link_id is not None:
        stmt = stmt.where(PRFulfillmentLink.id != excluding_link_id)
    current_total = (await db.execute(stmt)).scalar() or Decimal("0")
    projected = Decimal(str(current_total)) + Decimal(str(additional_qty))
    soft_limit = Decimal(str(pr_item.qty)) * Decimal("1.5")
    if projected > soft_limit:
        raise HTTPException(422, "fulfillment.qty_exceeds_soft_limit")


async def create_fulfillment_link(
    db: AsyncSession,
    actor: User,
    *,
    po_item_id: UUID,
    pr_item_id: UUID,
    fulfillment_type: str,
    qty_contribution: Decimal,
    deviation_note: str | None = None,
) -> PRFulfillmentLink:
    if qty_contribution <= 0:
        raise HTTPException(422, "fulfillment.qty_must_be_positive")

    fulfillment_type = await _validate_fulfillment_type(fulfillment_type)

    po_item = await db.get(POItem, po_item_id)
    if po_item is None:
        raise HTTPException(404, "po_item.not_found")

    pr_item = (
        await db.execute(
            select(PRItem)
            .where(PRItem.id == pr_item_id)
            .options(selectinload(PRItem.pr))
        )
    ).scalar_one_or_none()
    if pr_item is None:
        raise HTTPException(404, "pr_item.not_found")

    duplicate = (
        await db.execute(
            select(PRFulfillmentLink.id).where(
                PRFulfillmentLink.po_item_id == po_item_id,
                PRFulfillmentLink.pr_item_id == pr_item_id,
            )
        )
    ).scalar_one_or_none()
    if duplicate is not None:
        raise HTTPException(409, "fulfillment.link_already_exists")

    if fulfillment_type in _FULFILLING_TYPES:
        await _ensure_link_qty_under_limit(db, pr_item, Decimal(str(qty_contribution)))

    link = PRFulfillmentLink(
        pr_item_id=pr_item_id,
        po_item_id=po_item_id,
        qty_contribution=qty_contribution,
        fulfillment_type=fulfillment_type,
        deviation_note=deviation_note,
        created_by_id=actor.id,
    )
    db.add(link)
    await db.flush()

    pr = await _load_pr(db, pr_item.pr_id)
    if pr is not None:
        pr.status = await _compute_pr_status_after_link_change(db, pr)

    await _audit(
        db,
        actor,
        "fulfillment_link.created",
        "pr_fulfillment_link",
        str(link.id),
        metadata={
            "pr_item_id": str(pr_item_id),
            "po_item_id": str(po_item_id),
            "fulfillment_type": fulfillment_type,
            "qty_contribution": str(qty_contribution),
            "deviation_note": deviation_note,
        },
    )

    refreshed_link = await _load_link(db, link.id)
    if refreshed_link is not None:
        await _maybe_trigger_deviation_approval(db, actor, refreshed_link)

    await db.commit()

    refreshed = await _load_link(db, link.id)
    if refreshed is None:
        raise HTTPException(404, "fulfillment.link_not_found")
    return refreshed


async def update_fulfillment_link(
    db: AsyncSession,
    actor: User,
    link_id: UUID,
    *,
    fulfillment_type: str | None = None,
    qty_contribution: Decimal | None = None,
    deviation_note: str | None = None,
) -> PRFulfillmentLink:
    link = await _load_link(db, link_id)
    if link is None:
        raise HTTPException(404, "fulfillment.link_not_found")

    new_type = link.fulfillment_type
    if fulfillment_type is not None:
        new_type = await _validate_fulfillment_type(fulfillment_type)

    new_qty = Decimal(str(link.qty_contribution))
    if qty_contribution is not None:
        if qty_contribution <= 0:
            raise HTTPException(422, "fulfillment.qty_must_be_positive")
        new_qty = Decimal(str(qty_contribution))

    if new_type in _FULFILLING_TYPES:
        await _ensure_link_qty_under_limit(
            db, link.pr_item, new_qty, excluding_link_id=link.id
        )

    link.fulfillment_type = new_type
    link.qty_contribution = new_qty
    if deviation_note is not None:
        link.deviation_note = deviation_note

    await db.flush()

    pr = await _load_pr(db, link.pr_item.pr_id)
    if pr is not None:
        pr.status = await _compute_pr_status_after_link_change(db, pr)

    await _audit(
        db,
        actor,
        "fulfillment_link.updated",
        "pr_fulfillment_link",
        str(link.id),
        metadata={
            "fulfillment_type": new_type,
            "qty_contribution": str(new_qty),
            "deviation_note": link.deviation_note,
        },
    )

    if new_type in _DEVIATION_TYPES:
        await _maybe_trigger_deviation_approval(db, actor, link)

    await db.commit()

    refreshed = await _load_link(db, link.id)
    if refreshed is None:
        raise HTTPException(404, "fulfillment.link_not_found")
    return refreshed


async def delete_fulfillment_link(
    db: AsyncSession, actor: User, link_id: UUID
) -> None:
    link = await _load_link(db, link_id)
    if link is None:
        raise HTTPException(404, "fulfillment.link_not_found")

    pr_id = link.pr_item.pr_id
    await db.delete(link)
    await db.flush()

    pr = await _load_pr(db, pr_id)
    if pr is not None:
        pr.status = await _compute_pr_status_after_link_change(db, pr)

    await _audit(
        db,
        actor,
        "fulfillment_link.deleted",
        "pr_fulfillment_link",
        str(link_id),
        metadata={"pr_id": str(pr_id)},
    )
    await db.commit()


async def add_supplementary_po_item(
    db: AsyncSession,
    actor: User,
    *,
    po_id: UUID,
    item_name: str,
    qty: Decimal,
    unit_price: Decimal,
    uom: str = "EA",
    specification: str | None = None,
    item_id: UUID | None = None,
    supplementary_for_pr_item_id: UUID | None = None,
    deviation_note: str | None = None,
) -> POItem:
    if qty <= 0:
        raise HTTPException(422, "po_item.qty_must_be_positive")
    if unit_price < 0:
        raise HTTPException(422, "po_item.unit_price_negative")

    po = await _load_po(db, po_id)
    if po is None:
        raise HTTPException(404, "po.not_found")

    pr_item: PRItem | None = None
    if supplementary_for_pr_item_id is not None:
        pr_item = (
            await db.execute(
                select(PRItem).where(PRItem.id == supplementary_for_pr_item_id)
            )
        ).scalar_one_or_none()
        if pr_item is None:
            raise HTTPException(404, "pr_item.not_found")
        if pr_item.pr_id != po.pr_id:
            raise HTTPException(422, "fulfillment.supplementary_pr_mismatch")

    next_line_no = (max((i.line_no for i in po.items), default=0)) + 1
    amount = _compute_line_amount(Decimal(str(qty)), Decimal(str(unit_price)))

    po_item = POItem(
        po_id=po.id,
        pr_item_id=None,
        line_no=next_line_no,
        item_id=item_id,
        item_name=item_name,
        specification=specification,
        qty=qty,
        uom=uom,
        unit_price=unit_price,
        amount=amount,
    )
    db.add(po_item)
    await db.flush()

    if pr_item is not None:
        db.add(
            PRFulfillmentLink(
                pr_item_id=pr_item.id,
                po_item_id=po_item.id,
                qty_contribution=qty,
                fulfillment_type=FulfillmentType.SUPPLEMENTARY.value,
                deviation_note=deviation_note,
                created_by_id=actor.id,
            )
        )
        await db.flush()

    po.total_amount = Decimal(str(po.total_amount)) + amount

    await _audit(
        db,
        actor,
        "po_item.supplementary_added",
        "po_item",
        str(po_item.id),
        metadata={
            "po_id": str(po.id),
            "supplementary_for_pr_item_id": (
                str(supplementary_for_pr_item_id)
                if supplementary_for_pr_item_id
                else None
            ),
            "qty": str(qty),
            "amount": str(amount),
        },
    )
    await db.commit()

    refreshed = (
        await db.execute(
            select(POItem)
            .where(POItem.id == po_item.id)
            .options(selectinload(POItem.fulfillment_links))
        )
    ).scalar_one_or_none()
    if refreshed is None:
        raise HTTPException(404, "po_item.not_found")
    return refreshed


async def add_supplementary_for_pr_item(
    db: AsyncSession,
    actor: User,
    *,
    pr_item_id: UUID,
    item_name: str,
    qty: Decimal,
    unit_price: Decimal,
    supplier_id: UUID,
    target_po_id: UUID | None = None,
    item_id: UUID | None = None,
    uom: str = "EA",
    specification: str | None = None,
    deviation_note: str | None = None,
) -> POItem:
    if qty <= 0:
        raise HTTPException(422, "po_item.qty_must_be_positive")
    if unit_price < 0:
        raise HTTPException(422, "po_item.unit_price_negative")
    if not item_name or not item_name.strip():
        raise HTTPException(422, "po_item.item_name_required")

    pr_item = (
        await db.execute(select(PRItem).where(PRItem.id == pr_item_id))
    ).scalar_one_or_none()
    if pr_item is None:
        raise HTTPException(404, "pr_item.not_found")

    pr = await _load_pr(db, pr_item.pr_id)
    if pr is None:
        raise HTTPException(404, "pr.not_found")
    if pr.status not in (
        PRStatus.APPROVED.value,
        PRStatus.PARTIALLY_CONVERTED.value,
        PRStatus.CONVERTED.value,
    ):
        raise HTTPException(409, "pr.must_be_approved_to_convert")

    target_po: PurchaseOrder | None = None
    if target_po_id is not None:
        target_po = await _load_po(db, target_po_id)
        if target_po is None:
            raise HTTPException(404, "po.not_found")
        if target_po.pr_id != pr.id:
            raise HTTPException(422, "fulfillment.supplementary_pr_mismatch")
        if target_po.supplier_id != supplier_id:
            raise HTTPException(422, "fulfillment.supplier_mismatch_with_po")

    amount = _compute_line_amount(Decimal(str(qty)), Decimal(str(unit_price)))

    if target_po is None:
        po_number = await _next_po_number(db)
        target_po = PurchaseOrder(
            po_number=po_number,
            pr_id=pr.id,
            pr_title=pr.title,
            supplier_id=supplier_id,
            company_id=pr.company_id,
            status=POStatus.CONFIRMED.value,
            currency=pr.currency,
            total_amount=amount,
            source_type="manual",
            created_by_id=actor.id,
        )
        db.add(target_po)
        await db.flush()
        next_line_no = 1
    else:
        next_line_no = (max((i.line_no for i in target_po.items), default=0)) + 1
        target_po.total_amount = Decimal(str(target_po.total_amount)) + amount

    po_item = POItem(
        po_id=target_po.id,
        pr_item_id=None,
        line_no=next_line_no,
        item_id=item_id,
        item_name=item_name.strip(),
        specification=specification,
        qty=qty,
        uom=uom,
        unit_price=unit_price,
        amount=amount,
    )
    db.add(po_item)
    await db.flush()

    db.add(
        PRFulfillmentLink(
            pr_item_id=pr_item.id,
            po_item_id=po_item.id,
            qty_contribution=qty,
            fulfillment_type=FulfillmentType.SUPPLEMENTARY.value,
            deviation_note=deviation_note,
            created_by_id=actor.id,
        )
    )
    await db.flush()

    if item_id and Decimal(str(unit_price)) > 0:
        db.add(
            SKUPriceRecord(
                item_id=item_id,
                supplier_id=supplier_id,
                price=unit_price,
                currency=pr.currency or "CNY",
                quotation_date=datetime.now(UTC).date(),
                source_type="actual_po",
                source_ref=target_po.po_number,
                entered_by_id=actor.id,
            )
        )

    pr_after = await _load_pr(db, pr.id)
    if pr_after is not None:
        pr_after.status = await _compute_pr_status_after_link_change(db, pr_after)

    await _audit(
        db,
        actor,
        "po_item.supplementary_added_for_pr_item",
        "po_item",
        str(po_item.id),
        metadata={
            "pr_id": str(pr.id),
            "pr_item_id": str(pr_item_id),
            "po_id": str(target_po.id),
            "po_number": target_po.po_number,
            "supplier_id": str(supplier_id),
            "qty": str(qty),
            "amount": str(amount),
            "opened_new_po": target_po_id is None,
        },
    )
    await db.commit()

    refreshed = (
        await db.execute(
            select(POItem)
            .where(POItem.id == po_item.id)
            .options(selectinload(POItem.fulfillment_links))
        )
    ).scalar_one_or_none()
    if refreshed is None:
        raise HTTPException(404, "po_item.not_found")
    return refreshed


async def update_po_item(
    db: AsyncSession,
    actor: User,
    po_item_id: UUID,
    *,
    qty: Decimal | None = None,
    unit_price: Decimal | None = None,
    item_name: str | None = None,
    specification: str | None = None,
    sync_link_qty: bool = True,
) -> POItem:
    po_item = (
        await db.execute(
            select(POItem)
            .where(POItem.id == po_item_id)
            .options(selectinload(POItem.fulfillment_links))
        )
    ).scalar_one_or_none()
    if po_item is None:
        raise HTTPException(404, "po_item.not_found")

    if qty is not None and qty <= 0:
        raise HTTPException(422, "po_item.qty_must_be_positive")
    if unit_price is not None and unit_price < 0:
        raise HTTPException(422, "po_item.unit_price_negative")
    if item_name is not None and not item_name.strip():
        raise HTTPException(422, "po_item.item_name_required")

    if qty is not None and Decimal(str(qty)) < Decimal(str(po_item.qty_received or 0)):
        raise HTTPException(409, "po_item.qty_below_received")

    from app.models import InvoiceLine

    if qty is not None or unit_price is not None:
        invoice_count = (
            await db.execute(
                select(func.count(InvoiceLine.id)).where(
                    InvoiceLine.po_item_id == po_item_id
                )
            )
        ).scalar_one()
        if invoice_count:
            raise HTTPException(409, "po_item.cannot_edit_has_invoices")

    old_qty = Decimal(str(po_item.qty))
    old_unit_price = Decimal(str(po_item.unit_price))
    old_amount = Decimal(str(po_item.amount))

    new_qty = old_qty if qty is None else Decimal(str(qty))
    new_unit_price = old_unit_price if unit_price is None else Decimal(str(unit_price))
    new_amount = _compute_line_amount(new_qty, new_unit_price)

    po_item.qty = new_qty
    po_item.unit_price = new_unit_price
    po_item.amount = new_amount
    if item_name is not None:
        po_item.item_name = item_name.strip()
    if specification is not None:
        po_item.specification = specification.strip() or None

    if sync_link_qty and qty is not None and qty != old_qty:
        for link in po_item.fulfillment_links:
            current_contribution = Decimal(str(link.qty_contribution))
            if current_contribution == old_qty:
                link.qty_contribution = new_qty
            elif current_contribution > new_qty:
                link.qty_contribution = new_qty

    po = await _load_po(db, po_item.po_id)
    if po is not None:
        delta = new_amount - old_amount
        po.total_amount = Decimal(str(po.total_amount)) + delta

    await db.flush()

    if po is not None:
        po_pr_id = po.pr_id
    else:
        po_pr_id = None

    if po_pr_id is not None:
        pr = await _load_pr(db, po_pr_id)
        if pr is not None:
            pr.status = await _compute_pr_status_after_link_change(db, pr)

    await _audit(
        db,
        actor,
        "po_item.updated",
        "po_item",
        str(po_item_id),
        metadata={
            "po_id": str(po_item.po_id),
            "old_qty": str(old_qty),
            "new_qty": str(new_qty),
            "old_unit_price": str(old_unit_price),
            "new_unit_price": str(new_unit_price),
        },
    )
    await db.commit()

    refreshed = (
        await db.execute(
            select(POItem)
            .where(POItem.id == po_item_id)
            .options(selectinload(POItem.fulfillment_links))
        )
    ).scalar_one_or_none()
    if refreshed is None:
        raise HTTPException(404, "po_item.not_found")
    return refreshed


async def delete_po_item(
    db: AsyncSession,
    actor: User,
    po_item_id: UUID,
) -> None:
    from app.models import InvoiceLine, ShipmentItem

    po_item = await db.get(POItem, po_item_id)
    if po_item is None:
        raise HTTPException(404, "po_item.not_found")

    shipment_count = (
        await db.execute(
            select(func.count(ShipmentItem.id)).where(
                ShipmentItem.po_item_id == po_item_id
            )
        )
    ).scalar_one()
    if shipment_count:
        raise HTTPException(409, "po_item.cannot_delete_has_shipments")

    invoice_count = (
        await db.execute(
            select(func.count(InvoiceLine.id)).where(
                InvoiceLine.po_item_id == po_item_id
            )
        )
    ).scalar_one()
    if invoice_count:
        raise HTTPException(409, "po_item.cannot_delete_has_invoices")

    po_id = po_item.po_id
    line_amount = Decimal(str(po_item.amount))

    await db.delete(po_item)
    await db.flush()

    po = await _load_po(db, po_id)
    if po is not None:
        po.total_amount = max(
            Decimal("0"), Decimal(str(po.total_amount)) - line_amount
        )

    if po is not None:
        pr = await _load_pr(db, po.pr_id)
        if pr is not None:
            pr.status = await _compute_pr_status_after_link_change(db, pr)

    await _audit(
        db,
        actor,
        "po_item.deleted",
        "po_item",
        str(po_item_id),
        metadata={
            "po_id": str(po_id),
            "amount": str(line_amount),
        },
    )
    await db.commit()


async def get_pr_item_fulfillment_breakdown(
    db: AsyncSession, pr_item_id: UUID
) -> dict[str, Decimal]:
    rows = (
        await db.execute(
            select(
                PRFulfillmentLink.fulfillment_type,
                func.coalesce(func.sum(PRFulfillmentLink.qty_contribution), 0),
            )
            .where(PRFulfillmentLink.pr_item_id == pr_item_id)
            .group_by(PRFulfillmentLink.fulfillment_type)
        )
    ).all()
    breakdown: dict[str, Decimal] = {t.value: Decimal("0") for t in FulfillmentType}
    for ftype, total in rows:
        breakdown[ftype] = Decimal(str(total))
    return breakdown


async def _load_pr(db: AsyncSession, pr_id: UUID) -> PurchaseRequisition | None:
    result = await db.execute(
        select(PurchaseRequisition)
        .where(PurchaseRequisition.id == pr_id)
        .options(
            selectinload(PurchaseRequisition.items).selectinload(PRItem.fulfillment_links),
            selectinload(PurchaseRequisition.requester),
            selectinload(PurchaseRequisition.company),
            selectinload(PurchaseRequisition.department),
            selectinload(PurchaseRequisition.cost_center),
            selectinload(PurchaseRequisition.collaborators),
        )
    )
    return result.scalar_one_or_none()


async def _load_po(db: AsyncSession, po_id: UUID) -> PurchaseOrder | None:
    result = await db.execute(
        select(PurchaseOrder)
        .where(PurchaseOrder.id == po_id)
        .options(selectinload(PurchaseOrder.items).selectinload(POItem.fulfillment_links))
    )
    return result.scalar_one_or_none()


async def list_prs_for_user(db: AsyncSession, actor: User) -> list[PurchaseRequisition]:
    from app.core.scoping import visible_pr_filter

    stmt = (
        select(PurchaseRequisition)
        .order_by(PurchaseRequisition.created_at.desc())
        .options(
            selectinload(PurchaseRequisition.requester),
            selectinload(PurchaseRequisition.company),
            selectinload(PurchaseRequisition.department),
            selectinload(PurchaseRequisition.cost_center),
            selectinload(PurchaseRequisition.collaborators),
        )
    )
    scope_filter = await visible_pr_filter(db, actor)
    if scope_filter is not None:
        stmt = stmt.where(scope_filter)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_pr(db: AsyncSession, actor: User, pr_id: UUID) -> PurchaseRequisition:
    from app.core.scoping import has_full_access, visible_pr_filter

    pr = await _load_pr(db, pr_id)
    if pr is None:
        raise HTTPException(404, "pr.not_found")
    if has_full_access(actor):
        return pr
    scope_filter = await visible_pr_filter(db, actor)
    if scope_filter is not None:
        check = await db.execute(
            select(PurchaseRequisition.id).where(PurchaseRequisition.id == pr_id, scope_filter)
        )
        if check.scalar_one_or_none() is None:
            raise HTTPException(403, "insufficient_role")
    return pr


async def get_pr_downstream(
    db: AsyncSession, actor: User, pr_id: UUID
) -> dict[str, list[dict[str, JSONValue]]]:
    pr = await get_pr(db, actor, pr_id)

    pos = list(
        (
            await db.execute(
                select(PurchaseOrder)
                .where(PurchaseOrder.pr_id == pr.id)
                .order_by(PurchaseOrder.created_at.desc())
            )
        )
        .scalars()
        .all()
    )
    po_ids = [p.id for p in pos]

    contracts: list[Contract] = []
    if po_ids:
        primary = (
            (
                await db.execute(
                    select(Contract)
                    .where(Contract.po_id.in_(po_ids))
                    .options(selectinload(Contract.supplier))
                )
            )
            .scalars()
            .all()
        )
        contracts.extend(primary)

        linked_contract_ids = list(
            (
                await db.execute(
                    select(POContractLink.contract_id).where(POContractLink.po_id.in_(po_ids))
                )
            )
            .scalars()
            .all()
        )
        if linked_contract_ids:
            known = {c.id for c in contracts}
            extra_ids = [cid for cid in linked_contract_ids if cid not in known]
            if extra_ids:
                extra = (
                    (
                        await db.execute(
                            select(Contract)
                            .where(Contract.id.in_(extra_ids))
                            .options(selectinload(Contract.supplier))
                        )
                    )
                    .scalars()
                    .all()
                )
                contracts.extend(extra)

    supplier_ids = {p.supplier_id for p in pos}
    supplier_ids.update(c.supplier_id for c in contracts)
    supplier_ids.discard(None)  # type: ignore[arg-type]
    supplier_map: dict[UUID, str] = {}
    if supplier_ids:
        rows = (
            (await db.execute(select(Supplier).where(Supplier.id.in_(supplier_ids))))
            .scalars()
            .all()
        )
        supplier_map = {s.id: s.name for s in rows}

    return {
        "purchase_orders": [
            {
                "id": str(p.id),
                "po_number": p.po_number,
                "status": p.status,
                "total_amount": str(p.total_amount),
                "currency": p.currency,
                "supplier_id": str(p.supplier_id) if p.supplier_id else None,
                "supplier_name": supplier_map.get(p.supplier_id) if p.supplier_id else None,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in pos
        ],
        "contracts": [
            {
                "id": str(c.id),
                "contract_number": c.contract_number,
                "title": c.title,
                "status": c.status,
                "total_amount": str(c.total_amount),
                "currency": c.currency,
                "po_id": str(c.po_id),
                "supplier_id": str(c.supplier_id) if c.supplier_id else None,
                "supplier_name": supplier_map.get(c.supplier_id) if c.supplier_id else None,
            }
            for c in contracts
        ],
    }


async def list_pos(db: AsyncSession, actor: User) -> list[PurchaseOrder]:
    from app.core.scoping import visible_po_id_subquery

    stmt = (
        select(PurchaseOrder)
        .options(
            selectinload(PurchaseOrder.supplier),
            selectinload(PurchaseOrder.pr),
        )
        .order_by(PurchaseOrder.created_at.desc())
    )
    visible_po_ids = await visible_po_id_subquery(db, actor)
    if visible_po_ids is not None:
        stmt = stmt.where(PurchaseOrder.id.in_(visible_po_ids))
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_po(db: AsyncSession, po_id: UUID, actor: User | None = None) -> PurchaseOrder:
    po = await _load_po(db, po_id)
    if po is None:
        raise HTTPException(404, "po.not_found")
    if actor is not None:
        from app.core.scoping import has_full_access, visible_pr_filter

        if not has_full_access(actor):
            scope_filter = await visible_pr_filter(db, actor)
            if scope_filter is not None:
                check = await db.execute(
                    select(PurchaseRequisition.id).where(
                        PurchaseRequisition.id == po.pr_id, scope_filter
                    )
                )
                if check.scalar_one_or_none() is None:
                    raise HTTPException(403, "insufficient_role")
    return po


_SUPPLIER_QUOTE_SOURCE_TYPE = "supplier_quote"


async def delete_pr(db: AsyncSession, actor: User, pr_id: UUID) -> None:
    pr = await get_pr(db, actor, pr_id)
    deletable_statuses = {
        PRStatus.DRAFT.value,
        PRStatus.RETURNED.value,
        PRStatus.REJECTED.value,
        PRStatus.CANCELLED.value,
    }
    if pr.status not in deletable_statuses:
        raise HTTPException(409, "pr.cannot_delete_active")
    await db.delete(pr)
    await db.commit()


async def delete_po(db: AsyncSession, actor: User, po_id: UUID) -> None:
    from app.models import Contract, InvoiceLine, PaymentRecord, Shipment

    po = await _load_po(db, po_id)
    if po is None:
        raise HTTPException(404, "po.not_found")

    shipment_count = (
        await db.execute(select(func.count(Shipment.id)).where(Shipment.po_id == po_id))
    ).scalar_one()
    if shipment_count:
        raise HTTPException(409, "po.cannot_delete_has_shipments")

    payment_count = (
        await db.execute(select(func.count(PaymentRecord.id)).where(PaymentRecord.po_id == po_id))
    ).scalar_one()
    if payment_count:
        raise HTTPException(409, "po.cannot_delete_has_payments")

    contract_count = (
        await db.execute(select(func.count(Contract.id)).where(Contract.po_id == po_id))
    ).scalar_one()
    if contract_count:
        raise HTTPException(409, "po.cannot_delete_has_contracts")

    po_item_ids = [i.id for i in po.items]
    if po_item_ids:
        invoice_count = (
            await db.execute(
                select(func.count(InvoiceLine.id)).where(InvoiceLine.po_item_id.in_(po_item_ids))
            )
        ).scalar_one()
        if invoice_count:
            raise HTTPException(409, "po.cannot_delete_has_invoices")

    parent_pr_id = po.pr_id

    await _audit(
        db,
        actor,
        "po.deleted",
        "purchase_order",
        str(po_id),
        metadata={"po_number": po.po_number, "total_amount": str(po.total_amount)},
    )
    await db.delete(po)
    await db.flush()

    if parent_pr_id is not None:
        pr = await _load_pr(db, parent_pr_id)
        if pr is not None:
            new_status = await _compute_pr_status_after_link_change(db, pr)
            if pr.status != new_status:
                pr.status = new_status

    await db.commit()


def _quote_source_ref(pr_number: str, line_no: int) -> str:
    return f"{pr_number}-L{line_no}"


async def list_pr_quote_candidates(db: AsyncSession, actor: User, pr_id: UUID) -> list[dict]:
    pr = await _load_pr(db, pr_id)
    if pr is None:
        raise HTTPException(404, "pr.not_found")
    _ = actor

    eligible_items = [
        i
        for i in pr.items
        if i.item_id is not None
        and i.supplier_id is not None
        and i.unit_price is not None
        and i.unit_price > 0
    ]
    if not eligible_items:
        return []

    source_refs = [_quote_source_ref(pr.pr_number, i.line_no) for i in eligible_items]
    existing_rows = (
        (
            await db.execute(
                select(SKUPriceRecord).where(
                    SKUPriceRecord.source_type == _SUPPLIER_QUOTE_SOURCE_TYPE,
                    SKUPriceRecord.source_ref.in_(source_refs),
                )
            )
        )
        .scalars()
        .all()
    )
    existing_by_ref = {r.source_ref: r for r in existing_rows}

    suppliers_map = {
        s.id: s
        for s in (
            (
                await db.execute(
                    select(Supplier).where(Supplier.id.in_([i.supplier_id for i in eligible_items]))
                )
            )
            .scalars()
            .all()
        )
    }

    candidates: list[dict] = []
    for item in eligible_items:
        ref = _quote_source_ref(pr.pr_number, item.line_no)
        existing = existing_by_ref.get(ref)
        already_persisted_same_price = (
            existing is not None
            and existing.price == item.unit_price
            and existing.supplier_id == item.supplier_id
        )
        supplier = suppliers_map.get(item.supplier_id)
        candidates.append(
            {
                "pr_item_id": item.id,
                "line_no": item.line_no,
                "item_id": item.item_id,
                "item_name": item.item_name,
                "supplier_id": item.supplier_id,
                "supplier_name": supplier.name if supplier else None,
                "supplier_code": supplier.code if supplier else None,
                "unit_price": item.unit_price,
                "currency": pr.currency or "CNY",
                "source_ref": ref,
                "already_exists": existing is not None,
                "already_up_to_date": already_persisted_same_price,
            }
        )
    return candidates


async def save_pr_supplier_quotes(
    db: AsyncSession,
    actor: User,
    pr_id: UUID,
    selected_line_nos: list[int] | None = None,
) -> list[SKUPriceRecord]:
    pr = await _load_pr(db, pr_id)
    if pr is None:
        raise HTTPException(404, "pr.not_found")

    line_filter = set(selected_line_nos) if selected_line_nos is not None else None

    eligible_items = [
        i
        for i in pr.items
        if i.item_id is not None
        and i.supplier_id is not None
        and i.unit_price is not None
        and i.unit_price > 0
        and (line_filter is None or i.line_no in line_filter)
    ]
    if not eligible_items:
        return []

    today = datetime.now(UTC).date()
    source_refs = [_quote_source_ref(pr.pr_number, i.line_no) for i in eligible_items]
    existing_rows = (
        (
            await db.execute(
                select(SKUPriceRecord).where(
                    SKUPriceRecord.source_type == _SUPPLIER_QUOTE_SOURCE_TYPE,
                    SKUPriceRecord.source_ref.in_(source_refs),
                )
            )
        )
        .scalars()
        .all()
    )
    existing_by_ref = {r.source_ref: r for r in existing_rows}

    written: list[SKUPriceRecord] = []
    for item in eligible_items:
        ref = _quote_source_ref(pr.pr_number, item.line_no)
        existing = existing_by_ref.get(ref)
        if existing is not None:
            if existing.price == item.unit_price and existing.supplier_id == item.supplier_id:
                written.append(existing)
                continue
            existing.price = item.unit_price
            existing.supplier_id = item.supplier_id
            existing.currency = pr.currency or "CNY"
            existing.quotation_date = today
            existing.entered_by_id = actor.id
            written.append(existing)
        else:
            row = SKUPriceRecord(
                item_id=item.item_id,
                supplier_id=item.supplier_id,
                price=item.unit_price,
                currency=pr.currency or "CNY",
                quotation_date=today,
                source_type=_SUPPLIER_QUOTE_SOURCE_TYPE,
                source_ref=ref,
                entered_by_id=actor.id,
            )
            db.add(row)
            written.append(row)

    await _audit(
        db,
        actor,
        "sku.supplier_quotes_recorded_from_pr",
        "purchase_requisition",
        str(pr.id),
        metadata={
            "pr_number": pr.pr_number,
            "count": len(written),
            "line_nos": [i.line_no for i in eligible_items],
        },
    )
    await db.commit()
    for row in written:
        await db.refresh(row)
    return written


async def list_collaborators(db: AsyncSession, pr_id: UUID) -> list[dict]:
    from app.models import pr_collaborators

    stmt = (
        select(User.id, User.display_name, User.email)
        .join(pr_collaborators, pr_collaborators.c.user_id == User.id)
        .where(pr_collaborators.c.pr_id == pr_id)
    )
    rows = (await db.execute(stmt)).all()
    return [{"id": str(r.id), "display_name": r.display_name, "email": r.email} for r in rows]


async def add_collaborator(db: AsyncSession, actor: User, pr_id: UUID, user_id: UUID) -> None:
    from app.models import pr_collaborators

    pr = await get_pr(db, actor, pr_id)
    if pr.requester_id != actor.id and actor.role not in {
        UserRole.ADMIN.value,
        UserRole.PROCUREMENT_MGR.value,
        UserRole.IT_BUYER.value,
        UserRole.DEPT_MANAGER.value,
    }:
        raise HTTPException(403, "pr.only_requester_can_add_collaborator")

    target = await db.get(User, user_id)
    if target is None:
        raise HTTPException(404, "user.not_found")

    existing = (
        await db.execute(
            select(pr_collaborators.c.user_id).where(
                pr_collaborators.c.pr_id == pr_id,
                pr_collaborators.c.user_id == user_id,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        return

    await db.execute(
        pr_collaborators.insert().values(pr_id=pr_id, user_id=user_id, added_by_id=actor.id)
    )
    await db.commit()

    try:
        from app.models import NotificationCategory
        from app.services.notifications import create_notification

        await create_notification(
            db,
            user_id=user_id,
            category=NotificationCategory.SYSTEM,
            title=f"您已被添加为 {pr.pr_number} 的协作者",
            body=(
                f"**PR**: {pr.pr_number}\n**标题**: {pr.title}\n**添加人**: {actor.display_name}"
            ),
            link_url=f"/purchase-requisitions/{pr.id}",
            biz_type="pr",
            biz_id=pr.id,
        )
        await db.commit()
    except Exception:
        logger.warning("Failed to send collaborator notification for pr=%s", pr_id, exc_info=True)


async def remove_collaborator(db: AsyncSession, actor: User, pr_id: UUID, user_id: UUID) -> None:
    from app.models import pr_collaborators

    pr = await get_pr(db, actor, pr_id)
    if pr.requester_id != actor.id and actor.role not in {
        UserRole.ADMIN.value,
        UserRole.PROCUREMENT_MGR.value,
        UserRole.IT_BUYER.value,
        UserRole.DEPT_MANAGER.value,
    }:
        raise HTTPException(403, "pr.only_requester_can_remove_collaborator")

    await db.execute(
        pr_collaborators.delete().where(
            pr_collaborators.c.pr_id == pr_id,
            pr_collaborators.c.user_id == user_id,
        )
    )
    await db.commit()
