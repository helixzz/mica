from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser
from app.db import get_db
from app.schemas import (
    ContractCreateIn,
    ContractOut,
    InvoiceCreateIn,
    InvoiceListOut,
    InvoiceOut,
    PaymentConfirmIn,
    PaymentCreateIn,
    PaymentOut,
    POProgressOut,
    ShipmentCreateIn,
    ShipmentOut,
    SerialNumberIn,
)
from app.services import flow


router = APIRouter()


@router.post("/contracts", response_model=ContractOut, status_code=status.HTTP_201_CREATED, tags=["flow"])
async def create_contract(
    payload: ContractCreateIn,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    c = await flow.create_contract(
        db, user, payload.po_id, payload.title, payload.total_amount,
        payload.signed_date, payload.effective_date, payload.expiry_date, payload.notes,
    )
    return ContractOut.model_validate(c)


@router.get("/contracts", response_model=list[ContractOut], tags=["flow"])
async def list_contracts(
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    po_id: UUID | None = None,
):
    return [ContractOut.model_validate(c) for c in await flow.list_contracts(db, po_id)]


@router.post("/shipments", response_model=ShipmentOut, status_code=status.HTTP_201_CREATED, tags=["flow"])
async def create_shipment(
    payload: ShipmentCreateIn,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    s = await flow.create_shipment(
        db, user, payload.po_id,
        [i.model_dump() for i in payload.items],
        carrier=payload.carrier,
        tracking_number=payload.tracking_number,
        expected_date=payload.expected_date,
        actual_date=payload.actual_date,
        notes=payload.notes,
    )
    return ShipmentOut.model_validate(s)


@router.get("/shipments", response_model=list[ShipmentOut], tags=["flow"])
async def list_shipments(
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    po_id: UUID | None = None,
):
    return [ShipmentOut.model_validate(s) for s in await flow.list_shipments(db, po_id)]


@router.post("/shipments/items/{shipment_item_id}/serials", tags=["flow"])
async def record_serials(
    shipment_item_id: UUID,
    payload: list[SerialNumberIn],
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    entries = await flow.record_serial_numbers(
        db, user, shipment_item_id, [s.model_dump() for s in payload]
    )
    return [{"id": str(e.id), "serial_number": e.serial_number} for e in entries]


@router.post("/payments", response_model=PaymentOut, status_code=status.HTTP_201_CREATED, tags=["flow"])
async def create_payment(
    payload: PaymentCreateIn,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    p = await flow.create_payment(
        db, user, payload.po_id, payload.amount,
        due_date=payload.due_date,
        payment_date=payload.payment_date,
        payment_method=payload.payment_method,
        transaction_ref=payload.transaction_ref,
        notes=payload.notes,
    )
    return PaymentOut.model_validate(p)


@router.post("/payments/{payment_id}/confirm", response_model=PaymentOut, tags=["flow"])
async def confirm_payment(
    payment_id: UUID,
    payload: PaymentConfirmIn,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    p = await flow.confirm_payment(db, user, payment_id, payload.payment_date, payload.transaction_ref)
    return PaymentOut.model_validate(p)


@router.get("/payments", response_model=list[PaymentOut], tags=["flow"])
async def list_payments(
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    po_id: UUID | None = None,
):
    return [PaymentOut.model_validate(p) for p in await flow.list_payments(db, po_id)]


@router.post("/invoices", status_code=status.HTTP_201_CREATED, tags=["flow"])
async def create_invoice(
    payload: InvoiceCreateIn,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    inv, validations = await flow.create_invoice(
        db, user,
        supplier_id=payload.supplier_id,
        invoice_number=payload.invoice_number,
        invoice_date=payload.invoice_date,
        lines_in=[l.model_dump() for l in payload.lines],
        tax_number=payload.tax_number,
        due_date=payload.due_date,
        notes=payload.notes,
        attachment_document_ids=payload.attachment_document_ids,
    )
    inv_dict = InvoiceOut.model_validate(inv).model_dump(mode="json")
    inv_dict["attachments"] = [
        {
            "document_id": str(a.document_id),
            "role": a.role,
            "display_order": a.display_order,
            "original_filename": a.document.original_filename,
            "content_type": a.document.content_type,
            "file_size": a.document.file_size,
        }
        for a in inv.attachments
    ]
    return {
        "invoice": inv_dict,
        "validations": [
            {**v, "invoiced_subtotal": str(v["invoiced_subtotal"]),
             "po_remaining": str(v["po_remaining"]) if v["po_remaining"] is not None else None,
             "overage": str(v["overage"]),
             "po_item_id": str(v["po_item_id"]) if v["po_item_id"] else None}
            for v in validations
        ],
    }


@router.get("/invoices", response_model=list[InvoiceListOut], tags=["flow"])
async def list_invoices(
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    po_id: UUID | None = None,
):
    if po_id:
        rows = await flow.list_invoices_for_po(db, po_id)
    else:
        rows = await flow.list_invoices(db)
    return [InvoiceListOut.model_validate(i) for i in rows]


@router.get("/invoices/{invoice_id}", tags=["flow"])
async def get_invoice(
    invoice_id: UUID,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from app.models import Invoice, InvoiceDocument

    inv = (
        await db.execute(
            select(Invoice)
            .where(Invoice.id == invoice_id)
            .options(
                selectinload(Invoice.lines),
                selectinload(Invoice.attachments).selectinload(InvoiceDocument.document),
            )
        )
    ).scalar_one_or_none()
    if inv is None:
        from fastapi import HTTPException

        raise HTTPException(404, "invoice.not_found")
    inv_dict = InvoiceOut.model_validate(inv).model_dump(mode="json")
    inv_dict["attachments"] = [
        {
            "document_id": str(a.document_id),
            "role": a.role,
            "display_order": a.display_order,
            "original_filename": a.document.original_filename,
            "content_type": a.document.content_type,
            "file_size": a.document.file_size,
        }
        for a in inv.attachments
    ]
    return inv_dict


@router.get("/purchase-orders/{po_id}/progress", response_model=POProgressOut, tags=["flow"])
async def get_po_progress(
    po_id: UUID,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    data = await flow.po_progress(db, po_id)
    return POProgressOut.model_validate(data)
