from datetime import datetime
from secrets import token_urlsafe
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser, require_roles
from app.db import get_db
from app.models import (
    Contract,
    PaymentRecord,
    PurchaseOrder,
    Shipment,
    Supplier,
)

router = APIRouter()


class SupplierPortalPO(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    po_number: str
    status: str
    currency: str
    total_amount: str
    qty_received: str
    amount_paid: str
    created_at: datetime


class SupplierPortalContract(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    contract_number: str
    title: str
    status: str
    currency: str
    total_amount: str
    signed_date: datetime | None
    effective_date: datetime | None
    expiry_date: datetime | None


class SupplierPortalPayment(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    payment_number: str
    amount: str
    currency: str
    status: str
    due_date: datetime | None
    payment_date: datetime | None
    payment_method: str


class SupplierPortalShipment(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    shipment_number: str
    batch_no: int
    status: str
    carrier: str | None
    tracking_number: str | None
    expected_date: datetime | None
    actual_date: datetime | None


class SupplierPortalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    code: str
    contact_name: str | None
    contact_phone: str | None
    contact_email: str | None
    purchase_orders: list[SupplierPortalPO]
    contracts: list[SupplierPortalContract]
    payments: list[SupplierPortalPayment]
    shipments: list[SupplierPortalShipment]


@router.get("/supplier-portal/{token}", response_model=SupplierPortalOut, tags=["supplier-portal"])
async def supplier_portal(
    token: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SupplierPortalOut:
    supplier = (
        await db.execute(
            select(Supplier).where(
                Supplier.access_token == token,
                Supplier.is_enabled.is_(True),
                Supplier.is_deleted.is_(False),
            )
        )
    ).scalar_one_or_none()

    if supplier is None:
        raise HTTPException(status_code=404, detail="supplier_portal.invalid_token")

    pos_result = await db.execute(
        select(PurchaseOrder)
        .where(PurchaseOrder.supplier_id == supplier.id)
        .order_by(PurchaseOrder.created_at.desc())
        .limit(200)
    )
    pos = pos_result.scalars().all()

    contracts_result = await db.execute(
        select(Contract)
        .where(Contract.supplier_id == supplier.id)
        .order_by(Contract.signed_date.desc())
        .limit(200)
    )
    contracts = contracts_result.scalars().all()

    payments_result = await db.execute(
        select(PaymentRecord)
        .join(PurchaseOrder, PaymentRecord.po_id == PurchaseOrder.id)
        .where(PurchaseOrder.supplier_id == supplier.id)
        .order_by(PaymentRecord.due_date.desc())
        .limit(200)
    )
    payments = payments_result.scalars().all()

    shipments_result = await db.execute(
        select(Shipment)
        .join(PurchaseOrder, Shipment.po_id == PurchaseOrder.id)
        .where(PurchaseOrder.supplier_id == supplier.id)
        .order_by(Shipment.expected_date.desc())
        .limit(200)
    )
    shipments = shipments_result.scalars().all()

    return SupplierPortalOut(
        id=supplier.id,
        name=supplier.name,
        code=supplier.code,
        contact_name=supplier.contact_name,
        contact_phone=supplier.contact_phone,
        contact_email=supplier.contact_email,
        purchase_orders=[
            SupplierPortalPO(
                po_number=po.po_number,
                status=po.status,
                currency=po.currency,
                total_amount=str(po.total_amount),
                qty_received=str(po.qty_received),
                amount_paid=str(po.amount_paid),
                created_at=po.created_at,
            )
            for po in pos
        ],
        contracts=[
            SupplierPortalContract(
                contract_number=c.contract_number,
                title=c.title,
                status=c.status,
                currency=c.currency,
                total_amount=str(c.total_amount),
                signed_date=c.signed_date,
                effective_date=c.effective_date,
                expiry_date=c.expiry_date,
            )
            for c in contracts
        ],
        payments=[
            SupplierPortalPayment(
                payment_number=p.payment_number,
                amount=str(p.amount),
                currency=p.currency,
                status=p.status,
                due_date=p.due_date,
                payment_date=p.payment_date,
                payment_method=p.payment_method,
            )
            for p in payments
        ],
        shipments=[
            SupplierPortalShipment(
                shipment_number=s.shipment_number,
                batch_no=s.batch_no,
                status=s.status,
                carrier=s.carrier,
                tracking_number=s.tracking_number,
                expected_date=s.expected_date,
                actual_date=s.actual_date,
            )
            for s in shipments
        ],
    )


@router.post("/suppliers/{supplier_id}/generate-token", tags=["supplier-portal"])
async def generate_supplier_token(
    supplier_id: UUID,
    user: Annotated[CurrentUser, Depends(require_roles("admin", "procurement_mgr"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    supplier = await db.get(Supplier, supplier_id)
    if supplier is None:
        raise HTTPException(status_code=404, detail="supplier.not_found")

    supplier.access_token = token_urlsafe(32)
    await db.commit()
    await db.refresh(supplier)

    return {"token": supplier.access_token, "supplier_id": str(supplier.id)}


@router.post("/suppliers/{supplier_id}/revoke-token", tags=["supplier-portal"])
async def revoke_supplier_token(
    supplier_id: UUID,
    user: Annotated[CurrentUser, Depends(require_roles("admin", "procurement_mgr"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    supplier = await db.get(Supplier, supplier_id)
    if supplier is None:
        raise HTTPException(status_code=404, detail="supplier.not_found")

    supplier.access_token = None
    await db.commit()

    return {"message": "Token revoked", "supplier_id": str(supplier.id)}
