from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import new_uuid
from app.models import RFQ, RFQItem, RFQQuote, RFQStatus, RFQSupplier, User


async def list_rfqs(db: AsyncSession, user: User) -> list[RFQ]:
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
    from app.services.purchase import _next_number

    rfq = RFQ(
        id=new_uuid(),
        rfq_number=await _next_number(db, "RFQ", user.company_id),
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

    for sid in data.get("supplier_ids", []):
        rfq_sup = RFQSupplier(
            id=new_uuid(),
            rfq_id=rfq.id,
            supplier_id=UUID(sid),
        )
        db.add(rfq_sup)

    await db.flush()
    return rfq


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
) -> RFQQuote:
    rfq = await get_rfq(db, rfq_id)
    if rfq.status not in (RFQStatus.SENT.value, RFQStatus.QUOTING.value):
        raise HTTPException(409, "rfq.not_accepting_quotes")

    if rfq.status == RFQStatus.SENT.value:
        rfq.status = RFQStatus.QUOTING.value

    quote = RFQQuote(
        id=new_uuid(),
        rfq_id=rfq_id,
        rfq_item_id=UUID(data["rfq_item_id"]),
        supplier_id=UUID(data["supplier_id"]),
        unit_price=Decimal(str(data["unit_price"])),
        currency=data.get("currency", "CNY"),
        delivery_days=data.get("delivery_days"),
        valid_until=data.get("valid_until"),
        notes=data.get("notes"),
    )
    db.add(quote)

    sup = next((s for s in rfq.suppliers if str(s.supplier_id) == data["supplier_id"]), None)
    if sup and not sup.responded_at:
        sup.responded_at = datetime.now(UTC)
        sup.status = "quoted"

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
