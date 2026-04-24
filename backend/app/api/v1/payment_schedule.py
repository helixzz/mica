from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser, require_roles
from app.db import get_db
from app.schemas import (
    PaymentForecastOut,
    PaymentScheduleExecuteIn,
    PaymentScheduleIn,
    PaymentScheduleItemOut,
    PaymentScheduleItemUpdate,
    PaymentScheduleLinkInvoiceIn,
    PaymentScheduleSummaryOut,
)
from app.services import payment_schedule as svc

router = APIRouter(tags=["payment-schedule"])

_SCHEDULE_WRITE_ROLES = ("admin", "procurement_mgr", "finance_auditor")


@router.get(
    "/contracts/{contract_id}/payment-schedule",
    response_model=PaymentScheduleSummaryOut,
)
async def list_contract_payment_schedule(
    contract_id: UUID,
    _user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await svc.build_summary_for(db, contract_id=contract_id)


@router.post(
    "/contracts/{contract_id}/payment-schedule",
    response_model=list[PaymentScheduleItemOut],
    status_code=201,
)
async def create_contract_payment_schedule(
    contract_id: UUID,
    body: PaymentScheduleIn,
    _user: Annotated[None, Depends(require_roles(*_SCHEDULE_WRITE_ROLES))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    items = await svc.replace_schedule(
        db, [i.model_dump() for i in body.items], contract_id=contract_id
    )
    await db.commit()
    return items


@router.put(
    "/contracts/{contract_id}/payment-schedule/{installment_no}",
    response_model=PaymentScheduleItemOut,
)
async def update_contract_schedule_item(
    contract_id: UUID,
    installment_no: int,
    body: PaymentScheduleItemUpdate,
    _user: Annotated[None, Depends(require_roles(*_SCHEDULE_WRITE_ROLES))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    item = await svc.update_schedule_item(
        db,
        installment_no,
        body.model_dump(exclude_none=True),
        contract_id=contract_id,
    )
    await db.commit()
    return item


@router.delete(
    "/contracts/{contract_id}/payment-schedule/{installment_no}",
    status_code=204,
)
async def delete_contract_schedule_item(
    contract_id: UUID,
    installment_no: int,
    _user: Annotated[None, Depends(require_roles(*_SCHEDULE_WRITE_ROLES))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await svc.delete_schedule_item(db, installment_no, contract_id=contract_id)
    await db.commit()


@router.post(
    "/contracts/{contract_id}/payment-schedule/{installment_no}/execute",
    response_model=PaymentScheduleItemOut,
)
async def execute_contract_schedule_item(
    contract_id: UUID,
    installment_no: int,
    body: PaymentScheduleExecuteIn,
    _user: Annotated[None, Depends(require_roles(*_SCHEDULE_WRITE_ROLES))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    item = await svc.execute_schedule_item(
        db,
        installment_no,
        payment_method=body.payment_method,
        transaction_ref=body.transaction_ref,
        invoice_id=body.invoice_id,
        amount_override=body.amount,
        contract_id=contract_id,
    )
    await db.commit()
    return item


@router.patch(
    "/contracts/{contract_id}/payment-schedule/{installment_no}/link-invoice",
    response_model=PaymentScheduleItemOut,
)
async def link_invoice_to_contract_schedule(
    contract_id: UUID,
    installment_no: int,
    body: PaymentScheduleLinkInvoiceIn,
    _user: Annotated[None, Depends(require_roles(*_SCHEDULE_WRITE_ROLES))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    item = await svc.link_invoice(db, installment_no, body.invoice_id, contract_id=contract_id)
    await db.commit()
    return item


@router.get(
    "/purchase-orders/{po_id}/payment-schedule",
    response_model=PaymentScheduleSummaryOut,
)
async def list_po_payment_schedule(
    po_id: UUID,
    _user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await svc.build_summary_for(db, po_id=po_id)


@router.post(
    "/purchase-orders/{po_id}/payment-schedule",
    response_model=list[PaymentScheduleItemOut],
    status_code=201,
)
async def create_po_payment_schedule(
    po_id: UUID,
    body: PaymentScheduleIn,
    _user: Annotated[None, Depends(require_roles(*_SCHEDULE_WRITE_ROLES))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    items = await svc.replace_schedule(db, [i.model_dump() for i in body.items], po_id=po_id)
    await db.commit()
    return items


@router.put(
    "/purchase-orders/{po_id}/payment-schedule/{installment_no}",
    response_model=PaymentScheduleItemOut,
)
async def update_po_schedule_item(
    po_id: UUID,
    installment_no: int,
    body: PaymentScheduleItemUpdate,
    _user: Annotated[None, Depends(require_roles(*_SCHEDULE_WRITE_ROLES))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    item = await svc.update_schedule_item(
        db, installment_no, body.model_dump(exclude_none=True), po_id=po_id
    )
    await db.commit()
    return item


@router.delete(
    "/purchase-orders/{po_id}/payment-schedule/{installment_no}",
    status_code=204,
)
async def delete_po_schedule_item(
    po_id: UUID,
    installment_no: int,
    _user: Annotated[None, Depends(require_roles(*_SCHEDULE_WRITE_ROLES))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await svc.delete_schedule_item(db, installment_no, po_id=po_id)
    await db.commit()


@router.post(
    "/purchase-orders/{po_id}/payment-schedule/{installment_no}/execute",
    response_model=PaymentScheduleItemOut,
)
async def execute_po_schedule_item(
    po_id: UUID,
    installment_no: int,
    body: PaymentScheduleExecuteIn,
    _user: Annotated[None, Depends(require_roles(*_SCHEDULE_WRITE_ROLES))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    item = await svc.execute_schedule_item(
        db,
        installment_no,
        payment_method=body.payment_method,
        transaction_ref=body.transaction_ref,
        invoice_id=body.invoice_id,
        amount_override=body.amount,
        po_id=po_id,
    )
    await db.commit()
    return item


@router.patch(
    "/purchase-orders/{po_id}/payment-schedule/{installment_no}/link-invoice",
    response_model=PaymentScheduleItemOut,
)
async def link_invoice_to_po_schedule(
    po_id: UUID,
    installment_no: int,
    body: PaymentScheduleLinkInvoiceIn,
    _user: Annotated[None, Depends(require_roles(*_SCHEDULE_WRITE_ROLES))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    item = await svc.link_invoice(db, installment_no, body.invoice_id, po_id=po_id)
    await db.commit()
    return item


@router.get("/dashboard/payment-forecast", response_model=PaymentForecastOut)
async def get_payment_forecast(
    _user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    months: Annotated[int, Query(ge=1, le=24)] = 6,
    past_months: Annotated[int, Query(ge=0, le=24)] = 0,
    anchor: Annotated[str | None, Query(pattern=r"^\d{4}-\d{2}$")] = None,
):
    from datetime import date as _date

    anchor_date: _date | None = None
    if anchor:
        y, m = anchor.split("-")
        anchor_date = _date(int(y), int(m), 1)
    return await svc.payment_forecast(
        db, months=months, anchor=anchor_date, past_months=past_months
    )
