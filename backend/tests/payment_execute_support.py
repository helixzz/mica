"""Explicit, isolated payment-execution fixtures shared by HTTP and lock tests."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Company,
    Contract,
    PaymentRecord,
    PaymentSchedule,
    PurchaseOrder,
    PurchaseRequisition,
    Supplier,
    User,
)


@dataclass(frozen=True, slots=True)
class ExecutionCase:
    po: PurchaseOrder
    contract: Contract | None
    user: User
    schedules: tuple[PaymentSchedule, ...]
    history: PaymentRecord

    @property
    def number(self) -> str:
        return self.contract.contract_number if self.contract else self.po.po_number

    @property
    def route(self) -> str:
        parent = (
            f"contracts/{self.contract.id}" if self.contract else f"purchase-orders/{self.po.id}"
        )
        return f"/api/v1/{parent}/payment-schedule"


async def seed_execution_case(db: AsyncSession, contract_parent: bool) -> ExecutionCase:
    suffix = uuid4().hex[:8]
    company = Company(code=f"exec-{suffix}", name_zh="Execution test")
    supplier = Supplier(code=f"exec-{suffix}", name="Execution supplier")
    db.add_all([company, supplier])
    await db.flush()
    user = User(
        username=f"exec-{suffix}",
        email=f"exec-{suffix}@example.test",
        display_name="Execution manager",
        role="procurement_mgr",
        company_id=company.id,
    )
    db.add(user)
    await db.flush()
    pr = PurchaseRequisition(
        pr_number=f"PR-{suffix}",
        title="Execution PR",
        requester_id=user.id,
        company_id=company.id,
        total_amount=Decimal("30000"),
    )
    db.add(pr)
    await db.flush()
    po = PurchaseOrder(
        po_number=f"PO-{suffix}",
        pr_id=pr.id,
        supplier_id=supplier.id,
        company_id=company.id,
        created_by_id=user.id,
        total_amount=Decimal("30000"),
        amount_paid=Decimal("10000"),
    )
    db.add(po)
    await db.flush()
    contract = None
    if contract_parent:
        contract = Contract(
            contract_number=f"CT-{suffix}",
            po_id=po.id,
            supplier_id=supplier.id,
            title="Execution contract",
            total_amount=Decimal("30000"),
            status="active",
        )
        db.add(contract)
        await db.flush()
    schedules = tuple(
        PaymentSchedule(
            contract_id=contract.id if contract else None,
            po_id=None if contract else po.id,
            installment_no=number,
            label=f"Installment {number}",
            planned_amount=Decimal("10000"),
            planned_date=date(2026, 9, 1),
        )
        for number in (1, 2, 3)
    )
    db.add_all(schedules)
    await db.flush()
    number = contract.contract_number if contract else po.po_number
    history = PaymentRecord(
        payment_number=f"PAY-{number}-002",
        po_id=po.id,
        contract_id=contract.id if contract else None,
        installment_no=1,
        amount=Decimal("10000"),
        currency="CNY",
        status="confirmed",
        schedule_item_id=schedules[0].id,
        payment_date=date(2026, 9, 1),
        transaction_ref="historical-payment",
    )
    db.add(history)
    await db.flush()
    schedules[0].status = "paid"
    schedules[0].actual_amount = history.amount
    schedules[0].actual_date = history.payment_date
    schedules[0].payment_record_id = history.id
    await db.flush()
    return ExecutionCase(po, contract, user, schedules, history)
