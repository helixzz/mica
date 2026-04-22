from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser, require_roles
from app.db import get_db
from app.services import rfq as svc

router = APIRouter(tags=["rfq"])


class RFQItemIn(BaseModel):
    item_id: UUID | None = None
    item_name: str
    specification: str | None = None
    qty: Decimal
    uom: str = "EA"


class RFQCreateIn(BaseModel):
    title: str = Field(min_length=1)
    pr_id: UUID | None = None
    deadline: date | None = None
    notes: str | None = None
    items: list[RFQItemIn] = Field(min_length=1)
    supplier_ids: list[UUID] = Field(min_length=1)


class RFQQuoteIn(BaseModel):
    rfq_item_id: UUID
    supplier_id: UUID
    unit_price: Decimal
    currency: str = "CNY"
    delivery_days: int | None = None
    valid_until: date | None = None
    notes: str | None = None


class AwardIn(BaseModel):
    quote_ids: list[UUID]


class RFQOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    rfq_number: str
    title: str
    status: str
    pr_id: UUID | None = None
    deadline: date | None = None
    notes: str | None = None
    created_by_id: UUID
    company_id: UUID
    awarded_at: str | None = None
    created_at: str
    updated_at: str


class RFQItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    item_id: UUID | None = None
    item_name: str
    specification: str | None = None
    qty: Decimal
    uom: str


class RFQSupplierOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    supplier_id: UUID
    status: str
    supplier_name: str | None = None


class RFQQuoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    rfq_item_id: UUID
    supplier_id: UUID
    unit_price: Decimal
    currency: str
    delivery_days: int | None = None
    valid_until: date | None = None
    notes: str | None = None
    is_selected: bool
    supplier_name: str | None = None


class RFQDetailOut(RFQOut):
    items: list[RFQItemOut] = []
    suppliers: list[RFQSupplierOut] = []
    quotes: list[RFQQuoteOut] = []


@router.get("/rfqs", response_model=list[RFQOut])
async def list_rfqs(
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await svc.list_rfqs(db, user)


@router.get("/rfqs/{rfq_id}", response_model=RFQDetailOut)
async def get_rfq(
    rfq_id: UUID,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    rfq = await svc.get_rfq(db, rfq_id)
    return _to_detail(rfq)


@router.post("/rfqs", response_model=RFQOut, status_code=201)
async def create_rfq(
    body: RFQCreateIn,
    _user: Annotated[None, Depends(require_roles("admin", "it_buyer", "procurement_mgr"))],
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    rfq = await svc.create_rfq(db, user, body.model_dump())
    await db.commit()
    return rfq


@router.post("/rfqs/{rfq_id}/send", response_model=RFQOut)
async def send_rfq(
    rfq_id: UUID,
    _user: Annotated[None, Depends(require_roles("admin", "it_buyer", "procurement_mgr"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    rfq = await svc.send_rfq(db, rfq_id)
    await db.commit()
    return rfq


@router.post("/rfqs/{rfq_id}/quotes", response_model=RFQQuoteOut, status_code=201)
async def add_quote(
    rfq_id: UUID,
    body: RFQQuoteIn,
    _user: Annotated[None, Depends(require_roles("admin", "it_buyer", "procurement_mgr"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    q = await svc.add_quote(db, rfq_id, body.model_dump())
    await db.commit()
    return RFQQuoteOut(
        id=q.id,
        rfq_item_id=q.rfq_item_id,
        supplier_id=q.supplier_id,
        unit_price=q.unit_price,
        currency=q.currency,
        delivery_days=q.delivery_days,
        valid_until=q.valid_until,
        notes=q.notes,
        is_selected=q.is_selected,
    )


@router.post("/rfqs/{rfq_id}/award", response_model=RFQOut)
async def award_quotes(
    rfq_id: UUID,
    body: AwardIn,
    _user: Annotated[None, Depends(require_roles("admin", "it_buyer", "procurement_mgr"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    rfq = await svc.award_quote(db, rfq_id, [str(qid) for qid in body.quote_ids])
    await db.commit()
    return rfq


def _to_detail(rfq) -> dict:
    return {
        "id": rfq.id,
        "rfq_number": rfq.rfq_number,
        "title": rfq.title,
        "status": rfq.status,
        "pr_id": rfq.pr_id,
        "deadline": rfq.deadline,
        "notes": rfq.notes,
        "created_by_id": rfq.created_by_id,
        "company_id": rfq.company_id,
        "awarded_at": str(rfq.awarded_at) if rfq.awarded_at else None,
        "created_at": str(rfq.created_at),
        "updated_at": str(rfq.updated_at),
        "items": [
            {
                "id": i.id,
                "item_id": i.item_id,
                "item_name": i.item_name,
                "specification": i.specification,
                "qty": i.qty,
                "uom": i.uom,
            }
            for i in rfq.items
        ],
        "suppliers": [
            {
                "id": s.id,
                "supplier_id": s.supplier_id,
                "status": s.status,
                "supplier_name": getattr(s.supplier, "name", None),
            }
            for s in rfq.suppliers
        ],
        "quotes": [
            {
                "id": q.id,
                "rfq_item_id": q.rfq_item_id,
                "supplier_id": q.supplier_id,
                "unit_price": q.unit_price,
                "currency": q.currency,
                "delivery_days": q.delivery_days,
                "valid_until": q.valid_until,
                "notes": q.notes,
                "is_selected": q.is_selected,
                "supplier_name": getattr(q.supplier, "name", None),
            }
            for q in rfq.quotes
        ],
    }
