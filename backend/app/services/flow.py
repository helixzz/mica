from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, or_, select
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
    PaymentSchedule,
    PaymentStatus,
    POContractLink,
    POItem,
    POStatus,
    PurchaseOrder,
    ScheduleItemStatus,
    SerialNumberEntry,
    Shipment,
    ShipmentDocument,
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


async def suggest_contract_number(db: AsyncSession) -> str:
    now = datetime.now(UTC)
    prefix = f"ACME{now.year:04d}{now.month:02d}{now.day:02d}"
    max_suffix = (
        await db.execute(
            select(func.max(Contract.contract_number)).where(
                Contract.contract_number.like(f"{prefix}%")
            )
        )
    ).scalar_one_or_none()
    next_seq = 1
    if max_suffix and len(max_suffix) == len(prefix) + 3:
        try:
            next_seq = int(max_suffix[-3:]) + 1
        except ValueError:
            next_seq = 1
    return f"{prefix}{next_seq:03d}"


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
    contract_number: str | None = None,
) -> Contract:
    po = await _load_po(db, po_id)
    if po is None:
        raise HTTPException(404, "po.not_found")

    if contract_number:
        number = contract_number.strip()
        if not number:
            raise HTTPException(400, "contract.number_required")
        collision = (
            await db.execute(
                select(func.count(Contract.id)).where(Contract.contract_number == number)
            )
        ).scalar_one() or 0
        if collision > 0:
            raise HTTPException(409, "contract.number_duplicate")
    else:
        number = await suggest_contract_number(db)

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
    db.add(POContractLink(po_id=po.id, contract_id=contract.id))
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
    stmt = (
        select(Contract)
        .order_by(Contract.created_at.desc())
        .options(selectinload(Contract.po), selectinload(Contract.supplier))
    )
    if po_id:
        linked_ids = (
            (
                await db.execute(
                    select(POContractLink.contract_id).where(POContractLink.po_id == po_id)
                )
            )
            .scalars()
            .all()
        )
        if linked_ids:
            stmt = stmt.where(or_(Contract.po_id == po_id, Contract.id.in_(linked_ids)))
        else:
            stmt = stmt.where(Contract.po_id == po_id)
    return list((await db.execute(stmt)).scalars().all())


async def list_linked_pos(db: AsyncSession, contract_id: UUID) -> list[PurchaseOrder]:
    contract = (
        await db.execute(select(Contract).where(Contract.id == contract_id))
    ).scalar_one_or_none()
    if contract is None:
        raise HTTPException(404, "contract.not_found")

    link_ids = (
        (
            await db.execute(
                select(POContractLink.po_id).where(POContractLink.contract_id == contract_id)
            )
        )
        .scalars()
        .all()
    )
    po_ids: set[UUID] = set(link_ids)
    if contract.po_id:
        po_ids.add(contract.po_id)
    if not po_ids:
        return []
    rows = (
        (
            await db.execute(
                select(PurchaseOrder)
                .where(PurchaseOrder.id.in_(po_ids))
                .order_by(PurchaseOrder.po_number)
            )
        )
        .scalars()
        .all()
    )
    return list(rows)


async def link_po_contract(
    db: AsyncSession,
    actor: User,
    po_id: UUID,
    contract_id: UUID,
) -> POContractLink:
    po = await _load_po(db, po_id)
    if po is None:
        raise HTTPException(404, "po.not_found")
    contract = await _load_contract(db, contract_id)

    existing = (
        await db.execute(
            select(POContractLink).where(
                POContractLink.po_id == po_id,
                POContractLink.contract_id == contract_id,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing

    primary_po = await _load_po(db, contract.po_id)
    if primary_po is None:
        raise HTTPException(404, "po.not_found")
    if po.supplier_id != contract.supplier_id:
        raise HTTPException(409, "po_contract_link.supplier_mismatch")
    if po.company_id != primary_po.company_id:
        raise HTTPException(409, "po_contract_link.company_mismatch")
    if po.currency != contract.currency:
        raise HTTPException(409, "po_contract_link.currency_mismatch")

    link = POContractLink(po_id=po_id, contract_id=contract_id)
    db.add(link)
    await _audit_write(
        db,
        actor,
        "po_contract.linked",
        "contract",
        str(contract.id),
        meta={"po_id": str(po_id), "po_number": po.po_number},
    )
    await db.commit()
    return link


async def unlink_po_contract(
    db: AsyncSession,
    actor: User,
    po_id: UUID,
    contract_id: UUID,
) -> None:
    po = await _load_po(db, po_id)
    if po is None:
        raise HTTPException(404, "po.not_found")
    contract = await _load_contract(db, contract_id)

    link = (
        await db.execute(
            select(POContractLink).where(
                POContractLink.po_id == po_id,
                POContractLink.contract_id == contract_id,
            )
        )
    ).scalar_one_or_none()
    if link is None:
        raise HTTPException(404, "po_contract_link.not_found")

    if contract.po_id == po_id:
        raise HTTPException(409, "po_contract_link.cannot_unlink_primary")

    other_links = (
        await db.execute(
            select(func.count(POContractLink.po_id)).where(
                POContractLink.contract_id == contract_id,
                POContractLink.po_id != po_id,
            )
        )
    ).scalar_one()
    is_primary_po = contract.po_id == po_id
    if other_links == 0 and is_primary_po:
        raise HTTPException(409, "po_contract_link.cannot_remove_last")

    has_payments = (
        await db.execute(
            select(func.count(PaymentRecord.id)).where(
                PaymentRecord.contract_id == contract_id,
                PaymentRecord.po_id == po_id,
            )
        )
    ).scalar_one()
    if has_payments > 0:
        raise HTTPException(409, "po_contract_link.has_payments")

    await db.delete(link)
    await _audit_write(
        db,
        actor,
        "po_contract.unlinked",
        "contract",
        str(contract.id),
        meta={"po_id": str(po_id), "po_number": po.po_number},
    )
    await db.commit()


async def get_contract(db: AsyncSession, contract_id: UUID) -> Contract:
    stmt = (
        select(Contract)
        .where(Contract.id == contract_id)
        .options(selectinload(Contract.po), selectinload(Contract.supplier))
    )
    contract = (await db.execute(stmt)).scalar_one_or_none()
    if contract is None:
        raise HTTPException(404, "contract.not_found")
    return contract


_ALLOWED_CONTRACT_EDIT_FIELDS: frozenset[str] = frozenset(
    {"title", "total_amount", "signed_date", "effective_date", "expiry_date", "notes"}
)

# Terminal statuses block further edits/transitions — once a contract is
# superseded/terminated/expired, its terms are frozen for the audit trail.
_CONTRACT_TERMINAL_STATUSES: frozenset[str] = frozenset({"superseded", "terminated", "expired"})

_CONTRACT_STATUS_TRANSITIONS: dict[str, frozenset[str]] = {
    "active": frozenset({"superseded", "terminated", "expired"}),
}


async def _load_contract(db: AsyncSession, contract_id: UUID) -> Contract:
    contract = (
        await db.execute(select(Contract).where(Contract.id == contract_id))
    ).scalar_one_or_none()
    if contract is None:
        raise HTTPException(404, "contract.not_found")
    return contract


async def update_contract(
    db: AsyncSession,
    actor: User,
    contract_id: UUID,
    updates: dict,
) -> Contract:
    contract = await _load_contract(db, contract_id)
    if contract.status in _CONTRACT_TERMINAL_STATUSES:
        raise HTTPException(409, "contract.not_editable_in_status")

    changed: dict[str, object] = {}
    for field in _ALLOWED_CONTRACT_EDIT_FIELDS:
        if field not in updates:
            continue
        value = updates[field]
        if field == "total_amount" and value is not None:
            value = _as_decimal(value)
        if getattr(contract, field) != value:
            setattr(contract, field, value)
            changed[field] = value

    if not changed:
        return contract

    contract.current_version = (contract.current_version or 1) + 1
    await db.flush()
    await contract_svc.create_contract_version(
        db,
        contract=contract,
        actor=actor,
        change_type="updated",
        change_reason=updates.get("change_reason"),
    )
    await _audit_write(
        db,
        actor,
        "contract.updated",
        "contract",
        str(contract.id),
        meta={"fields": list(changed.keys())},
    )
    await db.commit()
    await db.refresh(contract)
    return contract


async def transition_contract_status(
    db: AsyncSession,
    actor: User,
    contract_id: UUID,
    new_status: str,
    reason: str | None = None,
) -> Contract:
    contract = await _load_contract(db, contract_id)
    current = contract.status or "active"
    allowed = _CONTRACT_STATUS_TRANSITIONS.get(current, frozenset())
    if new_status not in allowed:
        raise HTTPException(409, "contract.invalid_status_transition")

    contract.status = new_status
    contract.current_version = (contract.current_version or 1) + 1
    await db.flush()
    await contract_svc.create_contract_version(
        db,
        contract=contract,
        actor=actor,
        change_type=new_status,
        change_reason=reason,
    )
    await _audit_write(
        db,
        actor,
        "contract.status_changed",
        "contract",
        str(contract.id),
        meta={"from": current, "to": new_status, "reason": reason},
    )
    await db.commit()
    await db.refresh(contract)
    return contract


async def delete_contract(
    db: AsyncSession,
    actor: User,
    contract_id: UUID,
) -> None:
    contract = await _load_contract(db, contract_id)
    paid = (
        await db.execute(
            select(func.count(PaymentRecord.id)).where(
                PaymentRecord.schedule_item_id.in_(
                    select(PaymentSchedule.id).where(PaymentSchedule.contract_id == contract.id)
                ),
                PaymentRecord.status == PaymentStatus.CONFIRMED.value,
            )
        )
    ).scalar_one() or 0
    if paid > 0:
        raise HTTPException(409, "contract.cannot_delete_with_paid_schedule")

    number = contract.contract_number
    await db.delete(contract)
    await _audit_write(
        db,
        actor,
        "contract.deleted",
        "contract",
        str(contract_id),
        meta={"contract_number": number},
    )
    await db.commit()


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


async def update_shipment(
    db: AsyncSession, actor: User, shipment_id: UUID, payload: object
) -> Shipment:
    from app.schemas import ShipmentUpdate

    shipment = await db.get(Shipment, shipment_id)
    if shipment is None:
        raise HTTPException(404, "shipment.not_found")
    assert isinstance(payload, ShipmentUpdate)
    changes: dict[str, object] = {}
    for field_name in payload.model_fields_set:
        new_val = getattr(payload, field_name)
        old_val = getattr(shipment, field_name)
        if old_val != new_val:
            changes[field_name] = {"old": str(old_val), "new": str(new_val)}
            setattr(shipment, field_name, new_val)
    if changes:
        await _audit_write(db, actor, "shipment.updated", "shipment", str(shipment_id), changes)
        await db.commit()
    result = await db.execute(
        select(Shipment).where(Shipment.id == shipment_id).options(selectinload(Shipment.items))
    )
    return result.scalar_one()


async def delete_shipment(db: AsyncSession, actor: User, shipment_id: UUID) -> None:
    shipment = await db.get(Shipment, shipment_id)
    if shipment is None:
        raise HTTPException(404, "shipment.not_found")
    await _audit_write(
        db,
        actor,
        "shipment.deleted",
        "shipment",
        str(shipment_id),
        {"shipment_number": shipment.shipment_number},
    )
    await db.delete(shipment)
    await db.commit()


async def attach_document_to_shipment(
    db: AsyncSession, actor: User, shipment_id: UUID, document_id: UUID, role: str = "attachment"
) -> ShipmentDocument:
    shipment = await db.get(Shipment, shipment_id)
    if shipment is None:
        raise HTTPException(404, "shipment.not_found")
    doc = await db.get(Document, document_id)
    if doc is None:
        raise HTTPException(404, "document.not_found")
    link = ShipmentDocument(
        shipment_id=shipment_id,
        document_id=document_id,
        role=role,
    )
    db.add(link)
    await _audit_write(
        db,
        actor,
        "shipment.document.attached",
        "shipment",
        str(shipment_id),
        {"document_id": str(document_id), "filename": doc.original_filename},
    )
    await db.commit()
    return link


async def list_shipment_documents(db: AsyncSession, shipment_id: UUID) -> list[dict]:
    stmt = (
        select(ShipmentDocument, Document)
        .join(Document, ShipmentDocument.document_id == Document.id)
        .where(ShipmentDocument.shipment_id == shipment_id)
        .order_by(ShipmentDocument.display_order)
    )
    rows = (await db.execute(stmt)).all()
    return [
        {
            "document_id": str(sd.document_id),
            "role": sd.role,
            "original_filename": d.original_filename,
            "content_type": d.content_type,
            "file_size": d.file_size,
            "created_at": sd.created_at.isoformat() if sd.created_at else None,
        }
        for sd, d in rows
    ]


async def remove_shipment_document(db: AsyncSession, shipment_id: UUID, document_id: UUID) -> None:
    link = await db.get(ShipmentDocument, (shipment_id, document_id))
    if link is None:
        raise HTTPException(404, "shipment_document.not_found")
    await db.delete(link)
    await db.commit()


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
    contract_id: UUID,
    schedule_item_id: UUID | None = None,
    due_date=None,
    payment_date=None,
    payment_method: str = "bank_transfer",
    transaction_ref: str | None = None,
    notes: str | None = None,
) -> PaymentRecord:
    po = await _load_po(db, po_id)
    if po is None:
        raise HTTPException(404, "po.not_found")

    contract = (
        await db.execute(select(Contract).where(Contract.id == contract_id))
    ).scalar_one_or_none()
    if contract is None:
        raise HTTPException(404, "contract.not_found")
    if contract.po_id != po_id:
        link_exists = (
            await db.execute(
                select(func.count(POContractLink.po_id)).where(
                    POContractLink.po_id == po_id,
                    POContractLink.contract_id == contract_id,
                )
            )
        ).scalar_one()
        if not link_exists:
            raise HTTPException(409, "payment.contract_po_mismatch")

    if schedule_item_id is not None:
        schedule_item = (
            await db.execute(select(PaymentSchedule).where(PaymentSchedule.id == schedule_item_id))
        ).scalar_one_or_none()
        if schedule_item is None:
            raise HTTPException(404, "schedule_item.not_found")
        if schedule_item.contract_id is not None and contract.po_id != po_id:
            raise HTTPException(409, "payment.schedule_requires_primary_po")
        if schedule_item.contract_id != contract_id and schedule_item.po_id != po_id:
            raise HTTPException(409, "payment.schedule_parent_mismatch")

    existing_count = (
        await db.execute(select(func.count(PaymentRecord.id)).where(PaymentRecord.po_id == po_id))
    ).scalar_one() or 0
    installment_no = existing_count + 1
    payment_number = f"{po.po_number}-P{installment_no:02d}"

    status = PaymentStatus.CONFIRMED.value if payment_date else PaymentStatus.PENDING.value
    record = PaymentRecord(
        payment_number=payment_number,
        po_id=po_id,
        contract_id=contract_id,
        schedule_item_id=schedule_item_id,
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
    await db.flush()

    if status == PaymentStatus.CONFIRMED.value:
        po.amount_paid = (po.amount_paid or Decimal("0")) + _as_decimal(amount)

    if schedule_item_id is not None and status == PaymentStatus.CONFIRMED.value:
        schedule_item = await db.get(PaymentSchedule, schedule_item_id)
        if schedule_item is not None and schedule_item.status != ScheduleItemStatus.PAID.value:
            schedule_item.actual_amount = _as_decimal(amount)
            schedule_item.actual_date = payment_date
            schedule_item.payment_record_id = record.id
            schedule_item.status = ScheduleItemStatus.PAID.value

    await _audit_write(
        db,
        actor,
        "payment.created",
        "payment_record",
        str(record.id) or "",
        meta={
            "po_id": str(po_id),
            "contract_id": str(contract_id),
            "schedule_item_id": str(schedule_item_id) if schedule_item_id else None,
            "amount": str(amount),
            "status": status,
        },
    )
    await db.commit()
    await db.refresh(record)
    return record


async def update_payment(
    db: AsyncSession,
    actor: User,
    payment_id: UUID,
    updates: dict,
) -> PaymentRecord:
    record = (
        await db.execute(select(PaymentRecord).where(PaymentRecord.id == payment_id))
    ).scalar_one_or_none()
    if record is None:
        raise HTTPException(404, "payment.not_found")

    changes: dict[str, object] = {}

    new_contract_id = record.contract_id
    if "contract_id" in updates:
        candidate = updates["contract_id"]
        if candidate is None:
            raise HTTPException(400, "payment.contract_required")
        if candidate != record.contract_id:
            contract = (
                await db.execute(select(Contract).where(Contract.id == candidate))
            ).scalar_one_or_none()
            if contract is None:
                raise HTTPException(404, "contract.not_found")
            if contract.po_id != record.po_id:
                link_exists = (
                    await db.execute(
                        select(func.count(POContractLink.po_id)).where(
                            POContractLink.po_id == record.po_id,
                            POContractLink.contract_id == candidate,
                        )
                    )
                ).scalar_one()
                if not link_exists:
                    raise HTTPException(409, "payment.contract_po_mismatch")
            changes["contract_id"] = {
                "from": str(record.contract_id) if record.contract_id else None,
                "to": str(candidate),
            }
            record.contract_id = candidate
            new_contract_id = candidate

    if "schedule_item_id" in updates:
        candidate = updates["schedule_item_id"]
        if candidate != record.schedule_item_id:
            if record.schedule_item_id is not None:
                old_item = await db.get(PaymentSchedule, record.schedule_item_id)
                if old_item is not None and old_item.payment_record_id == record.id:
                    old_item.payment_record_id = None
                    old_item.actual_amount = None
                    old_item.actual_date = None
                    old_item.status = ScheduleItemStatus.PLANNED.value

            if candidate is not None:
                new_item = (
                    await db.execute(select(PaymentSchedule).where(PaymentSchedule.id == candidate))
                ).scalar_one_or_none()
                if new_item is None:
                    raise HTTPException(404, "schedule_item.not_found")
                if new_item.contract_id is not None:
                    contract = (
                        await db.execute(select(Contract).where(Contract.id == new_contract_id))
                    ).scalar_one_or_none()
                    if contract is None:
                        raise HTTPException(404, "contract.not_found")
                    if contract.po_id != record.po_id:
                        raise HTTPException(409, "payment.schedule_requires_primary_po")
                if new_item.contract_id != new_contract_id and new_item.po_id != record.po_id:
                    raise HTTPException(409, "payment.schedule_parent_mismatch")
                if record.status == PaymentStatus.CONFIRMED.value:
                    new_item.actual_amount = record.amount
                    new_item.actual_date = record.payment_date
                    new_item.payment_record_id = record.id
                    new_item.status = ScheduleItemStatus.PAID.value

            changes["schedule_item_id"] = {
                "from": str(record.schedule_item_id) if record.schedule_item_id else None,
                "to": str(candidate) if candidate else None,
            }
            record.schedule_item_id = candidate

    if "amount" in updates and updates["amount"] is not None:
        new = _as_decimal(updates["amount"])
        if new != record.amount:
            old = record.amount
            if record.status == PaymentStatus.CONFIRMED.value:
                po = await _load_po(db, record.po_id)
                if po is not None:
                    po.amount_paid = (po.amount_paid or Decimal("0")) - old + new
                if record.schedule_item_id is not None:
                    schedule_item = await db.get(PaymentSchedule, record.schedule_item_id)
                    if schedule_item is not None:
                        schedule_item.actual_amount = new
            record.amount = new
            changes["amount"] = {"from": str(old), "to": str(new)}

    if "due_date" in updates and updates["due_date"] != record.due_date:
        changes["due_date"] = {"from": str(record.due_date), "to": str(updates["due_date"])}
        record.due_date = updates["due_date"]

    if "payment_date" in updates and updates["payment_date"] != record.payment_date:
        new_payment_date = updates["payment_date"]
        changes["payment_date"] = {
            "from": str(record.payment_date),
            "to": str(new_payment_date),
        }
        record.payment_date = new_payment_date
        if record.schedule_item_id is not None:
            schedule_item = await db.get(PaymentSchedule, record.schedule_item_id)
            if schedule_item is not None:
                schedule_item.actual_date = new_payment_date

    if "payment_method" in updates and updates["payment_method"] != record.payment_method:
        changes["payment_method"] = {
            "from": record.payment_method,
            "to": updates["payment_method"],
        }
        record.payment_method = updates["payment_method"]

    if "transaction_ref" in updates and updates["transaction_ref"] != record.transaction_ref:
        changes["transaction_ref"] = {
            "from": record.transaction_ref,
            "to": updates["transaction_ref"],
        }
        record.transaction_ref = updates["transaction_ref"]

    if "notes" in updates and updates["notes"] != record.notes:
        changes["notes"] = {"from": record.notes, "to": updates["notes"]}
        record.notes = updates["notes"]

    if not changes:
        return record

    await _audit_write(
        db,
        actor,
        "payment.updated",
        "payment_record",
        str(record.id),
        meta={"changes": changes},
    )
    await db.commit()
    await db.refresh(record)
    return record


async def delete_payment(db: AsyncSession, actor: User, payment_id: UUID) -> None:
    record = (
        await db.execute(select(PaymentRecord).where(PaymentRecord.id == payment_id))
    ).scalar_one_or_none()
    if record is None:
        raise HTTPException(404, "payment.not_found")
    if record.status == PaymentStatus.CONFIRMED.value:
        raise HTTPException(409, "payment.cannot_delete_confirmed")

    if record.schedule_item_id is not None:
        schedule_item = await db.get(PaymentSchedule, record.schedule_item_id)
        if schedule_item is not None and schedule_item.payment_record_id == record.id:
            schedule_item.payment_record_id = None
            schedule_item.actual_amount = None
            schedule_item.actual_date = None
            schedule_item.status = ScheduleItemStatus.PLANNED.value

    payment_number = record.payment_number
    await db.delete(record)
    await _audit_write(
        db,
        actor,
        "payment.deleted",
        "payment_record",
        str(payment_id),
        meta={"payment_number": payment_number},
    )
    await db.commit()


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
