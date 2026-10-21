from __future__ import annotations

import logging
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import new_uuid
from app.models import RFQ, RFQItem, RFQQuote, RFQStatus, RFQSupplier, User
from app.services import sku as sku_svc

logger = logging.getLogger(__name__)


async def list_rfqs(db: AsyncSession, user: User) -> list[RFQ]:
    from app.core.scoping import is_rfq_hidden

    if is_rfq_hidden(user):
        return []
    q = select(RFQ).order_by(RFQ.created_at.desc())
    return list((await db.execute(q)).scalars().all())


async def get_rfq(db: AsyncSession, rfq_id: UUID) -> RFQ:
    q = (
        select(RFQ)
        .where(RFQ.id == rfq_id)
        .options(
            selectinload(RFQ.items),
            selectinload(RFQ.suppliers).selectinload(RFQSupplier.supplier),
            selectinload(RFQ.quotes).selectinload(RFQQuote.supplier),
        )
    )
    rfq = (await db.execute(q)).scalar_one_or_none()
    if rfq is None:
        raise HTTPException(404, "rfq.not_found")
    return rfq


async def create_rfq(db: AsyncSession, user: User, data: dict) -> RFQ:
    from app.services.purchase import _next_rfq_number

    rfq = RFQ(
        id=new_uuid(),
        rfq_number=await _next_rfq_number(db),
        title=data["title"],
        pr_id=data.get("pr_id"),
        deadline=data.get("deadline"),
        notes=data.get("notes"),
        created_by_id=user.id,
        company_id=user.company_id,
    )
    db.add(rfq)

    for item_data in data.get("items", []):
        rfq_item = RFQItem(
            id=new_uuid(),
            rfq_id=rfq.id,
            item_id=item_data.get("item_id"),
            item_name=item_data["item_name"],
            specification=item_data.get("specification"),
            qty=Decimal(str(item_data["qty"])),
            uom=item_data.get("uom", "EA"),
        )
        db.add(rfq_item)

    await db.flush()
    return rfq


def _add_rfq_supplier(db: AsyncSession, rfq_id: UUID, supplier_id: UUID) -> None:
    db.add(RFQSupplier(id=new_uuid(), rfq_id=rfq_id, supplier_id=supplier_id))


async def send_rfq(db: AsyncSession, rfq_id: UUID) -> RFQ:
    rfq = await get_rfq(db, rfq_id)
    if rfq.status != RFQStatus.DRAFT.value:
        raise HTTPException(409, "rfq.already_sent")
    if not rfq.items:
        raise HTTPException(422, "rfq.no_items")
    if not rfq.suppliers:
        raise HTTPException(422, "rfq.no_suppliers")
    rfq.status = RFQStatus.SENT.value
    await db.flush()
    return rfq


async def add_quote(
    db: AsyncSession,
    rfq_id: UUID,
    data: dict,
    actor: User | None = None,
) -> RFQQuote:
    rfq = await get_rfq(db, rfq_id)
    if rfq.status not in (RFQStatus.SENT.value, RFQStatus.QUOTING.value):
        raise HTTPException(409, "rfq.not_accepting_quotes")

    if rfq.status == RFQStatus.SENT.value:
        rfq.status = RFQStatus.QUOTING.value

    quote = RFQQuote(
        id=new_uuid(),
        rfq_id=rfq_id,
        rfq_item_id=data["rfq_item_id"],
        supplier_id=data["supplier_id"],
        unit_price=Decimal(str(data["unit_price"])),
        currency=data.get("currency", "CNY"),
        delivery_days=data.get("delivery_days"),
        valid_until=data.get("valid_until"),
        notes=data.get("notes"),
    )
    db.add(quote)

    sup = next((s for s in rfq.suppliers if str(s.supplier_id) == str(data["supplier_id"])), None)
    if sup and not sup.responded_at:
        sup.responded_at = datetime.now(UTC)
        sup.status = "quoted"

    # Record the price through the shared path, so benchmarks, anomaly detection and
    # the audit trail all happen. This used to insert SKUPriceRecord directly inside a
    # bare try/except: pass — a quoted price silently skipped every one of them, and a
    # failure left no trace. A failed side effect must not lose the quote itself, so
    # the error is logged rather than raised.
    try:
        rfq_item = await db.get(RFQItem, data["rfq_item_id"])
        if rfq_item is not None and rfq_item.item_id is not None and actor is not None:
            sid = (
                data["supplier_id"]
                if isinstance(data["supplier_id"], UUID)
                else UUID(str(data["supplier_id"]))
            )
            await sku_svc.record_price(
                db,
                actor,
                rfq_item.item_id,
                Decimal(str(data["unit_price"])),
                date.today(),
                supplier_id=sid,
                source_type="quote",
                source_ref=f"RFQ:{rfq.rfq_number}",
                currency=data.get("currency", "CNY"),
            )
    except Exception:
        logger.warning("rfq %s: could not record the quoted price", rfq_id, exc_info=True)

    await db.flush()
    return quote


async def award_quote(
    db: AsyncSession,
    rfq_id: UUID,
    quote_ids: list[str],
) -> RFQ:
    rfq = await get_rfq(db, rfq_id)
    if rfq.status not in (RFQStatus.QUOTING.value, RFQStatus.EVALUATION.value):
        raise HTTPException(409, "rfq.cannot_award")

    for q in rfq.quotes:
        q.is_selected = str(q.id) in quote_ids

    rfq.status = RFQStatus.AWARDED.value
    rfq.awarded_at = datetime.now(UTC)
    await db.flush()
    return rfq


async def delete_rfq(db: AsyncSession, rfq_id: UUID) -> None:
    rfq = await get_rfq(db, rfq_id)
    if rfq.status != RFQStatus.DRAFT.value:
        raise HTTPException(409, "rfq.cannot_delete_non_draft")
    await db.delete(rfq)
    await db.flush()
    await db.commit()


_LOCKED_STATUSES = {RFQStatus.AWARDED.value, RFQStatus.CLOSED.value, RFQStatus.CANCELLED.value}


async def update_rfq(
    db: AsyncSession,
    rfq_id: UUID,
    data: dict,
    actor: User,
) -> RFQ:
    rfq = await get_rfq(db, rfq_id)
    if rfq.status in _LOCKED_STATUSES:
        raise HTTPException(409, "rfq.cannot_edit_finalized")

    if data.get("title"):
        rfq.title = data["title"]
    if "deadline" in data:
        rfq.deadline = data["deadline"]
    if "notes" in data:
        rfq.notes = data["notes"]

    if "items" in data:
        existing_items = {str(item.id): item for item in rfq.items}
        incoming_ids = set()
        for item_data in data["items"]:
            item_id = item_data.get("id")
            if item_id and item_id in existing_items:
                item = existing_items[item_id]
                item.item_name = item_data.get("item_name", item.item_name)
                item.item_id = item_data.get("item_id", item.item_id)
                item.specification = item_data.get("specification", item.specification)
                item.qty = Decimal(str(item_data.get("qty", item.qty)))
                item.uom = item_data.get("uom", item.uom)
                incoming_ids.add(item_id)
            else:
                new_item = RFQItem(
                    id=new_uuid(),
                    rfq_id=rfq.id,
                    item_id=item_data.get("item_id"),
                    item_name=item_data["item_name"],
                    specification=item_data.get("specification"),
                    qty=Decimal(str(item_data["qty"])),
                    uom=item_data.get("uom", "EA"),
                )
                db.add(new_item)
        for eid, item in existing_items.items():
            if eid not in incoming_ids:
                await db.delete(item)

    if "supplier_ids" in data:
        existing_suppliers = {str(s.supplier_id): s for s in rfq.suppliers}
        new_supplier_ids = {str(sid) for sid in data["supplier_ids"]}
        for sid in new_supplier_ids - set(existing_suppliers.keys()):
            _add_rfq_supplier(db, rfq.id, UUID(sid))
        for sid, link in existing_suppliers.items():
            if sid not in new_supplier_ids:
                await db.delete(link)

    await db.flush()
    await db.commit()

    from app.models import AuditLog

    db.add(
        AuditLog(
            actor_id=actor.id,
            actor_name=actor.display_name,
            event_type="rfq.updated",
            resource_type="rfq",
            resource_id=str(rfq.id),
            metadata_json={"rfq_number": rfq.rfq_number, "status": rfq.status},
        )
    )
    await db.commit()

    return await get_rfq(db, rfq.id)


async def list_pending_collection(db: AsyncSession, user: User) -> list[dict]:
    """RFQs that went out and still owe us quotes.

    This is a to-do list, not a notification: procurement chases suppliers by hand,
    so what they need is one place that says "these are outstanding, and these are
    already late".
    """
    from app.core.scoping import is_rfq_hidden

    today = date.today()
    statement = (
        select(RFQ)
        .where(RFQ.status.in_((RFQStatus.SENT.value, RFQStatus.QUOTING.value)))
        .options(
            selectinload(RFQ.suppliers).selectinload(RFQSupplier.supplier),
            selectinload(RFQ.items),
        )
        .order_by(RFQ.deadline.is_(None), RFQ.deadline)
    )
    if is_rfq_hidden(user):
        return []

    rfqs = (await db.execute(statement)).scalars().all()
    quoted_suppliers = set(
        (await db.execute(select(RFQQuote.rfq_id, RFQQuote.supplier_id).distinct())).all()
    )

    pending: list[dict] = []
    for rfq in rfqs:
        outstanding = [
            invited
            for invited in rfq.suppliers
            if invited.responded_at is None
            and (rfq.id, invited.supplier_id) not in quoted_suppliers
        ]
        if not outstanding:
            continue
        overdue_days = 0
        if rfq.deadline is not None and rfq.deadline < today:
            overdue_days = (today - rfq.deadline).days
        pending.append(
            {
                "id": str(rfq.id),
                "rfq_number": rfq.rfq_number,
                "title": rfq.title,
                "status": rfq.status,
                "deadline": rfq.deadline.isoformat() if rfq.deadline else None,
                "overdue_days": overdue_days,
                "invited_count": len(rfq.suppliers),
                "outstanding_count": len(outstanding),
                "outstanding_suppliers": [
                    invited.supplier.name if invited.supplier else "" for invited in outstanding
                ],
                "item_count": len(rfq.items),
            }
        )
    return pending
