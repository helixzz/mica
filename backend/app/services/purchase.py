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
    Contract,
    JSONValue,
    POContractLink,
    POItem,
    POStatus,
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
        company_id=payload.company_id or actor.company_id,
        department_id=payload.department_id or actor.department_id,
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


async def convert_pr_to_po(db: AsyncSession, actor: User, pr_id: UUID) -> list[PurchaseOrder]:
    pr = await _load_pr(db, pr_id)
    if pr is None:
        raise HTTPException(404, "pr.not_found")
    if pr.status != PRStatus.APPROVED.value:
        raise HTTPException(409, "pr.must_be_approved_to_convert")
    if not pr.items:
        raise HTTPException(422, "pr.no_items")

    groups = await _build_supplier_groups(pr)

    created_pos: list[PurchaseOrder] = []
    for supplier_id, items in groups.items():
        po_number = await _next_po_number(db)
        subtotal = sum((Decimal(str(i.amount or 0)) for i in items), Decimal("0"))
        po = PurchaseOrder(
            po_number=po_number,
            pr_id=pr.id,
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
            },
        )
        created_pos.append(po)

    pr.status = PRStatus.CONVERTED.value
    await db.commit()

    refreshed: list[PurchaseOrder] = []
    for po in created_pos:
        loaded = await _load_po(db, po.id)
        if loaded is None:
            raise HTTPException(404, "po.not_found")
        refreshed.append(loaded)
    refreshed.sort(key=lambda p: p.po_number)
    return refreshed


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
    _ = actor
    stmt = (
        select(PurchaseOrder)
        .options(
            selectinload(PurchaseOrder.supplier),
            selectinload(PurchaseOrder.pr),
        )
        .order_by(PurchaseOrder.created_at.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_po(db: AsyncSession, po_id: UUID) -> PurchaseOrder:
    po = await _load_po(db, po_id)
    if po is None:
        raise HTTPException(404, "po.not_found")
    return po


_SUPPLIER_QUOTE_SOURCE_TYPE = "supplier_quote"


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
