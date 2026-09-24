from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.models import PaymentRecord, PurchaseOrder
from app.schemas import PaymentScheduleItemOut, PaymentScheduleSummaryOut
from app.services.payment_schedule import execute_schedule_item
from tests.payment_execute_support import seed_execution_case


@pytest.mark.parametrize("contract_parent", [True, False], ids=["contract", "direct-po"])
async def test_execute_preserves_history_when_only_payment_has_suffix_002(
    db_session: AsyncSession,
    client: AsyncClient,
    contract_parent: bool,
) -> None:
    # Given: paid installment 1 owns the sole payment 002; installment 2 is planned.
    case = await seed_execution_case(db_session, contract_parent)
    headers = {"Authorization": f"Bearer {create_access_token(str(case.user.id))}"}
    history_before = (
        case.history.id,
        case.history.payment_number,
        case.history.amount,
        case.history.schedule_item_id,
        case.history.transaction_ref,
    )
    await db_session.refresh(case.schedules[0])
    paid_before = PaymentScheduleItemOut.model_validate(case.schedules[0])

    # When: a real authenticated procurement manager executes through the HTTP route.
    response = await client.post(
        f"{case.route}/2/execute",
        headers=headers,
        json={
            "payment_method": "bank_transfer",
            "transaction_ref": "new-payment",
            "amount": "7500",
        },
    )

    # Then: serialization succeeds, payment 003 is linked, and history remains intact.
    assert response.status_code == 200, response.text
    item = PaymentScheduleItemOut.model_validate_json(response.content)
    assert (item.id, item.status, item.actual_amount) == (
        case.schedules[1].id,
        "paid",
        Decimal("7500"),
    )
    payment = (
        await db_session.scalars(
            select(PaymentRecord).where(PaymentRecord.id == item.payment_record_id)
        )
    ).one()
    assert (payment.payment_number, payment.schedule_item_id, payment.amount) == (
        f"PAY-{case.number}-003",
        item.id,
        Decimal("7500"),
    )
    assert payment.contract_id == (case.contract.id if case.contract else None)
    await db_session.refresh(case.history)
    await db_session.refresh(case.schedules[0])
    assert (
        case.history.id,
        case.history.payment_number,
        case.history.amount,
        case.history.schedule_item_id,
        case.history.transaction_ref,
    ) == history_before
    assert PaymentScheduleItemOut.model_validate(case.schedules[0]) == paid_before
    po = (
        await db_session.scalars(
            select(PurchaseOrder)
            .where(PurchaseOrder.id == case.po.id)
            .execution_options(populate_existing=True)
        )
    ).one()
    assert po.amount_paid == Decimal("17500")
    summary_response = await client.get(case.route, headers=headers)
    assert summary_response.status_code == 200
    summary = PaymentScheduleSummaryOut.model_validate_json(summary_response.content)
    assert (summary.paid_total, summary.remaining) == (Decimal("17500"), Decimal("12500"))


@pytest.mark.parametrize("contract_parent", [True, False], ids=["contract", "direct-po"])
async def test_execute_returns_409_when_installment_is_already_paid(
    db_session: AsyncSession,
    client: AsyncClient,
    contract_parent: bool,
) -> None:
    # Given: an already executed installment and its original payment.
    case = await seed_execution_case(db_session, contract_parent)
    headers = {"Authorization": f"Bearer {create_access_token(str(case.user.id))}"}

    # When: the same installment is executed again through HTTP.
    response = await client.post(f"{case.route}/1/execute", headers=headers, json={})

    # Then: conflict leaves the paid amount and payment history unchanged.
    assert response.status_code == 409, response.text
    payments = (
        await db_session.scalars(select(PaymentRecord).where(PaymentRecord.po_id == case.po.id))
    ).all()
    assert [payment.id for payment in payments] == [case.history.id]
    await db_session.refresh(case.po)
    assert case.po.amount_paid == Decimal("10000")


@pytest.mark.parametrize("contract_parent", [True, False], ids=["contract", "direct-po"])
@pytest.mark.parametrize(
    ("suffixes", "expected"),
    [(("001", "003"), "004"), (("999", "1000"), "1001")],
    ids=["deleted-middle-payment", "numeric-not-lexicographic"],
)
async def test_execute_uses_numeric_maximum_when_payment_numbers_have_gaps(
    db_session: AsyncSession,
    contract_parent: bool,
    suffixes: tuple[str, str],
    expected: str,
) -> None:
    # Given: surviving numbers after deletion, or a suffix exceeding three digits.
    case = await seed_execution_case(db_session, contract_parent)
    case.history.payment_number = f"PAY-{case.number}-{suffixes[0]}"
    db_session.add(
        PaymentRecord(
            payment_number=f"PAY-{case.number}-{suffixes[1]}",
            po_id=case.po.id,
            amount=Decimal("1"),
            status="pending",
        )
    )
    await db_session.flush()

    # When: the next planned installment is executed.
    item = await execute_schedule_item(
        db_session,
        2,
        "bank_transfer",
        None,
        None,
        None,
        contract_id=case.contract.id if case.contract else None,
        po_id=None if case.contract else case.po.id,
    )

    # Then: allocation follows the greatest numeric suffix, not count or text order.
    PaymentScheduleItemOut.model_validate(item)
    payment = (
        await db_session.scalars(
            select(PaymentRecord).where(PaymentRecord.id == item.payment_record_id)
        )
    ).one()
    assert payment.payment_number == f"PAY-{case.number}-{expected}"


@pytest.mark.parametrize("contract_parent", [True, False], ids=["contract", "direct-po"])
@pytest.mark.parametrize("number_case", [("007", "008"), ("manual", "001")])
async def test_execute_uses_exact_prefix_when_other_number_formats_exist(
    db_session: AsyncSession,
    contract_parent: bool,
    number_case: tuple[str, str],
) -> None:
    # Given: literal LIKE metacharacters, extended parent numbers, and manual formats.
    case = await seed_execution_case(db_session, contract_parent)
    if case.contract:
        case.contract.contract_number = "CT-EX_%"
    else:
        case.po.po_number = "PO-EX_%"
    history_suffix, expected = number_case
    case.history.payment_number = f"PAY-{case.number}-{history_suffix}"
    numbers = [
        f"PAY-{case.number}X-800",
        f"PAY-{case.number}-extra-900",
        f"PAY-{case.number}-",
        f"PAY-{case.number}-10x",
        f"PAY-{case.number}-９９９",
        f"PAY-{case.number.replace('_%', 'AB')}-999",
        f"{case.number}-P80",
    ]
    db_session.add_all(
        [
            PaymentRecord(payment_number=number, po_id=case.po.id, amount=Decimal("1"))
            for number in numbers
        ]
    )
    await db_session.flush()

    # When: an installment is executed in this namespace.
    item = await execute_schedule_item(
        db_session,
        2,
        "bank_transfer",
        None,
        None,
        None,
        contract_id=case.contract.id if case.contract else None,
        po_id=None if case.contract else case.po.id,
    )

    # Then: only complete ASCII numeric suffixes of the literal prefix contribute.
    payment = (
        await db_session.scalars(
            select(PaymentRecord).where(PaymentRecord.id == item.payment_record_id)
        )
    ).one()
    assert payment.payment_number == f"PAY-{case.number}-{expected}"
