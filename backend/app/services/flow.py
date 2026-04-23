from __future__ import annotations

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
    Document,
    Invoice,
    InvoiceDocument,
    InvoiceLine,
    InvoiceStatus,
    PaymentRecord,
    PaymentStatus,
    POItem,
    POStatus,
    PurchaseOrder,
    SerialNumberEntry,
    Shipment,
    ShipmentItem,
    ShipmentStatus,
    Supplier,
    User,
)
from app.services import contracts as contract_svc


def _as_decimal(v) -> Decimal:
    return v if isinstance(v, Decimal) else Decimal(str(v))


async def _audit_write(
    db: AsyncSession, actor: User, event: str, rtype: str, rid: str, meta: dict | None = None
) -> None:
    db.add(
        AuditLog(
            actor_id=actor.id,
            actor_name=actor.display_name,
            event_type=event,
            resource_type=rtype,
            resource_id=rid,
            metadata_json=meta,
        )
    )


async def _load_po(db: AsyncSession, po_id: UUID) -> PurchaseOrder | None:
    return (
        await db.execute(
            select(PurchaseOrder)
            .where(PurchaseOrder.id == po_id)
            .options(selectinload(PurchaseOrder.items))
        )
    ).scalar_one_or_none()


async def create_contract(
    db: AsyncSession,
    actor: User,
    po_id: UUID,
    title: str,
    total_amount: Decimal,
    signed_date=None,
    effective_date=None,
    expiry_date=None,
    notes: str | None = None,
) -> Contract:
    po = await _load_po(db, po_id)
    if po is None:
        raise HTTPException(404, "po.not_found")

    year = datetime.now(UTC).year
    prefix = f"CT-{year}-"
    n = (
        await db.execute(
            select(func.count(Contract.id)).where(Contract.contract_number.startswith(prefix))
        )
    ).scalar_one() or 0
    number = f"{prefix}{n + 1:04d}"

    contract = Contract(
        contract_number=number,
        po_id=po.id,
        supplier_id=po.supplier_id,
        title=title,
        currency=po.currency,
        total_amount=_as_decimal(total_amount),
        signed_date=signed_date,
        effective_date=effective_date,
        expiry_date=expiry_date,
        notes=notes,
    )
    db.add(contract)
    await db.flush()
    await contract_svc.create_contract_version(
        db,
        contract=contract,
        actor=actor,
        change_type="created",
    )
    await _audit_write(
        db,
        actor,
        "contract.created",
        "contract",
        str(contract.id) or "",
        meta={"contract_number": number, "po_id": str(po.id)},
    )
    await db.commit()
    await db.refresh(contract)
    return contract


async def list_contracts(db: AsyncSession, po_id: UUID | None = None) -> list[Contract]:
    stmt = select(Contract).order_by(Contract.created_at.desc())
    if po_id:
        stmt = stmt.where(Contract.po_id == po_id)
    return list((await db.execute(stmt)).scalars().all())


async def create_shipment(
    db: AsyncSession,
    actor: User,
    po_id: UUID,
    items_in: list[dict],
    carrier: str | None = None,
    tracking_number: str | None = None,
    expected_date=None,
    actual_date=None,
    notes: str | None = None,
) -> Shipment:
    po = await _load_po(db, po_id)
    if po is None:
        raise HTTPException(404, "po.not_found")

    existing_count = (
        await db.execute(select(func.count(Shipment.id)).where(Shipment.po_id == po_id))
    ).scalar_one() or 0
    batch_no = existing_count + 1
    shipment_number = f"{po.po_number}-S{batch_no:02d}"

    shipment = Shipment(
        shipment_number=shipment_number,
        po_id=po_id,
        batch_no=batch_no,
        is_default=(batch_no == 1),
        status=ShipmentStatus.ARRIVED.value if actual_date else ShipmentStatus.IN_TRANSIT.value,
        carrier=carrier,
        tracking_number=tracking_number,
        expected_date=expected_date,
        actual_date=actual_date,
        notes=notes,
    )
    db.add(shipment)
    await db.flush()

    po_item_map = {str(i.id): i for i in po.items}
    for idx, item_in in enumerate(items_in, start=1):
        po_item_id = item_in["po_item_id"]
        po_item = po_item_map.get(str(po_item_id))
        if po_item is None:
            raise HTTPException(422, "shipment.invalid_po_item")
        qty_shipped = _as_decimal(item_in["qty_shipped"])
        qty_received = _as_decimal(item_in.get("qty_received", qty_shipped))
        db.add(
            ShipmentItem(
                shipment_id=shipment.id,
                po_item_id=po_item.id,
                line_no=idx,
                item_name=po_item.item_name,
                qty_shipped=qty_shipped,
                qty_received=qty_received,
                unit_price=po_item.unit_price,
            )
        )
        po_item.qty_received = (po_item.qty_received or Decimal("0")) + qty_received

    total_received = sum((i.qty_received for i in po.items), start=Decimal("0"))
    po.qty_received = total_received
    total_qty = sum((i.qty for i in po.items), start=Decimal("0"))
    if total_received >= total_qty and total_qty > 0:
        po.status = POStatus.FULLY_RECEIVED.value
    elif total_received > 0:
        po.status = POStatus.PARTIALLY_RECEIVED.value

    await _audit_write(
        db,
        actor,
        "shipment.created",
        "shipment",
        str(shipment.id),
        meta={"po_id": str(po_id), "batch_no": batch_no},
    )
    await db.commit()
    result = await db.execute(
        select(Shipment).where(Shipment.id == shipment.id).options(selectinload(Shipment.items))
    )
    return result.scalar_one()


async def list_shipments(db: AsyncSession, po_id: UUID | None = None) -> list[Shipment]:
    stmt = (
        select(Shipment).options(selectinload(Shipment.items)).order_by(Shipment.created_at.desc())
    )
    if po_id:
        stmt = stmt.where(Shipment.po_id == po_id)
    return list((await db.execute(stmt)).scalars().all())


async def record_serial_numbers(
    db: AsyncSession,
    actor: User,
    shipment_item_id: UUID,
    serials: list[dict],
) -> list[SerialNumberEntry]:
    entries = []
    for s in serials:
        entry = SerialNumberEntry(
            shipment_item_id=shipment_item_id,
            serial_number=s["serial_number"],
            manufacturer=s.get("manufacturer"),
            model_number=s.get("model_number"),
            warranty_expiry=s.get("warranty_expiry"),
        )
        db.add(entry)
        entries.append(entry)
    await _audit_write(
        db,
        actor,
        "serials.recorded",
        "shipment_item",
        str(shipment_item_id),
        meta={"count": len(entries)},
    )
    await db.commit()
    for e in entries:
        await db.refresh(e)
    return entries


async def create_payment(
    db: AsyncSession,
    actor: User,
    po_id: UUID,
    amount: Decimal,
    due_date=None,
    payment_date=None,
    payment_method: str = "bank_transfer",
    transaction_ref: str | None = None,
    notes: str | None = None,
) -> PaymentRecord:
    po = await _load_po(db, po_id)
    if po is None:
        raise HTTPException(404, "po.not_found")

    existing_count = (
        await db.execute(select(func.count(PaymentRecord.id)).where(PaymentRecord.po_id == po_id))
    ).scalar_one() or 0
    installment_no = existing_count + 1
    payment_number = f"{po.po_number}-P{installment_no:02d}"

    status = PaymentStatus.CONFIRMED.value if payment_date else PaymentStatus.PENDING.value
    record = PaymentRecord(
        payment_number=payment_number,
        po_id=po_id,
        installment_no=installment_no,
        amount=_as_decimal(amount),
        currency=po.currency,
        due_date=due_date,
        payment_date=payment_date,
        payment_method=payment_method,
        transaction_ref=transaction_ref,
        status=status,
        notes=notes,
    )
    db.add(record)

    if status == PaymentStatus.CONFIRMED.value:
        po.amount_paid = (po.amount_paid or Decimal("0")) + _as_decimal(amount)

    await _audit_write(
        db,
        actor,
        "payment.created",
        "payment_record",
        str(record.id) or "",
        meta={"po_id": str(po_id), "amount": str(amount), "status": status},
    )
    await db.commit()
    await db.refresh(record)
    return record


async def confirm_payment(
    db: AsyncSession,
    actor: User,
    payment_id: UUID,
    payment_date=None,
    transaction_ref: str | None = None,
) -> PaymentRecord:
    record = (
        await db.execute(select(PaymentRecord).where(PaymentRecord.id == payment_id))
    ).scalar_one_or_none()
    if record is None:
        raise HTTPException(404, "payment.not_found")
    if record.status == PaymentStatus.CONFIRMED.value:
        return record
    record.status = PaymentStatus.CONFIRMED.value
    record.payment_date = payment_date or datetime.now(UTC).date()
    if transaction_ref:
        record.transaction_ref = transaction_ref
    po = await _load_po(db, record.po_id)
    if po:
        po.amount_paid = (po.amount_paid or Decimal("0")) + record.amount
    await _audit_write(db, actor, "payment.confirmed", "payment_record", str(record.id))
    await db.commit()
    await db.refresh(record)
    return record


async def list_payments(db: AsyncSession, po_id: UUID | None = None) -> list[PaymentRecord]:
    stmt = select(PaymentRecord).order_by(PaymentRecord.created_at.desc())
    if po_id:
        stmt = stmt.where(PaymentRecord.po_id == po_id)
    return list((await db.execute(stmt)).scalars().all())


async def create_invoice(
    db: AsyncSession,
    actor: User,
    supplier_id: UUID,
    invoice_number: str,
    invoice_date,
    lines_in: list[dict],
    tax_number: str | None = None,
    due_date=None,
    notes: str | None = None,
    attachment_document_ids: list[UUID] | None = None,
) -> tuple[Invoice, list[dict]]:
    if not attachment_document_ids:
        raise HTTPException(422, "invoice.attachments_required")

    attach_rows = (
        (await db.execute(select(Document).where(Document.id.in_(attachment_document_ids))))
        .scalars()
        .all()
    )
    if len(attach_rows) != len(set(attachment_document_ids)):
        raise HTTPException(404, "invoice.attachment_document_not_found")

    supplier = (
        await db.execute(select(Supplier).where(Supplier.id == supplier_id))
    ).scalar_one_or_none()
    if supplier is None:
        raise HTTPException(404, "supplier.not_found")

    year = datetime.now(UTC).year
    prefix = f"INV-{year}-"
    n = (
        await db.execute(
            select(func.count(Invoice.id)).where(Invoice.internal_number.startswith(prefix))
        )
    ).scalar_one() or 0
    internal_number = f"{prefix}{n + 1:04d}"

    po_item_ids = {line.get("po_item_id") for line in lines_in if line.get("po_item_id")}
    po_items_map: dict[str, POItem] = {}
    currency = "CNY"
    if po_item_ids:
        po_items = (
            (await db.execute(select(POItem).where(POItem.id.in_(po_item_ids)))).scalars().all()
        )
        po_items_map = {str(i.id): i for i in po_items}
        if po_items:
            first_po = (
                await db.execute(select(PurchaseOrder).where(PurchaseOrder.id == po_items[0].po_id))
            ).scalar_one_or_none()
            if first_po:
                currency = first_po.currency

    subtotal = Decimal("0")
    total_tax = Decimal("0")
    validations: list[dict] = []
    touched_po_ids: set[UUID] = set()

    for idx, line_in in enumerate(lines_in, start=1):
        qty = _as_decimal(line_in["qty"])
        unit_price = _as_decimal(line_in["unit_price"])
        line_subtotal = (qty * unit_price).quantize(Decimal("0.0001"))
        line_tax = _as_decimal(line_in.get("tax_amount", 0)).quantize(Decimal("0.0001"))
        subtotal += line_subtotal
        total_tax += line_tax
        line_type = line_in.get("line_type", "product")

        po_item_id = line_in.get("po_item_id")
        po_item = po_items_map.get(str(po_item_id)) if po_item_id else None

        validation = {
            "line_no": idx,
            "po_item_id": po_item_id,
            "invoiced_subtotal": line_subtotal,
            "po_remaining": None,
            "overage": Decimal("0"),
            "severity": "ok",
            "message": None,
        }
        if line_type == "product" and po_item:
            po_line_subtotal = (po_item.qty * po_item.unit_price).quantize(Decimal("0.0001"))
            already_invoiced = (po_item.qty_invoiced or Decimal("0")) * po_item.unit_price
            po_remaining = po_line_subtotal - already_invoiced
            validation["po_remaining"] = po_remaining
            overage = line_subtotal - po_remaining
            if overage > Decimal("0.01"):
                validation["overage"] = overage
                validation["severity"] = "warn"
                validation["message"] = "exceeds_po_remaining"
        elif line_type == "product" and po_item_id is None:
            validation["severity"] = "warn"
            validation["message"] = "product_line_without_po_item"
        validations.append(validation)

    total = subtotal + total_tax

    is_matched = all(
        v["severity"] == "ok"
        for v in validations
        if v.get("po_item_id")
        or lines_in[v["line_no"] - 1].get("line_type", "product") == "product"
    )
    initial_status = (
        InvoiceStatus.MATCHED.value if is_matched else InvoiceStatus.PENDING_MATCH.value
    )

    invoice = Invoice(
        internal_number=internal_number,
        invoice_number=invoice_number,
        supplier_id=supplier_id,
        invoice_date=invoice_date,
        due_date=due_date,
        subtotal=subtotal,
        tax_amount=total_tax,
        total_amount=total,
        currency=currency,
        tax_number=tax_number,
        status=initial_status,
        notes=notes,
        is_fully_matched=is_matched,
    )
    db.add(invoice)
    await db.flush()

    for idx, line_in in enumerate(lines_in, start=1):
        qty = _as_decimal(line_in["qty"])
        unit_price = _as_decimal(line_in["unit_price"])
        line_subtotal = (qty * unit_price).quantize(Decimal("0.0001"))
        line_tax = _as_decimal(line_in.get("tax_amount", 0)).quantize(Decimal("0.0001"))
        po_item_id = line_in.get("po_item_id")
        po_item = po_items_map.get(str(po_item_id)) if po_item_id else None
        line_type = line_in.get("line_type", "product")

        db.add(
            InvoiceLine(
                invoice_id=invoice.id,
                po_item_id=po_item.id if po_item else None,
                line_type=line_type,
                line_no=idx,
                item_name=line_in["item_name"],
                qty=qty,
                unit_price=unit_price,
                subtotal=line_subtotal,
                tax_amount=line_tax,
            )
        )

        if po_item and line_type == "product":
            po_item.qty_invoiced = (po_item.qty_invoiced or Decimal("0")) + qty
            touched_po_ids.add(po_item.po_id)

    for idx, doc_id in enumerate(attachment_document_ids):
        db.add(
            InvoiceDocument(
                invoice_id=invoice.id,
                document_id=doc_id,
                role="original" if idx == 0 else "attachment",
                display_order=idx,
            )
        )

    for po_id in touched_po_ids:
        po = (
            await db.execute(
                select(PurchaseOrder)
                .where(PurchaseOrder.id == po_id)
                .options(selectinload(PurchaseOrder.items))
            )
        ).scalar_one()
        po.amount_invoiced = sum(
            ((i.qty_invoiced or Decimal("0")) * i.unit_price for i in po.items),
            start=Decimal("0"),
        ).quantize(Decimal("0.0001"))

    await _audit_write(
        db,
        actor,
        "invoice.created",
        "invoice",
        str(invoice.id),
        meta={
            "internal_number": internal_number,
            "subtotal": str(subtotal),
            "tax": str(total_tax),
            "total": str(total),
            "po_ids": [str(p) for p in touched_po_ids],
        },
    )
    await db.commit()

    loaded = (
        await db.execute(
            select(Invoice)
            .where(Invoice.id == invoice.id)
            .options(
                selectinload(Invoice.lines),
                selectinload(Invoice.attachments).selectinload(InvoiceDocument.document),
            )
        )
    ).scalar_one()
    return loaded, validations


async def list_invoices(db: AsyncSession, po_item_ids: list[UUID] | None = None) -> list[Invoice]:
    stmt = select(Invoice).order_by(Invoice.created_at.desc())
    if po_item_ids:
        sub = select(InvoiceLine.invoice_id).where(InvoiceLine.po_item_id.in_(po_item_ids))
        stmt = stmt.where(Invoice.id.in_(sub))
    return list((await db.execute(stmt)).scalars().all())


async def list_invoices_for_po(db: AsyncSession, po_id: UUID) -> list[Invoice]:
    po = await _load_po(db, po_id)
    if po is None:
        return []
    item_ids = [i.id for i in po.items]
    if not item_ids:
        return []
    return await list_invoices(db, item_ids)


async def po_progress(db: AsyncSession, po_id: UUID) -> dict:
    po = await _load_po(db, po_id)
    if po is None:
        raise HTTPException(404, "po.not_found")
    total_qty = sum((i.qty for i in po.items), start=Decimal("0"))
    qty_received = sum((i.qty_received or Decimal("0") for i in po.items), start=Decimal("0"))
    qty_invoiced = sum((i.qty_invoiced or Decimal("0") for i in po.items), start=Decimal("0"))
    amount_invoiced_subtotal = sum(
        ((i.qty_invoiced or Decimal("0")) * i.unit_price for i in po.items),
        start=Decimal("0"),
    )

    def pct(n: Decimal, d: Decimal) -> float:
        return float((n / d * Decimal("100")).quantize(Decimal("0.01"))) if d > 0 else 0.0

    return {
        "po_id": str(po.id),
        "po_number": po.po_number,
        "total_amount": str(po.total_amount),
        "amount_paid": str(po.amount_paid),
        "amount_invoiced": str(amount_invoiced_subtotal),
        "total_qty": str(total_qty),
        "qty_received": str(qty_received),
        "qty_invoiced": str(qty_invoiced),
        "pct_received": pct(qty_received, total_qty),
        "pct_invoiced": pct(amount_invoiced_subtotal, po.total_amount),
        "pct_paid": pct(po.amount_paid, po.total_amount),
    }
