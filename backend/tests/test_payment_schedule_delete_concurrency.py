from decimal import Decimal

import anyio
import pytest
from fastapi import HTTPException
from sqlalchemy import delete, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from app.models import AuditLog, PaymentRecord, PaymentSchedule, PurchaseOrder
from app.schemas import PaymentScheduleItemOut
from app.services.flow import delete_payment
from app.services.payment_schedule import execute_schedule_item
from tests.payment_execute_support import ExecutionCase
from tests.test_payment_schedule_concurrency import committed_case as committed_case


@pytest.mark.parametrize("contract_parent", [True, False], ids=["contract", "direct-po"])
async def test_execute_completes_when_deletion_owns_the_installment_lock(
    test_engine: AsyncEngine,
    committed_case: ExecutionCase,
) -> None:
    # Given: deletion owns the paid installment row before it reaches the PO update.
    case = committed_case
    factory = async_sessionmaker(test_engine, expire_on_commit=False, autoflush=False)
    executed: list[PaymentScheduleItemOut] = []
    errors: list[DBAPIError | HTTPException] = []
    try:
        async with factory() as deleting, factory() as executing, factory() as observer:
            await deleting.execute(
                select(PaymentSchedule)
                .where(PaymentSchedule.id == case.schedules[0].id)
                .with_for_update()
            )
            deleting_pid = await deleting.scalar(text("SELECT pg_backend_pid()"))
            executing_pid = await executing.scalar(text("SELECT pg_backend_pid()"))

            async def competing_execute() -> None:
                try:
                    item = await execute_schedule_item(
                        executing,
                        1,
                        "bank_transfer",
                        None,
                        None,
                        Decimal("7000"),
                        contract_id=case.contract.id if case.contract else None,
                        po_id=None if case.contract else case.po.id,
                    )
                    await executing.commit()
                    executed.append(PaymentScheduleItemOut.model_validate(item))
                except (DBAPIError, HTTPException) as error:
                    await executing.rollback()
                    errors.append(error)

            # When: execution waits on deletion, then real deletion proceeds toward the PO.
            with anyio.fail_after(10):
                async with anyio.create_task_group() as tasks:
                    tasks.start_soon(competing_execute)
                    while not await observer.scalar(
                        text("SELECT :blocker = ANY(pg_blocking_pids(:waiter))"),
                        {"blocker": deleting_pid, "waiter": executing_pid},
                    ):
                        assert not executed and not errors, "execution bypassed the deletion lock"
                    try:
                        await delete_payment(deleting, case.user, case.history.id)
                    except DBAPIError as error:
                        await deleting.rollback()
                        errors.append(error)

            # Then: both operations commit, leaving one replacement payment and its exact amount.
            assert errors == [], "\n".join(str(error) for error in errors)
            assert len(executed) == 1
            item = executed[0]
            assert (item.status, item.actual_amount) == ("paid", Decimal("7000"))
            payments = (
                await observer.scalars(
                    select(PaymentRecord).where(PaymentRecord.po_id == case.po.id)
                )
            ).all()
            assert [
                (payment.id, payment.schedule_item_id, payment.amount) for payment in payments
            ] == [(item.payment_record_id, case.schedules[0].id, Decimal("7000"))]
            assert item.payment_record_id != case.history.id
            assert await observer.scalar(
                select(PurchaseOrder.amount_paid).where(PurchaseOrder.id == case.po.id)
            ) == Decimal("7000")
    finally:
        async with factory.begin() as cleanup:
            await cleanup.execute(delete(AuditLog).where(AuditLog.actor_id == case.user.id))
