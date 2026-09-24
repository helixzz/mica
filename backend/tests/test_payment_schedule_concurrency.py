from collections.abc import AsyncIterator
from decimal import Decimal
from uuid import UUID, uuid4

import anyio
import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from app.models import (
    Company,
    Contract,
    PaymentRecord,
    PaymentSchedule,
    POContractLink,
    PurchaseOrder,
    PurchaseRequisition,
    Supplier,
    User,
)
from app.schemas import PaymentScheduleItemOut
from app.services.payment_schedule import execute_schedule_item, list_schedule
from tests.payment_execute_support import ExecutionCase, seed_execution_case


@pytest_asyncio.fixture
async def committed_case(
    test_engine: AsyncEngine,
    contract_parent: bool,
) -> AsyncIterator[ExecutionCase]:
    # Separate committed seed is required for actual PostgreSQL row-lock contention.
    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    async with factory() as db:
        case = await seed_execution_case(db, contract_parent)
        case.history.payment_number = f"PAY-{case.number}-001"
        await db.commit()
    try:
        yield case
    finally:
        async with factory.begin() as db:
            await db.execute(delete(PaymentRecord).where(PaymentRecord.po_id == case.po.id))
            if case.contract:
                await db.execute(delete(Contract).where(Contract.id == case.contract.id))
            await db.execute(delete(PaymentSchedule).where(PaymentSchedule.po_id == case.po.id))
            await db.execute(delete(PurchaseOrder).where(PurchaseOrder.id == case.po.id))
            await db.execute(
                delete(PurchaseRequisition).where(PurchaseRequisition.id == case.po.pr_id)
            )
            await db.execute(delete(User).where(User.id == case.user.id))
            await db.execute(delete(Company).where(Company.id == case.po.company_id))
            await db.execute(delete(Supplier).where(Supplier.id == case.po.supplier_id))


@pytest.mark.parametrize("contract_parent", [True, False], ids=["contract", "direct-po"])
@pytest.mark.parametrize(
    "same_item", [True, False], ids=["same-installment", "different-installments"]
)
async def test_concurrent_execute_serializes_when_sessions_preload_stale_state(
    test_engine: AsyncEngine,
    committed_case: ExecutionCase,
    same_item: bool,
) -> None:
    # Given: two independent transactions cache the same unpaid schedule and PO amount.
    case = committed_case
    factory = async_sessionmaker(test_engine, expire_on_commit=False, autoflush=False)
    results: list[int] = []
    async with factory() as first, factory() as second, factory() as observer:
        cached = await list_schedule(
            second,
            contract_id=case.contract.id if case.contract else None,
            po_id=None if case.contract else case.po.id,
        )
        cached_po = await second.get(PurchaseOrder, case.po.id)
        assert cached[1].status == "planned"
        first_pid = await first.scalar(text("SELECT pg_backend_pid()"))
        second_pid = await second.scalar(text("SELECT pg_backend_pid()"))

        async def competing_execute() -> None:
            try:
                item = await execute_schedule_item(
                    second,
                    2 if same_item else 3,
                    "bank_transfer",
                    None,
                    None,
                    None,
                    contract_id=case.contract.id if case.contract else None,
                    po_id=None if case.contract else case.po.id,
                )
                PaymentScheduleItemOut.model_validate(item)
                await second.commit()
                results.append(200)
            except HTTPException as error:
                await second.rollback()
                results.append(error.status_code)

        # When: one execution is uncommitted while the second reaches a real DB lock wait.
        await execute_schedule_item(
            first,
            2,
            "bank_transfer",
            None,
            None,
            None,
            contract_id=case.contract.id if case.contract else None,
            po_id=None if case.contract else case.po.id,
        )
        with anyio.fail_after(10):
            async with anyio.create_task_group() as tasks:
                tasks.start_soon(competing_execute)
                while not await observer.scalar(
                    text("SELECT :blocker = ANY(pg_blocking_pids(:waiter))"),
                    {"blocker": first_pid, "waiter": second_pid},
                ):
                    assert not results, "contender completed without waiting for the transaction"
                await first.commit()

        # Then: duplicate execution conflicts; distinct executions accumulate without lost updates.
        assert results == [409 if same_item else 200]
        payments = (
            await observer.scalars(
                select(PaymentRecord)
                .where(PaymentRecord.po_id == case.po.id)
                .order_by(PaymentRecord.payment_number)
            )
        ).all()
        suffixes = ["001", "002"] if same_item else ["001", "002", "003"]
        assert [payment.payment_number for payment in payments] == [
            f"PAY-{case.number}-{suffix}" for suffix in suffixes
        ]
        amount_paid = await observer.scalar(
            select(PurchaseOrder.amount_paid).where(PurchaseOrder.id == case.po.id)
        )
        assert amount_paid == (Decimal("20000") if same_item else Decimal("30000"))
        assert cached_po is not None  # Keep a strong identity-map reference through the race.


@pytest_asyncio.fixture
async def linked_po_id(
    test_engine: AsyncEngine,
    committed_case: ExecutionCase,
) -> AsyncIterator[UUID]:
    case = committed_case
    assert case.contract is not None
    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    async with factory.begin() as db:
        po = PurchaseOrder(
            po_number=f"PO-LINK-{uuid4().hex[:8]}",
            pr_id=case.po.pr_id,
            supplier_id=case.po.supplier_id,
            company_id=case.po.company_id,
            created_by_id=case.user.id,
        )
        db.add(po)
        await db.flush()
        db.add(POContractLink(po_id=po.id, contract_id=case.contract.id))
    try:
        yield po.id
    finally:
        async with factory.begin() as db:
            await db.execute(delete(PaymentRecord).where(PaymentRecord.po_id == po.id))
            await db.execute(delete(PurchaseOrder).where(PurchaseOrder.id == po.id))


@pytest.mark.parametrize("contract_parent", [True], ids=["contract-via-linked-po"])
async def test_execute_rejects_duplicate_when_linked_po_has_a_different_parent_lock(
    test_engine: AsyncEngine,
    committed_case: ExecutionCase,
    linked_po_id: UUID,
) -> None:
    # Given: a contract installment is reachable via two POs with different lock rows.
    case = committed_case
    assert case.contract is not None
    factory = async_sessionmaker(test_engine, expire_on_commit=False, autoflush=False)
    results: list[int] = []
    async with factory() as first, factory() as second, factory() as observer:
        cached = await second.get(PaymentSchedule, case.schedules[1].id)
        first_pid = await first.scalar(text("SELECT pg_backend_pid()"))
        second_pid = await second.scalar(text("SELECT pg_backend_pid()"))

        async def competing_execute() -> None:
            try:
                await execute_schedule_item(
                    second,
                    2,
                    "bank_transfer",
                    None,
                    None,
                    None,
                    po_id=linked_po_id,
                )
                await second.commit()
                results.append(200)
            except HTTPException as error:
                await second.rollback()
                results.append(error.status_code)

        # When: execution through the linked PO waits for the original contract execution.
        await execute_schedule_item(
            first,
            2,
            "bank_transfer",
            None,
            None,
            None,
            contract_id=case.contract.id,
        )
        with anyio.fail_after(10):
            async with anyio.create_task_group() as tasks:
                tasks.start_soon(competing_execute)
                while not await observer.scalar(
                    text("SELECT :blocker = ANY(pg_blocking_pids(:waiter))"),
                    {"blocker": first_pid, "waiter": second_pid},
                ):
                    assert not results, "contender completed before the first transaction"
                await first.commit()

        # Then: the schedule lock protects the single payment despite distinct PO locks/prefixes.
        assert results == [409]
        payments = (
            await observer.scalars(
                select(PaymentRecord).where(PaymentRecord.schedule_item_id == case.schedules[1].id)
            )
        ).all()
        assert [payment.po_id for payment in payments] == [case.po.id]
        assert await observer.scalar(
            select(PurchaseOrder.amount_paid).where(PurchaseOrder.id == linked_po_id)
        ) == Decimal("0")
        assert cached is not None
