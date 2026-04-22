from __future__ import annotations

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
    ScheduleItemStatus,
)


async def get_contract_with_schedules(db: AsyncSession, contract_id: UUID) -> Contract:
    result = await db.execute(
        select(Contract).where(Contract.id == contract_id).options(selectinload(Contract.schedules))
    )
    contract = result.scalar_one_or_none()
    if contract is None:
        raise HTTPException(404, "contract.not_found")
    return contract


async def list_schedule(db: AsyncSession, contract_id: UUID) -> list[PaymentSchedule]:
    await get_contract_with_schedules(db, contract_id)
    result = await db.execute(
        select(PaymentSchedule)
        .where(PaymentSchedule.contract_id == contract_id)
        .order_by(PaymentSchedule.installment_no)
    )
    return list(result.scalars().all())


async def replace_schedule(
    db: AsyncSession,
    contract_id: UUID,
    items: list[dict],
) -> list[PaymentSchedule]:
    await get_contract_with_schedules(db, contract_id)

    await db.execute(
        delete(PaymentSchedule).where(
            PaymentSchedule.contract_id == contract_id,
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
            contract_id=contract_id,
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
    contract_id: UUID,
    installment_no: int,
    updates: dict,
) -> PaymentSchedule:
    result = await db.execute(
        select(PaymentSchedule).where(
            PaymentSchedule.contract_id == contract_id,
            PaymentSchedule.installment_no == installment_no,
        )
    )
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(404, "schedule_item.not_found")

    for field, value in updates.items():
        if value is not None and hasattr(item, field):
            setattr(item, field, value)

    await db.flush()
    return item


async def delete_schedule_item(
    db: AsyncSession,
    contract_id: UUID,
    installment_no: int,
) -> None:
    result = await db.execute(
        select(PaymentSchedule).where(
            PaymentSchedule.contract_id == contract_id,
            PaymentSchedule.installment_no == installment_no,
        )
    )
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(404, "schedule_item.not_found")
    if item.status in (ScheduleItemStatus.PAID.value, ScheduleItemStatus.PARTIALLY_PAID.value):
        raise HTTPException(409, "schedule_item.cannot_delete_paid")
    await db.delete(item)
    await db.flush()


async def execute_schedule_item(
    db: AsyncSession,
    contract_id: UUID,
    installment_no: int,
    payment_method: str,
    transaction_ref: str | None,
    invoice_id: UUID | None,
    amount_override: Decimal | None,
) -> PaymentSchedule:
    contract = await get_contract_with_schedules(db, contract_id)

    result = await db.execute(
        select(PaymentSchedule).where(
            PaymentSchedule.contract_id == contract_id,
            PaymentSchedule.installment_no == installment_no,
        )
    )
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(404, "schedule_item.not_found")
    if item.status == ScheduleItemStatus.PAID.value:
        raise HTTPException(409, "schedule_item.already_paid")

    pay_amount = amount_override if amount_override is not None else item.planned_amount

    existing_count = (
        await db.execute(
            select(func.count(PaymentRecord.id)).where(PaymentRecord.po_id == contract.po_id)
        )
    ).scalar() or 0

    payment = PaymentRecord(
        id=new_uuid(),
        payment_number=f"PAY-{contract.contract_number}-{existing_count + 1:03d}",
        po_id=contract.po_id,
        installment_no=installment_no,
        amount=pay_amount,
        currency=contract.currency,
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

    if invoice_id is not None:
        invoice = await db.get(Invoice, invoice_id)
        if invoice is None:
            raise HTTPException(404, "invoice.not_found")
        item.invoice_id = invoice_id

    await db.flush()
    return item


async def link_invoice(
    db: AsyncSession,
    contract_id: UUID,
    installment_no: int,
    invoice_id: UUID,
) -> PaymentSchedule:
    result = await db.execute(
        select(PaymentSchedule).where(
            PaymentSchedule.contract_id == contract_id,
            PaymentSchedule.installment_no == installment_no,
        )
    )
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(404, "schedule_item.not_found")

    invoice = await db.get(Invoice, invoice_id)
    if invoice is None:
        raise HTTPException(404, "invoice.not_found")

    item.invoice_id = invoice_id
    await db.flush()
    return item


def build_summary(contract: Contract, items: list[PaymentSchedule]) -> dict:
    planned_total = sum(s.planned_amount for s in items)
    paid_total = sum(s.actual_amount or Decimal("0") for s in items)
    return {
        "contract_total": contract.total_amount,
        "planned_total": planned_total,
        "paid_total": paid_total,
        "remaining": planned_total - paid_total,
        "total_mismatch": planned_total != contract.total_amount,
        "items": items,
    }


async def payment_forecast(db: AsyncSession, months: int = 6) -> dict:
    today = date.today()
    current_month = today.replace(day=1)

    month_buckets: list[dict] = []
    for i in range(months):
        y = current_month.year + (current_month.month + i - 1) // 12
        m = (current_month.month + i - 1) % 12 + 1
        month_start = date(y, m, 1)
        if m == 12:
            month_end = date(y + 1, 1, 1)
        else:
            month_end = date(y, m + 1, 1)

        planned_q = select(func.coalesce(func.sum(PaymentSchedule.planned_amount), 0)).where(
            PaymentSchedule.planned_date >= month_start,
            PaymentSchedule.planned_date < month_end,
            PaymentSchedule.status != ScheduleItemStatus.CANCELLED.value,
        )
        planned = Decimal(str((await db.execute(planned_q)).scalar()))

        paid_q = select(func.coalesce(func.sum(PaymentSchedule.actual_amount), 0)).where(
            PaymentSchedule.actual_date >= month_start,
            PaymentSchedule.actual_date < month_end,
            PaymentSchedule.status == ScheduleItemStatus.PAID.value,
        )
        paid = Decimal(str((await db.execute(paid_q)).scalar()))

        month_buckets.append(
            {
                "month": f"{y}-{m:02d}",
                "planned": planned,
                "paid": paid,
                "remaining": planned - paid,
            }
        )

    grand_planned = sum(b["planned"] for b in month_buckets)
    grand_paid = sum(b["paid"] for b in month_buckets)

    return {
        "months": month_buckets,
        "grand_planned": grand_planned,
        "grand_paid": grand_paid,
    }
