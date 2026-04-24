from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.db import new_uuid
from app.models import (
    Contract,
    ContractStatus,
    POStatus,
    PurchaseOrder,
    PurchaseRequisition,
    ScheduleItemStatus,
    Supplier,
    User,
)
from app.services import payment_schedule as svc


async def _ensure_contract(db_session) -> Contract:
    existing = (await db_session.execute(select(Contract).limit(1))).scalar_one_or_none()
    if existing:
        return existing

    user = (await db_session.execute(select(User).limit(1))).scalar_one()
    supplier = (await db_session.execute(select(Supplier).limit(1))).scalar_one()

    pr = PurchaseRequisition(
        id=new_uuid(),
        pr_number=f"PR-SCHED-{uuid4().hex[:6]}",
        title="Schedule test PR",
        business_reason="unit test",
        status="draft",
        requester_id=user.id,
        company_id=user.company_id,
        department_id=user.department_id,
        currency="CNY",
        total_amount=Decimal("48000"),
    )
    db_session.add(pr)
    await db_session.flush()

    po = PurchaseOrder(
        id=new_uuid(),
        po_number=f"PO-SCHED-{uuid4().hex[:6]}",
        pr_id=pr.id,
        supplier_id=supplier.id,
        company_id=user.company_id,
        status=POStatus.CONFIRMED.value,
        currency="CNY",
        total_amount=Decimal("48000"),
        created_by_id=user.id,
    )
    db_session.add(po)
    await db_session.flush()

    contract = Contract(
        id=new_uuid(),
        contract_number=f"CT-SCHED-{uuid4().hex[:6]}",
        po_id=po.id,
        supplier_id=supplier.id,
        title="Schedule Test Contract",
        status=ContractStatus.ACTIVE.value,
        currency="CNY",
        total_amount=Decimal("48000"),
    )
    db_session.add(contract)
    await db_session.flush()
    return contract


async def test_replace_schedule_creates_items(seeded_db_session):
    contract = await _ensure_contract(seeded_db_session)
    items = await svc.replace_schedule(
        seeded_db_session,
        [
            {
                "installment_no": 1,
                "label": "首付",
                "planned_amount": Decimal("10000"),
                "planned_date": "2026-05-01",
            },
            {
                "installment_no": 2,
                "label": "尾款",
                "planned_amount": Decimal("38000"),
                "planned_date": "2026-08-01",
            },
        ],
        contract_id=contract.id,
    )
    assert len(items) == 2
    assert items[0].label == "首付"
    assert items[1].planned_amount == Decimal("38000")


async def test_replace_schedule_removes_old_planned_items(seeded_db_session):
    contract = await _ensure_contract(seeded_db_session)
    await svc.replace_schedule(
        seeded_db_session,
        [{"installment_no": 1, "label": "v1", "planned_amount": Decimal("1000")}],
        contract_id=contract.id,
    )
    new_items = await svc.replace_schedule(
        seeded_db_session,
        [{"installment_no": 1, "label": "v2", "planned_amount": Decimal("2000")}],
        contract_id=contract.id,
    )
    assert len(new_items) == 1
    assert new_items[0].label == "v2"


async def test_list_schedule_returns_summary(seeded_db_session):
    contract = await _ensure_contract(seeded_db_session)
    created = await svc.replace_schedule(
        seeded_db_session,
        [
            {"installment_no": 1, "label": "A", "planned_amount": Decimal("24000")},
            {"installment_no": 2, "label": "B", "planned_amount": Decimal("24000")},
        ],
        contract_id=contract.id,
    )
    summary = svc.build_summary(contract, created)
    assert summary["planned_total"] == Decimal("48000")
    assert summary["paid_total"] == Decimal("0")
    assert summary["total_mismatch"] is (summary["planned_total"] != contract.total_amount)


async def test_update_schedule_item(seeded_db_session):
    contract = await _ensure_contract(seeded_db_session)
    await svc.replace_schedule(
        seeded_db_session,
        [{"installment_no": 1, "label": "原始", "planned_amount": Decimal("10000")}],
        contract_id=contract.id,
    )
    updated = await svc.update_schedule_item(
        seeded_db_session, 1, {"label": "已改"}, contract_id=contract.id
    )
    assert updated.label == "已改"


async def test_delete_schedule_item(seeded_db_session):
    contract = await _ensure_contract(seeded_db_session)
    await svc.replace_schedule(
        seeded_db_session,
        [
            {"installment_no": 1, "label": "keep", "planned_amount": Decimal("10000")},
            {"installment_no": 2, "label": "remove", "planned_amount": Decimal("5000")},
        ],
        contract_id=contract.id,
    )
    await svc.delete_schedule_item(seeded_db_session, 2, contract_id=contract.id)
    remaining = await svc.list_schedule(seeded_db_session, contract_id=contract.id)
    assert len(remaining) == 1
    assert remaining[0].installment_no == 1


async def test_delete_paid_item_raises(seeded_db_session):
    contract = await _ensure_contract(seeded_db_session)
    await svc.replace_schedule(
        seeded_db_session,
        [
            {
                "installment_no": 1,
                "label": "pay",
                "planned_amount": Decimal("10000"),
                "planned_date": "2026-05-01",
            }
        ],
        contract_id=contract.id,
    )
    await svc.execute_schedule_item(
        seeded_db_session,
        1,
        contract_id=contract.id,
        payment_method="bank_transfer",
        transaction_ref=None,
        invoice_id=None,
        amount_override=None,
    )
    with pytest.raises(Exception) as exc:
        await svc.delete_schedule_item(seeded_db_session, 1, contract_id=contract.id)
    assert exc.value.status_code == 409


async def test_execute_creates_payment_record(seeded_db_session):
    contract = await _ensure_contract(seeded_db_session)
    await svc.replace_schedule(
        seeded_db_session,
        [
            {
                "installment_no": 1,
                "label": "exec",
                "planned_amount": Decimal("5000"),
                "planned_date": "2026-06-01",
            }
        ],
        contract_id=contract.id,
    )
    item = await svc.execute_schedule_item(
        seeded_db_session,
        1,
        contract_id=contract.id,
        payment_method="bank_transfer",
        transaction_ref="TXN-001",
        invoice_id=None,
        amount_override=None,
    )
    assert item.status == ScheduleItemStatus.PAID.value
    assert item.actual_amount == Decimal("5000")
    assert item.payment_record_id is not None


async def test_execute_schedule_item_updates_po_amount_paid(seeded_db_session):
    contract = await _ensure_contract(seeded_db_session)
    po = (
        await seeded_db_session.execute(
            select(PurchaseOrder).where(PurchaseOrder.id == contract.po_id)
        )
    ).scalar_one()
    starting_amount_paid = po.amount_paid or Decimal("0")
    await svc.replace_schedule(
        seeded_db_session,
        [
            {
                "installment_no": 1,
                "label": "execute-updates-po",
                "planned_amount": Decimal("7500"),
                "planned_date": "2026-06-01",
            }
        ],
        contract_id=contract.id,
    )

    await svc.execute_schedule_item(
        seeded_db_session,
        1,
        contract_id=contract.id,
        payment_method="bank_transfer",
        transaction_ref=None,
        invoice_id=None,
        amount_override=None,
    )

    refreshed_po = (
        await seeded_db_session.execute(
            select(PurchaseOrder).where(PurchaseOrder.id == contract.po_id)
        )
    ).scalar_one()
    assert refreshed_po.amount_paid == starting_amount_paid + Decimal("7500")


async def test_execute_with_amount_override(seeded_db_session):
    contract = await _ensure_contract(seeded_db_session)
    await svc.replace_schedule(
        seeded_db_session,
        [
            {
                "installment_no": 1,
                "label": "partial",
                "planned_amount": Decimal("20000"),
                "planned_date": "2026-06-01",
            }
        ],
        contract_id=contract.id,
    )
    item = await svc.execute_schedule_item(
        seeded_db_session,
        1,
        contract_id=contract.id,
        payment_method="bank_transfer",
        transaction_ref=None,
        invoice_id=None,
        amount_override=Decimal("15000"),
    )
    assert item.actual_amount == Decimal("15000")


async def test_execute_already_paid_raises(seeded_db_session):
    contract = await _ensure_contract(seeded_db_session)
    await svc.replace_schedule(
        seeded_db_session,
        [
            {
                "installment_no": 1,
                "label": "dup",
                "planned_amount": Decimal("1000"),
                "planned_date": "2026-06-01",
            }
        ],
        contract_id=contract.id,
    )
    await svc.execute_schedule_item(
        seeded_db_session,
        1,
        contract_id=contract.id,
        payment_method="bank_transfer",
        transaction_ref=None,
        invoice_id=None,
        amount_override=None,
    )
    with pytest.raises(Exception) as exc:
        await svc.execute_schedule_item(
            seeded_db_session,
            1,
            contract_id=contract.id,
            payment_method="bank_transfer",
            transaction_ref=None,
            invoice_id=None,
            amount_override=None,
        )
    assert exc.value.status_code == 409


async def test_payment_forecast_returns_monthly_buckets(seeded_db_session):
    result = await svc.payment_forecast(seeded_db_session, months=3)
    assert len(result["months"]) == 3
    assert all("month" in m and "planned" in m for m in result["months"])


async def test_nonexistent_contract_raises_404(seeded_db_session):
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        await svc.list_schedule(seeded_db_session, contract_id=uuid4())
    assert exc.value.status_code == 404


async def _ensure_standalone_po(db_session) -> PurchaseOrder:
    user = (await db_session.execute(select(User).limit(1))).scalar_one()
    supplier = (await db_session.execute(select(Supplier).limit(1))).scalar_one()
    pr = PurchaseRequisition(
        id=new_uuid(),
        pr_number=f"PR-PO-PAY-{uuid4().hex[:6]}",
        title="PO payment plan PR",
        business_reason="po-level payment schedule test",
        status="draft",
        requester_id=user.id,
        company_id=user.company_id,
        department_id=user.department_id,
        currency="CNY",
        total_amount=Decimal("30000"),
    )
    db_session.add(pr)
    await db_session.flush()

    po = PurchaseOrder(
        id=new_uuid(),
        po_number=f"PO-PAY-{uuid4().hex[:6]}",
        pr_id=pr.id,
        supplier_id=supplier.id,
        company_id=user.company_id,
        status=POStatus.CONFIRMED.value,
        currency="CNY",
        total_amount=Decimal("30000"),
        created_by_id=user.id,
    )
    db_session.add(po)
    await db_session.flush()
    return po


async def test_po_level_payment_schedule_create_and_summary(seeded_db_session):
    db = seeded_db_session
    po = await _ensure_standalone_po(db)

    items = await svc.replace_schedule(
        db,
        [
            {"installment_no": 1, "label": "deposit", "planned_amount": Decimal("10000")},
            {"installment_no": 2, "label": "balance", "planned_amount": Decimal("20000")},
        ],
        po_id=po.id,
    )
    assert len(items) == 2
    assert all(i.po_id == po.id for i in items)
    assert all(i.contract_id is None for i in items)

    summary = await svc.build_summary_for(db, po_id=po.id)
    assert summary["contract_total"] == Decimal("30000")
    assert summary["planned_total"] == Decimal("30000")
    assert summary["paid_total"] == Decimal("0")
    assert summary["total_mismatch"] is False
    assert len(summary["items"]) == 2


async def test_po_level_schedule_isolation_from_contract_schedules(seeded_db_session):
    db = seeded_db_session
    po = await _ensure_standalone_po(db)
    contract = await _ensure_contract(db)

    await svc.replace_schedule(
        db,
        [{"installment_no": 1, "label": "po-only", "planned_amount": Decimal("5000")}],
        po_id=po.id,
    )
    await svc.replace_schedule(
        db,
        [{"installment_no": 1, "label": "contract-only", "planned_amount": Decimal("48000")}],
        contract_id=contract.id,
    )

    po_items = await svc.list_schedule(db, po_id=po.id)
    ct_items = await svc.list_schedule(db, contract_id=contract.id)

    assert {i.label for i in po_items} == {"po-only"}
    assert {i.label for i in ct_items} == {"contract-only"}


async def test_payment_schedule_requires_exactly_one_parent(seeded_db_session):
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        await svc.list_schedule(seeded_db_session)
    assert exc.value.status_code == 400

    with pytest.raises(HTTPException) as exc:
        await svc.list_schedule(seeded_db_session, contract_id=uuid4(), po_id=uuid4())
    assert exc.value.status_code == 400


async def test_payment_forecast_includes_direct_confirmed_payments(seeded_db_session):
    from datetime import date as _date

    from app.models import PaymentRecord, PaymentStatus

    today = _date.today()
    po = await _ensure_standalone_po(seeded_db_session)

    seeded_db_session.add(
        PaymentRecord(
            id=new_uuid(),
            payment_number=f"PAY-FORECAST-{uuid4().hex[:6]}",
            po_id=po.id,
            contract_id=None,
            installment_no=1,
            amount=Decimal("4500000"),
            currency="CNY",
            due_date=today,
            payment_date=today,
            payment_method="bank_transfer",
            status=PaymentStatus.CONFIRMED.value,
        )
    )
    await seeded_db_session.flush()

    result = await svc.payment_forecast(seeded_db_session, months=1)

    assert len(result["months"]) == 1
    current_bucket = result["months"][0]
    assert current_bucket["paid"] >= Decimal("4500000")
    assert result["grand_paid"] >= Decimal("4500000")


async def test_payment_forecast_includes_pending_records_in_planned(seeded_db_session):
    from datetime import date as _date

    from app.models import PaymentRecord, PaymentStatus

    po = await _ensure_standalone_po(seeded_db_session)
    due = _date.today()

    seeded_db_session.add(
        PaymentRecord(
            id=new_uuid(),
            payment_number=f"PAY-PENDING-{uuid4().hex[:6]}",
            po_id=po.id,
            contract_id=None,
            installment_no=1,
            amount=Decimal("1200000"),
            currency="CNY",
            due_date=due,
            payment_date=None,
            payment_method="bank_transfer",
            status=PaymentStatus.PENDING.value,
        )
    )
    await seeded_db_session.flush()

    result = await svc.payment_forecast(seeded_db_session, months=3)

    grand_planned = sum(Decimal(str(m["planned"])) for m in result["months"])
    assert grand_planned >= Decimal("1200000")
