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


@router.get(
    "/contracts/{contract_id}/payment-schedule",
    response_model=PaymentScheduleSummaryOut,
)
async def list_payment_schedule(
    contract_id: UUID,
    _user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    contract = await svc.get_contract_with_schedules(db, contract_id)
    items = list(contract.schedules)
    return svc.build_summary(contract, items)


@router.post(
    "/contracts/{contract_id}/payment-schedule",
    response_model=list[PaymentScheduleItemOut],
    status_code=201,
)
async def create_payment_schedule(
    contract_id: UUID,
    body: PaymentScheduleIn,
    _user: Annotated[None, Depends(require_roles("admin", "procurement_mgr", "finance_auditor"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    items = await svc.replace_schedule(db, contract_id, [i.model_dump() for i in body.items])
    await db.commit()
    return items


@router.put(
    "/contracts/{contract_id}/payment-schedule/{installment_no}",
    response_model=PaymentScheduleItemOut,
)
async def update_schedule_item(
    contract_id: UUID,
    installment_no: int,
    body: PaymentScheduleItemUpdate,
    _user: Annotated[None, Depends(require_roles("admin", "procurement_mgr", "finance_auditor"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    item = await svc.update_schedule_item(
        db, contract_id, installment_no, body.model_dump(exclude_none=True)
    )
    await db.commit()
    return item


@router.delete(
    "/contracts/{contract_id}/payment-schedule/{installment_no}",
    status_code=204,
)
async def delete_schedule_item(
    contract_id: UUID,
    installment_no: int,
    _user: Annotated[None, Depends(require_roles("admin", "procurement_mgr", "finance_auditor"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await svc.delete_schedule_item(db, contract_id, installment_no)
    await db.commit()


@router.post(
    "/contracts/{contract_id}/payment-schedule/{installment_no}/execute",
    response_model=PaymentScheduleItemOut,
)
async def execute_schedule_item(
    contract_id: UUID,
    installment_no: int,
    body: PaymentScheduleExecuteIn,
    _user: Annotated[None, Depends(require_roles("admin", "procurement_mgr", "finance_auditor"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    item = await svc.execute_schedule_item(
        db,
        contract_id,
        installment_no,
        payment_method=body.payment_method,
        transaction_ref=body.transaction_ref,
        invoice_id=body.invoice_id,
        amount_override=body.amount,
    )
    await db.commit()
    return item


@router.patch(
    "/contracts/{contract_id}/payment-schedule/{installment_no}/link-invoice",
    response_model=PaymentScheduleItemOut,
)
async def link_invoice_to_schedule(
    contract_id: UUID,
    installment_no: int,
    body: PaymentScheduleLinkInvoiceIn,
    _user: Annotated[None, Depends(require_roles("admin", "procurement_mgr", "finance_auditor"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    item = await svc.link_invoice(db, contract_id, installment_no, body.invoice_id)
    await db.commit()
    return item


@router.get("/dashboard/payment-forecast", response_model=PaymentForecastOut)
async def get_payment_forecast(
    _user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    months: Annotated[int, Query(ge=1, le=24)] = 6,
):
    return await svc.payment_forecast(db, months)
