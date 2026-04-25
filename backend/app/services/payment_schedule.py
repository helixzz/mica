from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import new_uuid
from app.models import (
    Contract,
    Invoice,
    PaymentRecord,
    PaymentSchedule,
    PaymentStatus,
    POContractLink,
    PurchaseOrder,
    ScheduleItemStatus,
)


@dataclass(frozen=True)
class _Parent:
    kind: str
    id: UUID
    number: str
    currency: str
    total_amount: Decimal
    po_id_for_payment: UUID


async def _resolve_parent(
    db: AsyncSession,
    *,
    contract_id: UUID | None = None,
    po_id: UUID | None = None,
) -> _Parent:
    if (contract_id is None) == (po_id is None):
        raise HTTPException(400, "payment_schedule.parent_required")

    if contract_id is not None:
        contract = (
            await db.execute(
                select(Contract)
                .where(Contract.id == contract_id)
                .options(selectinload(Contract.schedules))
            )
        ).scalar_one_or_none()
        if contract is None:
            raise HTTPException(404, "contract.not_found")
        return _Parent(
            kind="contract",
            id=contract.id,
            number=contract.contract_number,
            currency=contract.currency,
            total_amount=contract.total_amount,
            po_id_for_payment=contract.po_id,
        )

    assert po_id is not None
    po = (
        await db.execute(
            select(PurchaseOrder)
            .where(PurchaseOrder.id == po_id)
            .options(selectinload(PurchaseOrder.payment_schedules))
        )
    ).scalar_one_or_none()
    if po is None:
        raise HTTPException(404, "po.not_found")
    return _Parent(
        kind="po",
        id=po.id,
        number=po.po_number,
        currency=po.currency,
        total_amount=po.total_amount,
        po_id_for_payment=po.id,
    )


def _parent_filter(parent: _Parent):
    if parent.kind == "contract":
        return PaymentSchedule.contract_id == parent.id
    return PaymentSchedule.po_id == parent.id


async def _list_schedules_for_summary(db: AsyncSession, parent: _Parent) -> list[PaymentSchedule]:
    """Return every PaymentSchedule that belongs to the parent.

    For PO parents this is the union of (a) schedules attached directly to
    the PO and (b) schedules attached to any contract linked to that PO,
    either via ``Contract.po_id`` (legacy single-PO) or ``po_contract_links``
    (M:N introduced in v0.9.15). Without this union the PO detail page
    misses every payment installment that lives on its contracts.
    """
    if parent.kind == "contract":
        result = await db.execute(
            select(PaymentSchedule)
            .where(PaymentSchedule.contract_id == parent.id)
            .order_by(PaymentSchedule.installment_no)
        )
        return list(result.scalars().all())

    linked_contract_ids = set(
        (await db.execute(select(Contract.id).where(Contract.po_id == parent.id))).scalars().all()
    )
    linked_contract_ids.update(
        (
            await db.execute(
                select(POContractLink.contract_id).where(POContractLink.po_id == parent.id)
            )
        )
        .scalars()
        .all()
    )

    conditions = [PaymentSchedule.po_id == parent.id]
    if linked_contract_ids:
        conditions.append(PaymentSchedule.contract_id.in_(linked_contract_ids))

    from sqlalchemy import or_ as _or

    result = await db.execute(
        select(PaymentSchedule).where(_or(*conditions)).order_by(PaymentSchedule.installment_no)
    )
    return list(result.scalars().all())


async def _find_schedule_item(
    db: AsyncSession, parent: _Parent, installment_no: int
) -> PaymentSchedule | None:
    """Locate one installment within the parent's full schedule union.

    Mirrors ``_list_schedules_for_summary`` so PO-scoped writes (update /
    delete / execute) reach installments that live on a linked contract.
    Without this, v0.9.18's read-side union created a UI affordance the
    write-side endpoints couldn't honor (404 schedule_item.not_found).
    """
    items = await _list_schedules_for_summary(db, parent)
    for item in items:
        if item.installment_no == installment_no:
            return item
    return None


async def get_contract_with_schedules(db: AsyncSession, contract_id: UUID) -> Contract:
    result = await db.execute(
        select(Contract).where(Contract.id == contract_id).options(selectinload(Contract.schedules))
    )
    contract = result.scalar_one_or_none()
    if contract is None:
        raise HTTPException(404, "contract.not_found")
    return contract


async def list_schedule(
    db: AsyncSession,
    *,
    contract_id: UUID | None = None,
    po_id: UUID | None = None,
) -> list[PaymentSchedule]:
    parent = await _resolve_parent(db, contract_id=contract_id, po_id=po_id)
    result = await db.execute(
        select(PaymentSchedule)
        .where(_parent_filter(parent))
        .order_by(PaymentSchedule.installment_no)
    )
    return list(result.scalars().all())


async def build_summary_for(
    db: AsyncSession,
    *,
    contract_id: UUID | None = None,
    po_id: UUID | None = None,
) -> dict:
    parent = await _resolve_parent(db, contract_id=contract_id, po_id=po_id)
    items = await _list_schedules_for_summary(db, parent)
    planned_total = sum((s.planned_amount for s in items), Decimal("0"))
    paid_total = sum((s.actual_amount or Decimal("0") for s in items), Decimal("0"))
    return {
        "contract_total": parent.total_amount,
        "planned_total": planned_total,
        "paid_total": paid_total,
        "remaining": planned_total - paid_total,
        "total_mismatch": planned_total != parent.total_amount,
        "items": items,
    }


async def replace_schedule(
    db: AsyncSession,
    items: list[dict],
    *,
    contract_id: UUID | None = None,
    po_id: UUID | None = None,
) -> list[PaymentSchedule]:
    parent = await _resolve_parent(db, contract_id=contract_id, po_id=po_id)

    await db.execute(
        delete(PaymentSchedule).where(
            _parent_filter(parent),
            PaymentSchedule.status == ScheduleItemStatus.PLANNED.value,
        )
    )

    created: list[PaymentSchedule] = []
    for item_data in items:
        raw_date = item_data.get("planned_date")
        if isinstance(raw_date, str):
            raw_date = date.fromisoformat(raw_date)

        schedule = PaymentSchedule(
            id=new_uuid(),
            contract_id=parent.id if parent.kind == "contract" else None,
            po_id=parent.id if parent.kind == "po" else None,
            installment_no=item_data["installment_no"],
            label=item_data["label"],
            planned_amount=Decimal(str(item_data["planned_amount"])),
            planned_date=raw_date,
            trigger_type=item_data.get("trigger_type", "fixed_date"),
            trigger_description=item_data.get("trigger_description"),
            notes=item_data.get("notes"),
        )
        db.add(schedule)
        created.append(schedule)

    await db.flush()
    return created


async def update_schedule_item(
    db: AsyncSession,
    installment_no: int,
    updates: dict,
    *,
    contract_id: UUID | None = None,
    po_id: UUID | None = None,
) -> PaymentSchedule:
    parent = await _resolve_parent(db, contract_id=contract_id, po_id=po_id)
    item = await _find_schedule_item(db, parent, installment_no)
    if item is None:
        raise HTTPException(404, "schedule_item.not_found")

    for field, value in updates.items():
        if value is not None and hasattr(item, field):
            setattr(item, field, value)

    await db.flush()
    return item


async def delete_schedule_item(
    db: AsyncSession,
    installment_no: int,
    *,
    contract_id: UUID | None = None,
    po_id: UUID | None = None,
) -> None:
    parent = await _resolve_parent(db, contract_id=contract_id, po_id=po_id)
    item = await _find_schedule_item(db, parent, installment_no)
    if item is None:
        raise HTTPException(404, "schedule_item.not_found")
    if item.status in (ScheduleItemStatus.PAID.value, ScheduleItemStatus.PARTIALLY_PAID.value):
        raise HTTPException(409, "schedule_item.cannot_delete_paid")
    await db.delete(item)
    await db.flush()


async def execute_schedule_item(
    db: AsyncSession,
    installment_no: int,
    payment_method: str,
    transaction_ref: str | None,
    invoice_id: UUID | None,
    amount_override: Decimal | None,
    *,
    contract_id: UUID | None = None,
    po_id: UUID | None = None,
) -> PaymentSchedule:
    parent = await _resolve_parent(db, contract_id=contract_id, po_id=po_id)

    item = await _find_schedule_item(db, parent, installment_no)
    if item is None:
        raise HTTPException(404, "schedule_item.not_found")
    if item.status == ScheduleItemStatus.PAID.value:
        raise HTTPException(409, "schedule_item.already_paid")

    pay_amount = amount_override if amount_override is not None else item.planned_amount

    existing_count = (
        await db.execute(
            select(func.count(PaymentRecord.id)).where(
                PaymentRecord.po_id == parent.po_id_for_payment
            )
        )
    ).scalar() or 0

    payment = PaymentRecord(
        id=new_uuid(),
        payment_number=f"PAY-{parent.number}-{existing_count + 1:03d}",
        po_id=parent.po_id_for_payment,
        contract_id=item.contract_id,
        installment_no=installment_no,
        amount=pay_amount,
        currency=parent.currency,
        due_date=item.planned_date,
        payment_date=date.today(),
        payment_method=payment_method,
        transaction_ref=transaction_ref,
        status=PaymentStatus.CONFIRMED.value,
        schedule_item_id=item.id,
    )
    db.add(payment)

    item.actual_amount = pay_amount
    item.actual_date = date.today()
    item.payment_record_id = payment.id
    item.status = ScheduleItemStatus.PAID.value

    po = await db.get(PurchaseOrder, parent.po_id_for_payment)
    if po is not None:
        po.amount_paid = (po.amount_paid or Decimal("0")) + pay_amount

    if invoice_id is not None:
        invoice = await db.get(Invoice, invoice_id)
        if invoice is None:
            raise HTTPException(404, "invoice.not_found")
        item.invoice_id = invoice_id

    await db.flush()
    return item


async def link_invoice(
    db: AsyncSession,
    installment_no: int,
    invoice_id: UUID,
    *,
    contract_id: UUID | None = None,
    po_id: UUID | None = None,
) -> PaymentSchedule:
    parent = await _resolve_parent(db, contract_id=contract_id, po_id=po_id)
    item = await _find_schedule_item(db, parent, installment_no)
    if item is None:
        raise HTTPException(404, "schedule_item.not_found")

    invoice = await db.get(Invoice, invoice_id)
    if invoice is None:
        raise HTTPException(404, "invoice.not_found")

    item.invoice_id = invoice_id
    await db.flush()
    return item


def build_summary(contract: Contract, items: list[PaymentSchedule]) -> dict:
    planned_total = sum((s.planned_amount for s in items), Decimal("0"))
    paid_total = sum((s.actual_amount or Decimal("0") for s in items), Decimal("0"))
    return {
        "contract_total": contract.total_amount,
        "planned_total": planned_total,
        "paid_total": paid_total,
        "remaining": planned_total - paid_total,
        "total_mismatch": planned_total != contract.total_amount,
        "items": items,
    }


async def payment_forecast(
    db: AsyncSession,
    months: int = 6,
    *,
    anchor: date | None = None,
    past_months: int = 0,
) -> dict:
    today = date.today()
    anchor_month = (anchor or today).replace(day=1)

    start_offset = -abs(past_months)
    total = past_months + months

    month_buckets: list[dict] = []
    for i in range(total):
        offset = start_offset + i
        y = anchor_month.year + (anchor_month.month + offset - 1) // 12
        m = (anchor_month.month + offset - 1) % 12 + 1
        month_start = date(y, m, 1)
        if m == 12:
            month_end = date(y + 1, 1, 1)
        else:
            month_end = date(y, m + 1, 1)

        planned_from_schedule = select(
            func.coalesce(func.sum(PaymentSchedule.planned_amount), 0)
        ).where(
            PaymentSchedule.planned_date >= month_start,
            PaymentSchedule.planned_date < month_end,
            PaymentSchedule.status.in_(
                (ScheduleItemStatus.PLANNED.value, ScheduleItemStatus.DUE.value)
            ),
        )
        planned_from_pending_records = select(
            func.coalesce(func.sum(PaymentRecord.amount), 0)
        ).where(
            PaymentRecord.due_date >= month_start,
            PaymentRecord.due_date < month_end,
            PaymentRecord.status == PaymentStatus.PENDING.value,
        )
        planned_sched = Decimal(str((await db.execute(planned_from_schedule)).scalar()))
        planned_pending = Decimal(str((await db.execute(planned_from_pending_records)).scalar()))
        planned_forward = planned_sched + planned_pending

        paid_q = select(func.coalesce(func.sum(PaymentRecord.amount), 0)).where(
            PaymentRecord.payment_date >= month_start,
            PaymentRecord.payment_date < month_end,
            PaymentRecord.status == PaymentStatus.CONFIRMED.value,
        )
        paid = Decimal(str((await db.execute(paid_q)).scalar()))

        planned = planned_forward if planned_forward >= paid else paid
        remaining = planned - paid
        if remaining < 0:
            remaining = Decimal("0")

        month_buckets.append(
            {
                "month": f"{y}-{m:02d}",
                "planned": planned,
                "paid": paid,
                "remaining": remaining,
            }
        )

    grand_planned = sum((b["planned"] for b in month_buckets), Decimal("0"))
    grand_paid = sum((b["paid"] for b in month_buckets), Decimal("0"))

    paid_to_date_q = select(func.coalesce(func.sum(PaymentRecord.amount), 0)).where(
        PaymentRecord.status == PaymentStatus.CONFIRMED.value,
    )
    paid_to_date = Decimal(str((await db.execute(paid_to_date_q)).scalar()))

    undated_planned_q = select(func.coalesce(func.sum(PaymentSchedule.planned_amount), 0)).where(
        PaymentSchedule.planned_date.is_(None),
        PaymentSchedule.status.in_(
            (ScheduleItemStatus.PLANNED.value, ScheduleItemStatus.DUE.value)
        ),
    )
    undated_planned = Decimal(str((await db.execute(undated_planned_q)).scalar()))

    if month_buckets:
        window_start = date.fromisoformat(f"{month_buckets[0]['month']}-01")
        last_month_str = month_buckets[-1]["month"]
        ly, lm = (int(x) for x in last_month_str.split("-"))
        if lm == 12:
            window_end = date(ly + 1, 1, 1)
        else:
            window_end = date(ly, lm + 1, 1)
        out_of_window_q = select(func.coalesce(func.sum(PaymentSchedule.planned_amount), 0)).where(
            PaymentSchedule.planned_date.isnot(None),
            (PaymentSchedule.planned_date < window_start)
            | (PaymentSchedule.planned_date >= window_end),
            PaymentSchedule.status.in_(
                (ScheduleItemStatus.PLANNED.value, ScheduleItemStatus.DUE.value)
            ),
        )
        out_of_window_planned = Decimal(str((await db.execute(out_of_window_q)).scalar()))
    else:
        out_of_window_planned = Decimal("0")

    return {
        "months": month_buckets,
        "grand_planned": grand_planned,
        "grand_paid": grand_paid,
        "paid_to_date": paid_to_date,
        "undated_planned": undated_planned,
        "out_of_window_planned": out_of_window_planned,
    }


async def upcoming_due_count(db: AsyncSession, within_days: int = 30) -> int:
    today = date.today()
    end = date.fromordinal(today.toordinal() + within_days)
    q = select(func.count(PaymentSchedule.id)).where(
        PaymentSchedule.planned_date.isnot(None),
        PaymentSchedule.planned_date >= today,
        PaymentSchedule.planned_date <= end,
        PaymentSchedule.status.in_(
            (ScheduleItemStatus.PLANNED.value, ScheduleItemStatus.DUE.value)
        ),
    )
    return int((await db.execute(q)).scalar() or 0)


__all__ = [
    "build_summary",
    "build_summary_for",
    "delete_schedule_item",
    "execute_schedule_item",
    "get_contract_with_schedules",
    "link_invoice",
    "list_schedule",
    "payment_forecast",
    "replace_schedule",
    "upcoming_due_count",
    "update_schedule_item",
]
