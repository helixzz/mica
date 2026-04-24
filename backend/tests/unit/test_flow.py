# pyright: reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportUnusedCallResult=false, reportPrivateUsage=false
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app.db import new_uuid
from app.models import (
    Contract,
    ContractVersion,
    Document,
    PaymentRecord,
    POItem,
    PurchaseOrder,
    PurchaseRequisition,
    Supplier,
    User,
)
from app.schemas import PRCreateIn, PRItemIn
from app.services import flow as flow_svc
from app.services import purchase as purchase_svc


async def _get_user(db, username="alice"):
    return (await db.execute(select(User).where(User.username == username))).scalar_one()


async def _get_supplier(db):
    return (await db.execute(select(Supplier).order_by(Supplier.code).limit(1))).scalar_one()


def _pr_line(line_no: int, item_name: str, qty: str, unit_price: str, supplier_id) -> PRItemIn:
    return PRItemIn(
        line_no=line_no,
        item_name=item_name,
        qty=Decimal(qty),
        unit_price=Decimal(unit_price),
        supplier_id=supplier_id,
        uom="EA",
    )


async def _create_confirmed_po(
    db,
    username: str = "alice",
    *,
    title: str = "Flow PR",
    items: list[PRItemIn] | None = None,
):
    user = await _get_user(db, username)
    supplier = await _get_supplier(db)
    payload = PRCreateIn(
        title=title,
        business_reason="Flow testing",
        currency="CNY",
        items=items
        or [
            _pr_line(1, "Widget", "6", "100", supplier.id),
            _pr_line(2, "Cable", "4", "50", supplier.id),
        ],
    )
    pr = await purchase_svc.create_pr(db, user, payload)
    pr.status = "approved"
    await db.commit()
    po = await purchase_svc.convert_pr_to_po(db, user, pr.id)
    return user, supplier, pr, po


async def _create_document(db, user: User, suffix: str = "1") -> Document:
    document = Document(
        id=new_uuid(),
        storage_key=f"invoices/{suffix}-{uuid4().hex}",
        storage_backend="local",
        original_filename=f"invoice-{suffix}.pdf",
        content_type="application/pdf",
        file_size=1024,
        content_hash=f"hash-{suffix}-{uuid4().hex}",
        doc_category="invoice",
        uploaded_by_id=user.id,
    )
    db.add(document)
    await db.flush()
    return document


async def test_next_pr_number_returns_sequential(seeded_db_session):
    db = seeded_db_session
    year = datetime.now(UTC).year
    number = await purchase_svc._next_pr_number(db)
    assert number.startswith(f"PR-{year}-")
    seq = int(number.split("-")[-1])
    assert seq >= 1


async def test_next_pr_number_increments(seeded_db_session):
    db = seeded_db_session
    user = await _get_user(db)
    n1 = await purchase_svc._next_pr_number(db)
    pr = PurchaseRequisition(
        pr_number=n1,
        title="test",
        business_reason="test",
        status="draft",
        requester_id=user.id,
        company_id=user.company_id,
        department_id=user.department_id,
        currency="CNY",
        total_amount=Decimal("100"),
    )
    db.add(pr)
    await db.flush()
    n2 = await purchase_svc._next_pr_number(db)
    assert int(n2.split("-")[-1]) == int(n1.split("-")[-1]) + 1


async def test_next_po_number_increments(seeded_db_session):
    db = seeded_db_session
    user = await _get_user(db)
    supplier = await _get_supplier(db)
    n1 = await purchase_svc._next_po_number(db)
    pr = PurchaseRequisition(
        pr_number=f"PR-FLOW-{n1}",
        title="test",
        business_reason="test",
        status="draft",
        requester_id=user.id,
        company_id=user.company_id,
        department_id=user.department_id,
        currency="CNY",
        total_amount=Decimal("100"),
    )
    db.add(pr)
    await db.flush()
    po = PurchaseOrder(
        po_number=n1,
        pr_id=pr.id,
        supplier_id=supplier.id,
        company_id=user.company_id,
        status="confirmed",
        currency="CNY",
        total_amount=Decimal("100"),
        amount_paid=Decimal("0"),
        created_by_id=user.id,
    )
    db.add(po)
    await db.flush()
    n2 = await purchase_svc._next_po_number(db)
    assert int(n2.split("-")[-1]) == int(n1.split("-")[-1]) + 1


def test_compute_line_amount():
    assert purchase_svc._compute_line_amount(Decimal("3"), Decimal("20")) == Decimal("60.0000")
    assert purchase_svc._compute_line_amount(Decimal("1"), Decimal("19.9999")) == Decimal("19.9999")


async def test_po_progress(seeded_db_session):
    db = seeded_db_session
    user = await _get_user(db)
    supplier = await _get_supplier(db)
    year = datetime.now(UTC).year
    pr = PurchaseRequisition(
        pr_number=f"PR-{year}-PROG",
        title="test",
        business_reason="test",
        status="draft",
        requester_id=user.id,
        company_id=user.company_id,
        department_id=user.department_id,
        currency="CNY",
        total_amount=Decimal("200"),
    )
    db.add(pr)
    await db.flush()
    po = PurchaseOrder(
        po_number=f"PO-{year}-PROG",
        pr_id=pr.id,
        supplier_id=supplier.id,
        company_id=user.company_id,
        status="confirmed",
        currency="CNY",
        total_amount=Decimal("200"),
        amount_paid=Decimal("50"),
        created_by_id=user.id,
    )
    db.add(po)
    await db.flush()
    db.add_all(
        [
            POItem(
                po_id=po.id,
                line_no=1,
                item_name="L1",
                specification="S1",
                qty=Decimal("4"),
                qty_received=Decimal("2"),
                qty_invoiced=Decimal("1"),
                uom="EA",
                unit_price=Decimal("20"),
                amount=Decimal("80"),
            ),
            POItem(
                po_id=po.id,
                line_no=2,
                item_name="L2",
                specification="S2",
                qty=Decimal("6"),
                qty_received=Decimal("6"),
                qty_invoiced=Decimal("3"),
                uom="EA",
                unit_price=Decimal("20"),
                amount=Decimal("120"),
            ),
        ]
    )
    await db.flush()

    progress = await flow_svc.po_progress(db, po.id)
    assert progress["po_number"] == po.po_number
    assert float(progress["pct_received"]) == 80.0
    assert float(progress["pct_paid"]) == 25.0


async def test_create_contract_creates_contract_from_po(seeded_db_session):
    db = seeded_db_session
    user, supplier, _pr, po = await _create_confirmed_po(db)

    contract = await flow_svc.create_contract(
        db,
        user,
        po.id,
        title="Hardware Contract",
        total_amount=Decimal("800.00"),
        signed_date=date(2026, 4, 1),
        effective_date=date(2026, 4, 2),
        expiry_date=date(2027, 4, 1),
        notes="Annual support",
    )

    assert contract.po_id == po.id
    assert contract.supplier_id == supplier.id
    assert contract.currency == po.currency
    assert contract.total_amount == Decimal("800.00")
    today = datetime.now(UTC).date()
    expected_prefix = f"JQPA{today.year:04d}{today.month:02d}{today.day:02d}"
    assert contract.contract_number.startswith(expected_prefix)
    assert contract.notes == "Annual support"
    version = (
        await db.execute(select(ContractVersion).where(ContractVersion.contract_id == contract.id))
    ).scalar_one()
    assert version.version_number == 1
    assert version.change_type == "created"
    assert version.snapshot_json["contract_number"] == contract.contract_number


async def test_create_contract_increments_contract_numbers(seeded_db_session):
    db = seeded_db_session
    user, _supplier, _pr1, po1 = await _create_confirmed_po(db, title="Contract PO 1")
    _user2, _supplier2, _pr2, po2 = await _create_confirmed_po(db, title="Contract PO 2")

    c1 = await flow_svc.create_contract(db, user, po1.id, title="C1", total_amount=Decimal("10"))
    c2 = await flow_svc.create_contract(db, user, po2.id, title="C2", total_amount=Decimal("20"))

    assert c1.contract_number[:-3] == c2.contract_number[:-3]
    assert int(c2.contract_number[-3:]) == int(c1.contract_number[-3:]) + 1


async def test_create_contract_accepts_custom_contract_number(seeded_db_session):
    db = seeded_db_session
    user, _supplier, _pr, po = await _create_confirmed_po(db)

    contract = await flow_svc.create_contract(
        db,
        user,
        po.id,
        title="Custom numbered",
        total_amount=Decimal("500"),
        contract_number="CUSTOM-2026-001",
    )

    assert contract.contract_number == "CUSTOM-2026-001"


async def test_create_contract_rejects_duplicate_custom_number(seeded_db_session):
    db = seeded_db_session
    user, _supplier, _pr1, po1 = await _create_confirmed_po(db, title="DupTest1")
    _u2, _s2, _pr2, po2 = await _create_confirmed_po(db, title="DupTest2")

    await flow_svc.create_contract(
        db, user, po1.id, title="first", total_amount=Decimal("1"), contract_number="DUP-001"
    )

    with pytest.raises(HTTPException) as exc:
        await flow_svc.create_contract(
            db,
            user,
            po2.id,
            title="second",
            total_amount=Decimal("1"),
            contract_number="DUP-001",
        )

    assert exc.value.status_code == 409
    assert exc.value.detail == "contract.number_duplicate"


async def test_suggest_contract_number_follows_jqpa_format(seeded_db_session):
    db = seeded_db_session
    today = datetime.now(UTC).date()
    expected_prefix = f"JQPA{today.year:04d}{today.month:02d}{today.day:02d}"

    suggested = await flow_svc.suggest_contract_number(db)

    assert suggested.startswith(expected_prefix)
    assert len(suggested) == len(expected_prefix) + 3
    assert suggested[-3:].isdigit()


async def test_create_contract_raises_for_missing_po(seeded_db_session):
    db = seeded_db_session
    user = await _get_user(db)

    with pytest.raises(HTTPException) as exc:
        await flow_svc.create_contract(
            db, user, uuid4(), title="Missing", total_amount=Decimal("1")
        )

    assert exc.value.status_code == 404
    assert exc.value.detail == "po.not_found"


async def test_list_contracts_returns_all_when_unfiltered(seeded_db_session):
    db = seeded_db_session
    user, _supplier, _pr1, po1 = await _create_confirmed_po(db, title="All Contracts 1")
    _user2, _supplier2, _pr2, po2 = await _create_confirmed_po(db, title="All Contracts 2")
    c1 = await flow_svc.create_contract(
        db, user, po1.id, title="Contract A", total_amount=Decimal("10")
    )
    c2 = await flow_svc.create_contract(
        db, user, po2.id, title="Contract B", total_amount=Decimal("20")
    )

    contracts = await flow_svc.list_contracts(db)

    assert {contract.id for contract in contracts} >= {c1.id, c2.id}


async def test_list_contracts_filters_by_po_id(seeded_db_session):
    db = seeded_db_session
    user, _supplier, _pr1, po1 = await _create_confirmed_po(db, title="Filtered Contract 1")
    _user2, _supplier2, _pr2, po2 = await _create_confirmed_po(db, title="Filtered Contract 2")
    c1 = await flow_svc.create_contract(db, user, po1.id, title="Keep", total_amount=Decimal("10"))
    await flow_svc.create_contract(db, user, po2.id, title="Skip", total_amount=Decimal("20"))

    contracts = await flow_svc.list_contracts(db, po_id=po1.id)

    assert [contract.id for contract in contracts] == [c1.id]


async def test_update_contract_modifies_fields_and_creates_new_version(seeded_db_session):
    db = seeded_db_session
    user, _supplier, _pr, po = await _create_confirmed_po(db)
    contract = await flow_svc.create_contract(
        db, user, po.id, title="Original", total_amount=Decimal("500")
    )
    original_version = contract.current_version

    updated = await flow_svc.update_contract(
        db,
        user,
        contract.id,
        {
            "title": "Revised Title",
            "total_amount": Decimal("750.00"),
            "change_reason": "Price renegotiation",
        },
    )

    assert updated.title == "Revised Title"
    assert updated.total_amount == Decimal("750.00")
    assert updated.current_version == original_version + 1
    versions = list(
        (
            await db.execute(
                select(ContractVersion).where(ContractVersion.contract_id == contract.id)
            )
        )
        .scalars()
        .all()
    )
    assert len(versions) == 2
    latest = next(v for v in versions if v.version_number == original_version + 1)
    assert latest.change_type == "updated"
    assert latest.change_reason == "Price renegotiation"


async def test_update_contract_noop_when_no_fields_change(seeded_db_session):
    db = seeded_db_session
    user, _supplier, _pr, po = await _create_confirmed_po(db)
    contract = await flow_svc.create_contract(
        db, user, po.id, title="Same", total_amount=Decimal("100")
    )
    before_version = contract.current_version

    result = await flow_svc.update_contract(db, user, contract.id, {})

    assert result.current_version == before_version


async def test_update_contract_rejects_terminated_status(seeded_db_session):
    db = seeded_db_session
    user, _supplier, _pr, po = await _create_confirmed_po(db)
    contract = await flow_svc.create_contract(
        db, user, po.id, title="Lock", total_amount=Decimal("100")
    )
    await flow_svc.transition_contract_status(db, user, contract.id, "terminated", reason="test")

    with pytest.raises(HTTPException) as exc_info:
        await flow_svc.update_contract(db, user, contract.id, {"title": "Should fail"})

    assert exc_info.value.status_code == 409
    assert "not_editable" in str(exc_info.value.detail)


async def test_transition_contract_status_allows_active_to_terminated(seeded_db_session):
    db = seeded_db_session
    user, _supplier, _pr, po = await _create_confirmed_po(db)
    contract = await flow_svc.create_contract(
        db, user, po.id, title="Transition", total_amount=Decimal("100")
    )

    result = await flow_svc.transition_contract_status(
        db, user, contract.id, "terminated", reason="customer request"
    )

    assert result.status == "terminated"
    version = (
        (
            await db.execute(
                select(ContractVersion)
                .where(ContractVersion.contract_id == contract.id)
                .order_by(ContractVersion.version_number.desc())
            )
        )
        .scalars()
        .first()
    )
    assert version.change_type == "terminated"
    assert version.change_reason == "customer request"


async def test_transition_contract_status_blocks_invalid_transition(seeded_db_session):
    db = seeded_db_session
    user, _supplier, _pr, po = await _create_confirmed_po(db)
    contract = await flow_svc.create_contract(
        db, user, po.id, title="Invalid", total_amount=Decimal("100")
    )
    await flow_svc.transition_contract_status(db, user, contract.id, "terminated", reason="a")

    with pytest.raises(HTTPException) as exc_info:
        await flow_svc.transition_contract_status(db, user, contract.id, "active")

    assert exc_info.value.status_code == 409


async def test_delete_contract_removes_contract_and_versions(seeded_db_session):
    db = seeded_db_session
    user, _supplier, _pr, po = await _create_confirmed_po(db)
    contract = await flow_svc.create_contract(
        db, user, po.id, title="Delete me", total_amount=Decimal("100")
    )
    contract_id = contract.id

    await flow_svc.delete_contract(db, user, contract_id)

    remaining = (
        await db.execute(select(Contract).where(Contract.id == contract_id))
    ).scalar_one_or_none()
    assert remaining is None


async def test_create_shipment_creates_items_and_updates_po_partially_received(seeded_db_session):
    db = seeded_db_session
    user, _supplier, _pr, po = await _create_confirmed_po(db)

    shipment = await flow_svc.create_shipment(
        db,
        user,
        po.id,
        items_in=[
            {
                "po_item_id": po.items[0].id,
                "qty_shipped": Decimal("3"),
                "qty_received": Decimal("2"),
            },
            {"po_item_id": po.items[1].id, "qty_shipped": Decimal("1")},
        ],
        carrier="DHL",
        tracking_number="TRK-001",
        expected_date=date(2026, 4, 10),
    )

    refreshed_po = await purchase_svc.get_po(db, po.id)
    assert shipment.po_id == po.id
    assert shipment.batch_no == 1
    assert shipment.is_default is True
    assert shipment.status == "in_transit"
    assert len(shipment.items) == 2
    assert shipment.items[0].qty_received == Decimal("2")
    assert shipment.items[1].qty_received == Decimal("1")
    assert refreshed_po.items[0].qty_received == Decimal("2")
    assert refreshed_po.items[1].qty_received == Decimal("1")
    assert refreshed_po.qty_received == Decimal("3")
    assert refreshed_po.status == "partially_received"


async def test_create_shipment_marks_po_fully_received_when_complete(seeded_db_session):
    db = seeded_db_session
    user, _supplier, _pr, po = await _create_confirmed_po(db)

    shipment = await flow_svc.create_shipment(
        db,
        user,
        po.id,
        items_in=[
            {"po_item_id": po.items[0].id, "qty_shipped": po.items[0].qty},
            {"po_item_id": po.items[1].id, "qty_shipped": po.items[1].qty},
        ],
        actual_date=date(2026, 4, 11),
    )

    refreshed_po = await purchase_svc.get_po(db, po.id)
    assert shipment.status == "arrived"
    assert refreshed_po.qty_received == Decimal("10")
    assert refreshed_po.status == "fully_received"


async def test_create_shipment_increments_batch_number(seeded_db_session):
    db = seeded_db_session
    user, _supplier, _pr, po = await _create_confirmed_po(db)

    s1 = await flow_svc.create_shipment(
        db,
        user,
        po.id,
        items_in=[{"po_item_id": po.items[0].id, "qty_shipped": Decimal("1")}],
    )
    s2 = await flow_svc.create_shipment(
        db,
        user,
        po.id,
        items_in=[{"po_item_id": po.items[1].id, "qty_shipped": Decimal("1")}],
    )

    assert s1.shipment_number.endswith("-S01")
    assert s2.shipment_number.endswith("-S02")
    assert s2.batch_no == 2
    assert s2.is_default is False


async def test_create_shipment_raises_for_invalid_po_item(seeded_db_session):
    db = seeded_db_session
    user, _supplier, _pr, po = await _create_confirmed_po(db)

    with pytest.raises(HTTPException) as exc:
        await flow_svc.create_shipment(
            db,
            user,
            po.id,
            items_in=[{"po_item_id": uuid4(), "qty_shipped": Decimal("1")}],
        )

    assert exc.value.status_code == 422
    assert exc.value.detail == "shipment.invalid_po_item"


async def test_create_shipment_raises_for_missing_po(seeded_db_session):
    db = seeded_db_session
    user = await _get_user(db)

    with pytest.raises(HTTPException) as exc:
        await flow_svc.create_shipment(
            db,
            user,
            uuid4(),
            items_in=[{"po_item_id": uuid4(), "qty_shipped": Decimal("1")}],
        )

    assert exc.value.status_code == 404
    assert exc.value.detail == "po.not_found"


async def test_create_payment_creates_pending_record_without_updating_po_amount_paid(
    seeded_db_session,
):
    db = seeded_db_session
    user, _supplier, _pr, po = await _create_confirmed_po(db)
    contract = await flow_svc.create_contract(
        db, user, po.id, title="Pay test", total_amount=Decimal("1000")
    )

    payment = await flow_svc.create_payment(
        db,
        user,
        po.id,
        amount=Decimal("300"),
        contract_id=contract.id,
        due_date=date(2026, 4, 20),
        notes="Pending payment",
    )

    refreshed_po = await purchase_svc.get_po(db, po.id)
    assert payment.payment_number.endswith("-P01")
    assert payment.installment_no == 1
    assert payment.status == "pending"
    assert payment.payment_date is None
    assert payment.currency == po.currency
    assert payment.contract_id == contract.id
    assert refreshed_po.amount_paid == Decimal("0")


async def test_create_payment_with_payment_date_updates_po_amount_paid(seeded_db_session):
    db = seeded_db_session
    user, _supplier, _pr, po = await _create_confirmed_po(db)
    contract = await flow_svc.create_contract(
        db, user, po.id, title="Pay test", total_amount=Decimal("1000")
    )

    payment = await flow_svc.create_payment(
        db,
        user,
        po.id,
        amount=Decimal("450"),
        contract_id=contract.id,
        payment_date=date(2026, 4, 21),
        transaction_ref="TX-100",
    )

    refreshed_po = await purchase_svc.get_po(db, po.id)
    assert payment.status == "confirmed"
    assert payment.payment_date == date(2026, 4, 21)
    assert payment.contract_id == contract.id
    assert refreshed_po.amount_paid == Decimal("450")


async def test_create_payment_increments_installment_number(seeded_db_session):
    db = seeded_db_session
    user, _supplier, _pr, po = await _create_confirmed_po(db)
    contract = await flow_svc.create_contract(
        db, user, po.id, title="Pay test", total_amount=Decimal("1000")
    )

    p1 = await flow_svc.create_payment(
        db, user, po.id, amount=Decimal("100"), contract_id=contract.id
    )
    p2 = await flow_svc.create_payment(
        db, user, po.id, amount=Decimal("200"), contract_id=contract.id
    )

    assert p1.installment_no == 1
    assert p2.installment_no == 2
    assert p2.payment_number.endswith("-P02")


async def test_create_payment_raises_for_missing_po(seeded_db_session):
    db = seeded_db_session
    user = await _get_user(db)

    with pytest.raises(HTTPException) as exc:
        await flow_svc.create_payment(db, user, uuid4(), amount=Decimal("1"), contract_id=uuid4())

    assert exc.value.status_code == 404
    assert exc.value.detail == "po.not_found"


async def test_create_payment_rejects_contract_not_belonging_to_po(seeded_db_session):
    db = seeded_db_session
    user, _supplier, _pr, po_a = await _create_confirmed_po(db, title="PO A")
    _u, _s, _pr2, po_b = await _create_confirmed_po(db, title="PO B")
    contract_b = await flow_svc.create_contract(
        db, user, po_b.id, title="Belongs to PO B", total_amount=Decimal("500")
    )

    with pytest.raises(HTTPException) as exc:
        await flow_svc.create_payment(
            db, user, po_a.id, amount=Decimal("100"), contract_id=contract_b.id
        )

    assert exc.value.status_code == 409
    assert exc.value.detail == "payment.contract_po_mismatch"


async def test_update_payment_adjusts_po_amount_paid(seeded_db_session):
    db = seeded_db_session
    user, _supplier, _pr, po = await _create_confirmed_po(db)
    contract = await flow_svc.create_contract(
        db, user, po.id, title="Pay test", total_amount=Decimal("1000")
    )
    payment = await flow_svc.create_payment(
        db,
        user,
        po.id,
        amount=Decimal("200"),
        contract_id=contract.id,
        payment_date=date(2026, 4, 22),
    )

    po_before = await purchase_svc.get_po(db, po.id)
    assert po_before.amount_paid == Decimal("200")

    await flow_svc.update_payment(db, user, payment.id, {"amount": Decimal("250")})

    po_after = await purchase_svc.get_po(db, po.id)
    assert po_after.amount_paid == Decimal("250")


async def test_delete_payment_blocks_confirmed_records(seeded_db_session):
    db = seeded_db_session
    user, _supplier, _pr, po = await _create_confirmed_po(db)
    contract = await flow_svc.create_contract(
        db, user, po.id, title="Pay test", total_amount=Decimal("1000")
    )
    payment = await flow_svc.create_payment(
        db,
        user,
        po.id,
        amount=Decimal("300"),
        contract_id=contract.id,
        payment_date=date(2026, 4, 22),
    )

    with pytest.raises(HTTPException) as exc:
        await flow_svc.delete_payment(db, user, payment.id)

    assert exc.value.status_code == 409
    assert exc.value.detail == "payment.cannot_delete_confirmed"


async def test_delete_payment_removes_pending_records(seeded_db_session):
    db = seeded_db_session
    user, _supplier, _pr, po = await _create_confirmed_po(db)
    contract = await flow_svc.create_contract(
        db, user, po.id, title="Pay test", total_amount=Decimal("1000")
    )
    payment = await flow_svc.create_payment(
        db,
        user,
        po.id,
        amount=Decimal("300"),
        contract_id=contract.id,
        due_date=date(2026, 4, 25),
    )

    await flow_svc.delete_payment(db, user, payment.id)

    remaining = (
        await db.execute(select(PaymentRecord).where(PaymentRecord.id == payment.id))
    ).scalar_one_or_none()
    assert remaining is None


async def test_update_payment_can_retroactively_set_contract(seeded_db_session):
    db = seeded_db_session
    user, _supplier, _pr, po = await _create_confirmed_po(db)
    contract = await flow_svc.create_contract(
        db, user, po.id, title="Backfill link", total_amount=Decimal("1000")
    )
    payment = await flow_svc.create_payment(
        db,
        user,
        po.id,
        amount=Decimal("300"),
        contract_id=contract.id,
        due_date=date(2026, 4, 25),
    )
    payment.contract_id = None
    await db.flush()

    updated = await flow_svc.update_payment(db, user, payment.id, {"contract_id": contract.id})

    assert updated.contract_id == contract.id


async def test_update_payment_rejects_contract_from_different_po(seeded_db_session):
    db = seeded_db_session
    user, _s, _pr, po_a = await _create_confirmed_po(db, title="A")
    _u, _s2, _pr2, po_b = await _create_confirmed_po(db, title="B")
    contract_a = await flow_svc.create_contract(
        db, user, po_a.id, title="Belongs to A", total_amount=Decimal("100")
    )
    contract_b = await flow_svc.create_contract(
        db, user, po_b.id, title="Belongs to B", total_amount=Decimal("100")
    )
    payment = await flow_svc.create_payment(
        db,
        user,
        po_a.id,
        amount=Decimal("50"),
        contract_id=contract_a.id,
    )

    with pytest.raises(HTTPException) as exc:
        await flow_svc.update_payment(db, user, payment.id, {"contract_id": contract_b.id})

    assert exc.value.status_code == 409
    assert exc.value.detail == "payment.contract_po_mismatch"


async def test_update_payment_clearing_contract_id_rejected(seeded_db_session):
    db = seeded_db_session
    user, _supplier, _pr, po = await _create_confirmed_po(db)
    contract = await flow_svc.create_contract(
        db, user, po.id, title="Nullify", total_amount=Decimal("100")
    )
    payment = await flow_svc.create_payment(
        db,
        user,
        po.id,
        amount=Decimal("50"),
        contract_id=contract.id,
    )

    with pytest.raises(HTTPException) as exc:
        await flow_svc.update_payment(db, user, payment.id, {"contract_id": None})

    assert exc.value.status_code == 400
    assert exc.value.detail == "payment.contract_required"


async def test_create_invoice_creates_invoice_lines_and_attachments(seeded_db_session):
    db = seeded_db_session
    user, supplier, _pr, po = await _create_confirmed_po(db)
    document = await _create_document(db, user)

    invoice, validations = await flow_svc.create_invoice(
        db,
        user,
        supplier_id=supplier.id,
        invoice_number="INV-001",
        invoice_date=date(2026, 4, 15),
        lines_in=[
            {
                "po_item_id": po.items[0].id,
                "item_name": po.items[0].item_name,
                "qty": Decimal("2"),
                "unit_price": po.items[0].unit_price,
                "tax_amount": Decimal("10"),
            },
            {
                "line_type": "freight",
                "item_name": "Freight",
                "qty": Decimal("1"),
                "unit_price": Decimal("50"),
                "tax_amount": Decimal("5"),
            },
        ],
        attachment_document_ids=[document.id],
        tax_number="TAX-1",
    )

    refreshed_po = await purchase_svc.get_po(db, po.id)
    assert invoice.invoice_number == "INV-001"
    assert invoice.currency == po.currency
    assert invoice.status == "matched"
    assert invoice.is_fully_matched is True
    assert invoice.subtotal == Decimal("250.0000")
    assert invoice.tax_amount == Decimal("15.0000")
    assert invoice.total_amount == Decimal("265.0000")
    assert len(invoice.lines) == 2
    assert len(invoice.attachments) == 1
    assert invoice.attachments[0].document_id == document.id
    assert validations[0]["severity"] == "ok"
    assert validations[1]["po_item_id"] is None
    assert refreshed_po.items[0].qty_invoiced == Decimal("2")
    assert refreshed_po.amount_invoiced == Decimal("200.0000")


async def test_create_invoice_warns_when_line_exceeds_po_remaining(seeded_db_session):
    db = seeded_db_session
    user, supplier, _pr, po = await _create_confirmed_po(db)
    document = await _create_document(db, user, "warn")

    invoice, validations = await flow_svc.create_invoice(
        db,
        user,
        supplier_id=supplier.id,
        invoice_number="INV-WARN",
        invoice_date=date(2026, 4, 16),
        lines_in=[
            {
                "po_item_id": po.items[0].id,
                "item_name": po.items[0].item_name,
                "qty": po.items[0].qty + Decimal("1"),
                "unit_price": po.items[0].unit_price,
            }
        ],
        attachment_document_ids=[document.id],
    )

    assert invoice.status == "pending_match"
    assert invoice.is_fully_matched is False
    assert validations[0]["severity"] == "warn"
    assert validations[0]["message"] == "exceeds_po_remaining"


async def test_create_invoice_requires_attachments(seeded_db_session):
    db = seeded_db_session
    _user, supplier, _pr, po = await _create_confirmed_po(db)
    user = await _get_user(db)

    with pytest.raises(HTTPException) as exc:
        await flow_svc.create_invoice(
            db,
            user,
            supplier_id=supplier.id,
            invoice_number="INV-NO-DOC",
            invoice_date=date(2026, 4, 17),
            lines_in=[
                {
                    "po_item_id": po.items[0].id,
                    "item_name": po.items[0].item_name,
                    "qty": Decimal("1"),
                    "unit_price": po.items[0].unit_price,
                }
            ],
            attachment_document_ids=[],
        )

    assert exc.value.status_code == 422
    assert exc.value.detail == "invoice.attachments_required"


async def test_create_invoice_raises_for_missing_document(seeded_db_session):
    db = seeded_db_session
    user, supplier, _pr, po = await _create_confirmed_po(db)

    with pytest.raises(HTTPException) as exc:
        await flow_svc.create_invoice(
            db,
            user,
            supplier_id=supplier.id,
            invoice_number="INV-BAD-DOC",
            invoice_date=date(2026, 4, 18),
            lines_in=[
                {
                    "po_item_id": po.items[0].id,
                    "item_name": po.items[0].item_name,
                    "qty": Decimal("1"),
                    "unit_price": po.items[0].unit_price,
                }
            ],
            attachment_document_ids=[uuid4()],
        )

    assert exc.value.status_code == 404
    assert exc.value.detail == "invoice.attachment_document_not_found"


async def test_create_invoice_raises_for_missing_supplier(seeded_db_session):
    db = seeded_db_session
    user, _supplier, _pr, po = await _create_confirmed_po(db)
    document = await _create_document(db, user, "missing-supplier")

    with pytest.raises(HTTPException) as exc:
        await flow_svc.create_invoice(
            db,
            user,
            supplier_id=uuid4(),
            invoice_number="INV-BAD-SUP",
            invoice_date=date(2026, 4, 19),
            lines_in=[
                {
                    "po_item_id": po.items[0].id,
                    "item_name": po.items[0].item_name,
                    "qty": Decimal("1"),
                    "unit_price": po.items[0].unit_price,
                }
            ],
            attachment_document_ids=[document.id],
        )

    assert exc.value.status_code == 404
    assert exc.value.detail == "supplier.not_found"
