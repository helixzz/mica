# pyright: reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnusedCallResult=false, reportOptionalMemberAccess=false, reportOptionalSubscript=false
from datetime import UTC, date, datetime
from decimal import Decimal
from io import BytesIO
from uuid import uuid4

import pytest
from fastapi import HTTPException
from openpyxl import load_workbook
from sqlalchemy import select

from app.models import (
    Contract,
    Invoice,
    InvoiceLine,
    InvoiceStatus,
    Item,
    PaymentRecord,
    PaymentStatus,
    POContractLink,
    POItem,
    POStatus,
    PurchaseOrder,
    PurchaseRequisition,
    Supplier,
    User,
)
from app.services import export_excel as svc


def _suffix() -> str:
    return uuid4().hex[:8].upper()


async def _user(db, username: str = "alice") -> User:
    return (await db.execute(select(User).where(User.username == username))).scalar_one()


async def _supplier(db, code: str = "SUP-DELL") -> Supplier:
    return (await db.execute(select(Supplier).where(Supplier.code == code))).scalar_one()


async def _create_po(db, *, actor: User, supplier: Supplier, title: str) -> PurchaseOrder:
    pr = PurchaseRequisition(
        pr_number=f"PR-XL-{_suffix()}",
        title=title,
        business_reason="xlsx export test",
        status="approved",
        requester_id=actor.id,
        company_id=actor.company_id,
        department_id=actor.department_id,
        currency="CNY",
        total_amount=Decimal("350.50"),
    )
    db.add(pr)
    await db.flush()

    po = PurchaseOrder(
        po_number=f"PO-XL-{_suffix()}",
        pr_id=pr.id,
        supplier_id=supplier.id,
        company_id=actor.company_id,
        status=POStatus.CONFIRMED.value,
        currency="CNY",
        total_amount=Decimal("350.50"),
        amount_paid=Decimal("0"),
        created_by_id=actor.id,
    )
    db.add(po)
    await db.flush()
    return po


async def _create_payment(
    db,
    *,
    po: PurchaseOrder,
    payment_number: str,
    amount: str,
    status: str,
    created_at: datetime,
    due_date: date | None,
    payment_date: date | None,
    transaction_ref: str | None,
    notes: str | None,
) -> PaymentRecord:
    payment = PaymentRecord(
        payment_number=payment_number,
        po_id=po.id,
        installment_no=1,
        amount=Decimal(amount),
        currency="CNY",
        due_date=due_date,
        payment_date=payment_date,
        payment_method="bank_transfer",
        transaction_ref=transaction_ref,
        status=status,
        notes=notes,
        created_at=created_at,
    )
    db.add(payment)
    await db.flush()
    return payment


def _payment_numbers(ws) -> list[str]:
    return [
        ws[f"A{row_idx}"].value for row_idx in range(2, ws.max_row + 1) if ws[f"A{row_idx}"].value
    ]


async def test_render_payments_xlsx_returns_workbook_with_payment_rows(seeded_db_session):
    actor = await _user(seeded_db_session)
    supplier = await _supplier(seeded_db_session)
    po = await _create_po(seeded_db_session, actor=actor, supplier=supplier, title="Excel export")
    await _create_payment(
        seeded_db_session,
        po=po,
        payment_number="PAY-OLDER",
        amount="100.00",
        status=PaymentStatus.PENDING.value,
        created_at=datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
        due_date=date(2026, 1, 10),
        payment_date=None,
        transaction_ref="REF-OLD",
        notes="older row",
    )
    await _create_payment(
        seeded_db_session,
        po=po,
        payment_number="PAY-NEWER",
        amount="250.50",
        status=PaymentStatus.CONFIRMED.value,
        created_at=datetime(2026, 1, 2, 9, 0, tzinfo=UTC),
        due_date=None,
        payment_date=date(2026, 1, 11),
        transaction_ref=None,
        notes=None,
    )

    content = await svc.render_payments_xlsx(seeded_db_session)

    assert content.startswith(b"PK")
    workbook = load_workbook(BytesIO(content))
    sheet = workbook.active
    assert sheet.title == "Payments"
    assert sheet["A1"].value == "付款编号 Payment No."
    assert sheet.freeze_panes == "A2"
    assert sheet.auto_filter is not None
    assert sheet["A2"].value == "PAY-NEWER"
    assert sheet["B2"].value == po.po_number
    assert sheet["C2"].value == supplier.name
    assert sheet["G2"].value in (None, "")
    assert sheet["H2"].value == "2026-01-11"
    assert sheet["I2"].value == "bank_transfer"
    assert sheet["J2"].value in (None, "")
    assert sheet["L2"].value in (None, "")
    assert sheet["A3"].value == "PAY-OLDER"
    assert sheet["G3"].value == "2026-01-10"
    assert sheet["H3"].value in (None, "")
    assert sheet["J3"].value == "REF-OLD"
    assert sheet["L3"].value == "older row"
    last_row = sheet.max_row
    assert sheet[f"D{last_row}"].value == "合计 Total"
    assert sheet[f"E{last_row}"].value == pytest.approx(350.5)


async def test_render_payments_xlsx_filters_by_po_id_and_status(seeded_db_session):
    actor = await _user(seeded_db_session)
    supplier = await _supplier(seeded_db_session)
    target_po = await _create_po(
        seeded_db_session, actor=actor, supplier=supplier, title="Target PO"
    )
    other_po = await _create_po(seeded_db_session, actor=actor, supplier=supplier, title="Other PO")
    await _create_payment(
        seeded_db_session,
        po=target_po,
        payment_number="PAY-MATCH",
        amount="88.00",
        status=PaymentStatus.CONFIRMED.value,
        created_at=datetime(2026, 2, 1, 9, 0, tzinfo=UTC),
        due_date=date(2026, 2, 10),
        payment_date=date(2026, 2, 9),
        transaction_ref="REF-MATCH",
        notes="kept",
    )
    await _create_payment(
        seeded_db_session,
        po=target_po,
        payment_number="PAY-WRONG-STATUS",
        amount="99.00",
        status=PaymentStatus.PENDING.value,
        created_at=datetime(2026, 2, 2, 9, 0, tzinfo=UTC),
        due_date=date(2026, 2, 11),
        payment_date=None,
        transaction_ref=None,
        notes=None,
    )
    await _create_payment(
        seeded_db_session,
        po=other_po,
        payment_number="PAY-WRONG-PO",
        amount="77.00",
        status=PaymentStatus.CONFIRMED.value,
        created_at=datetime(2026, 2, 3, 9, 0, tzinfo=UTC),
        due_date=date(2026, 2, 12),
        payment_date=date(2026, 2, 12),
        transaction_ref="REF-OTHER",
        notes="filtered",
    )

    content = await svc.render_payments_xlsx(
        seeded_db_session,
        po_id=str(target_po.id),
        status=PaymentStatus.CONFIRMED.value,
    )

    workbook = load_workbook(BytesIO(content))
    sheet = workbook.active
    assert _payment_numbers(sheet) == ["PAY-MATCH"]
    assert sheet["E4"].value == pytest.approx(88.0)


async def test_render_payments_xlsx_returns_valid_workbook_for_empty_data(seeded_db_session):
    content = await svc.render_payments_xlsx(seeded_db_session, status="missing-status")

    assert content.startswith(b"PK")
    workbook = load_workbook(BytesIO(content))
    sheet = workbook.active
    assert _payment_numbers(sheet) == []
    assert sheet["A1"].value == "付款编号 Payment No."
    assert sheet["D3"].value == "合计 Total"
    assert sheet["E3"].value == 0


# ---------------------------------------------------------------------------
# Procurement ledger export (v1.52.0)
#
# Some other suites commit real rows through the legacy ``seeded_client``
# fixture and the savepoint rollback cannot undo those, so tests that assert
# on the *whole* result set narrow the export to a supplier created inside the
# test, and tests that assert on a single PO filter by that PO's number.
# ---------------------------------------------------------------------------


async def _ledger_supplier(db) -> Supplier:
    supplier = Supplier(
        code=f"SUP-LG-{_suffix()}",
        name=f"Ledger Supplier {_suffix()}",
    )
    db.add(supplier)
    await db.flush()
    return supplier


async def _ledger_pr(
    db,
    *,
    actor: User,
    title: str,
    blank_department: bool = False,
    cost_center_id=None,
) -> PurchaseRequisition:
    pr = PurchaseRequisition(
        pr_number=f"PR-LG-{_suffix()}",
        title=title,
        business_reason="ledger export test",
        status="approved",
        requester_id=actor.id,
        company_id=actor.company_id,
        department_id=None if blank_department else actor.department_id,
        cost_center_id=cost_center_id,
        currency="CNY",
        total_amount=Decimal("1000.00"),
    )
    db.add(pr)
    await db.flush()
    return pr


async def _ledger_po(
    db,
    *,
    actor: User,
    supplier: Supplier,
    pr: PurchaseRequisition,
    items: list[dict],
    status: str = POStatus.CONFIRMED.value,
) -> tuple[PurchaseOrder, list[POItem]]:
    po = PurchaseOrder(
        po_number=f"PO-LG-{_suffix()}",
        pr_id=pr.id,
        supplier_id=supplier.id,
        company_id=actor.company_id,
        status=status,
        currency="CNY",
        total_amount=sum(item["amount"] for item in items),
        amount_paid=Decimal("0"),
        created_by_id=actor.id,
    )
    db.add(po)
    await db.flush()

    created: list[POItem] = []
    for line_no, spec in enumerate(items, start=1):
        po_item = POItem(
            po_id=po.id,
            line_no=line_no,
            item_name=spec["name"],
            qty=spec["qty"],
            uom="EA",
            unit_price=spec["price"],
            amount=spec["amount"],
            qty_received=spec.get("received", Decimal("0")),
            qty_invoiced=spec.get("invoiced", Decimal("0")),
        )
        db.add(po_item)
        created.append(po_item)
    await db.flush()
    return po, created


async def _ledger_contract(db, *, po: PurchaseOrder, number: str) -> Contract:
    contract = Contract(
        contract_number=number,
        po_id=po.id,
        supplier_id=po.supplier_id,
        title=f"Contract {number}",
        currency="CNY",
        total_amount=po.total_amount,
    )
    db.add(contract)
    await db.flush()
    return contract


async def _ledger_invoice_line(db, *, po_item: POItem, supplier_id) -> Invoice:
    invoice = Invoice(
        internal_number=f"INV-LG-{_suffix()}",
        invoice_number=f"FP-{_suffix()}",
        supplier_id=supplier_id,
        invoice_date=date(2026, 3, 1),
        subtotal=po_item.amount,
        tax_amount=Decimal("0"),
        total_amount=po_item.amount,
        currency="CNY",
        status=InvoiceStatus.MATCHED.value,
        is_fully_matched=True,
    )
    db.add(invoice)
    await db.flush()
    line = InvoiceLine(
        invoice_id=invoice.id,
        po_item_id=po_item.id,
        line_no=1,
        item_name=po_item.item_name,
        qty=po_item.qty,
        unit_price=po_item.unit_price,
        subtotal=po_item.amount,
    )
    db.add(line)
    await db.flush()
    return invoice


async def test_collect_procurement_ledger_groups_one_row_per_po_item(seeded_db_session):
    db = seeded_db_session
    actor = await _user(db)
    supplier = await _supplier(db)
    pr = await _ledger_pr(db, actor=actor, title="Ledger grouping")
    po, items = await _ledger_po(
        db,
        actor=actor,
        supplier=supplier,
        pr=pr,
        items=[
            {
                "name": "GPU A",
                "qty": Decimal("400"),
                "price": Decimal("129000"),
                "amount": Decimal("51600000"),
                "received": Decimal("400"),
                "invoiced": Decimal("400"),
            },
            {
                "name": "GPU B",
                "qty": Decimal("80"),
                "price": Decimal("125000"),
                "amount": Decimal("10000000"),
                "received": Decimal("40"),
            },
        ],
    )
    await _ledger_contract(db, po=po, number="ACME202606008002")
    await _ledger_contract(db, po=po, number="ACME202606009003")
    for index, number in enumerate(["PAY-A-001", "PAY-A-002"], start=1):
        db.add(
            PaymentRecord(
                payment_number=number,
                po_id=po.id,
                installment_no=index,
                amount=Decimal("500.00"),
                currency="CNY",
                status=PaymentStatus.PENDING.value,
            )
        )
    await db.flush()

    data = await svc.collect_procurement_ledger(db, actor=actor)

    rows = [row for row in data.ledger_rows if row[PO_COL] == po.po_number]
    assert len(rows) == 2
    first = rows[0]
    # Index by header so adding a column cannot silently invalidate these.
    header_row = _ledger_row(first)
    assert header_row["申请单号 PR No."] == pr.pr_number
    assert header_row["申请标题 PR Title"] == pr.title
    assert header_row["需求说明 Business Reason"] == "ledger export test"
    assert header_row["申请人 Requester"] == actor.display_name
    assert header_row["供应商 Supplier"] == supplier.name
    assert header_row["合同流程号 Contract No."] == "ACME202606008002 / ACME202606009003"
    assert header_row["品名 Item Name"] == "GPU A"
    assert header_row["规格 Specification"] == ""
    assert header_row["SKU 编码 SKU Code"] == ""
    assert header_row["数量 Qty"] == pytest.approx(400.0)
    assert header_row["单价 Unit Price"] == pytest.approx(129000.0)
    assert header_row["总金额 Amount"] == pytest.approx(51600000.0)
    assert header_row["币种 Currency"] == "CNY"
    assert header_row["采购订单号 PO No."] == po.po_number
    assert header_row["采购付款单号 Payment No."] == "PAY-A-001 / PAY-A-002"
    assert header_row["开票状态 Invoice Status"] == "已开票 Invoiced"
    assert header_row["到货状态 Delivery Status"] == "已到货 Delivered"
    assert header_row["OA付款单号 OA Payment No."] == ""
    assert header_row["备注 Notes"] == ""

    second_row = _ledger_row(rows[1])
    assert second_row["序号 No."] == first[0] + 1
    assert second_row["品名 Item Name"] == "GPU B"
    assert second_row["数量 Qty"] == pytest.approx(80.0)
    assert second_row["开票状态 Invoice Status"] == "未开票 Not Invoiced"
    assert second_row["到货状态 Delivery Status"] == "部分到货 Partially Delivered"

    payments = [row for row in data.payment_rows if row[1] == po.po_number]
    assert len(payments) == 2
    assert payments[0][2] == "PAY-A-001"
    assert payments[0][3] == "ACME202606008002 / ACME202606009003"

    await _ledger_invoice_line(db, po_item=items[0], supplier_id=supplier.id)
    data = await svc.collect_procurement_ledger(db, actor=actor)
    invoices = [row for row in data.invoice_rows if row[4] == po.po_number]
    assert len(invoices) == 1
    assert invoices[0][9] == "GPU A"


async def test_collect_procurement_ledger_applies_status_and_keyword_filters(seeded_db_session):
    db = seeded_db_session
    actor = await _user(db)
    supplier = await _ledger_supplier(db)

    kept_pr = await _ledger_pr(db, actor=actor, title="Kept")
    kept_po, _ = await _ledger_po(
        db,
        actor=actor,
        supplier=supplier,
        pr=kept_pr,
        items=[
            {"name": "Kept", "qty": Decimal("1"), "price": Decimal("10"), "amount": Decimal("10")}
        ],
        status=POStatus.CONFIRMED.value,
    )
    other_pr = await _ledger_pr(db, actor=actor, title="Other")
    other_po, _ = await _ledger_po(
        db,
        actor=actor,
        supplier=supplier,
        pr=other_pr,
        items=[
            {"name": "Other", "qty": Decimal("1"), "price": Decimal("10"), "amount": Decimal("10")}
        ],
        status=POStatus.CLOSED.value,
    )

    by_status = await svc.collect_procurement_ledger(
        db, actor=actor, statuses=[POStatus.CONFIRMED.value]
    )
    status_numbers = {row[PO_COL] for row in by_status.ledger_rows}
    assert kept_po.po_number in status_numbers
    assert other_po.po_number not in status_numbers

    by_po_status = await svc.collect_procurement_ledger(
        db, actor=actor, statuses=[POStatus.CLOSED.value]
    )
    closed_numbers = {row[PO_COL] for row in by_po_status.ledger_rows}
    assert other_po.po_number in closed_numbers
    assert kept_po.po_number not in closed_numbers

    by_keyword = await svc.collect_procurement_ledger(db, actor=actor, keyword=kept_pr.pr_number)
    assert {row[PO_COL] for row in by_keyword.ledger_rows} == {kept_po.po_number}

    by_supplier = await svc.collect_procurement_ledger(db, actor=actor, supplier_id=supplier.id)
    assert {row[SUPPLIER_COL] for row in by_supplier.ledger_rows} == {supplier.name}
    assert {row[PO_COL] for row in by_supplier.ledger_rows} == {
        kept_po.po_number,
        other_po.po_number,
    }

    future = await svc.collect_procurement_ledger(db, actor=actor, date_from=date(2099, 1, 1))
    assert future.ledger_rows == []
    assert future.ledger_total == Decimal("0")


async def test_collect_procurement_ledger_scopes_rows_for_dept_manager(seeded_db_session):
    db = seeded_db_session
    alice = await _user(db)
    bob = (await db.execute(select(User).where(User.username == "bob"))).scalar_one()
    supplier = await _ledger_supplier(db)

    own_pr = await _ledger_pr(db, actor=alice, title="Bob dept")
    own_po, _ = await _ledger_po(
        db,
        actor=alice,
        supplier=supplier,
        pr=own_pr,
        items=[
            {
                "name": "Visible",
                "qty": Decimal("1"),
                "price": Decimal("10"),
                "amount": Decimal("10"),
            }
        ],
    )
    hidden_pr = await _ledger_pr(db, actor=alice, title="Another dept", blank_department=True)
    hidden_po, _ = await _ledger_po(
        db,
        actor=alice,
        supplier=supplier,
        pr=hidden_pr,
        items=[
            {"name": "Hidden", "qty": Decimal("1"), "price": Decimal("10"), "amount": Decimal("10")}
        ],
    )

    scoped = await svc.collect_procurement_ledger(db, actor=bob, supplier_id=supplier.id)
    assert [row[PO_COL] for row in scoped.ledger_rows] == [own_po.po_number]

    unscoped = await svc.collect_procurement_ledger(db, actor=alice, supplier_id=supplier.id)
    assert {row[PO_COL] for row in unscoped.ledger_rows} == {own_po.po_number, hidden_po.po_number}


async def test_collect_procurement_ledger_blanks_amounts_when_field_denied(
    seeded_db_session, monkeypatch
):
    db = seeded_db_session
    actor = await _user(db)
    supplier = await _supplier(db)
    pr = await _ledger_pr(db, actor=actor, title="Denied fields")
    po, _ = await _ledger_po(
        db,
        actor=actor,
        supplier=supplier,
        pr=pr,
        items=[
            {"name": "X", "qty": Decimal("2"), "price": Decimal("50"), "amount": Decimal("100")}
        ],
    )
    db.add(
        PaymentRecord(
            payment_number="PAY-DENIED-001",
            po_id=po.id,
            installment_no=1,
            amount=Decimal("100.00"),
            currency="CNY",
            status=PaymentStatus.PENDING.value,
        )
    )
    await db.flush()

    async def _deny_all(*args, **kwargs):
        return set()

    monkeypatch.setattr(svc, "check_field_access", _deny_all)
    data = await svc.collect_procurement_ledger(db, actor=actor)

    row = next(
        r
        for r in data.ledger_rows
        if r[svc.LEDGER_HEADERS.index("采购订单号 PO No.")] == po.po_number
    )
    denied = _ledger_row(row)
    assert denied["单价 Unit Price"] == ""
    assert denied["总金额 Amount"] == ""
    assert denied["采购付款单号 Payment No."] == ""
    # PR text is gated by a second kind, which the blanket denial also blocks.
    assert denied["申请标题 PR Title"] == ""
    assert denied["需求说明 Business Reason"] == ""
    # Non-gated descriptive columns stay visible.
    assert denied["品名 Item Name"] == "X"
    assert data.amount_visible is False

    payments = [r for r in data.payment_rows if r[1] == po.po_number]
    assert len(payments) == 1
    payment_row = payments[0]
    assert payment_row[2] == ""
    assert payment_row[5] == ""
    assert payment_row[7] == ""
    assert payment_row[4] == 1


async def test_collect_procurement_ledger_raises_when_exceeding_max_rows(seeded_db_session):
    db = seeded_db_session
    actor = await _user(db)
    supplier = await _supplier(db)
    pr = await _ledger_pr(db, actor=actor, title="Too many")
    await _ledger_po(
        db,
        actor=actor,
        supplier=supplier,
        pr=pr,
        items=[
            {"name": "A", "qty": Decimal("1"), "price": Decimal("1"), "amount": Decimal("1")},
            {"name": "B", "qty": Decimal("1"), "price": Decimal("1"), "amount": Decimal("1")},
        ],
    )

    with pytest.raises(HTTPException) as excinfo:
        await svc.collect_procurement_ledger(db, actor=actor, max_rows=1)

    assert excinfo.value.status_code == 400
    assert excinfo.value.detail == "export.too_many_rows"


async def test_ledger_to_xlsx_has_three_sheets_and_total_row(seeded_db_session):
    db = seeded_db_session
    actor = await _user(db)
    supplier = await _ledger_supplier(db)
    pr = await _ledger_pr(db, actor=actor, title="Workbook")
    po, items = await _ledger_po(
        db,
        actor=actor,
        supplier=supplier,
        pr=pr,
        items=[
            {
                "name": "A",
                "qty": Decimal("1"),
                "price": Decimal("250.25"),
                "amount": Decimal("250.25"),
            },
            {"name": "B", "qty": Decimal("2"), "price": Decimal("100"), "amount": Decimal("200")},
        ],
    )
    await _ledger_contract(db, po=po, number="CT-LEDGER-1")
    await _ledger_invoice_line(db, po_item=items[1], supplier_id=supplier.id)

    data = await svc.collect_procurement_ledger(db, actor=actor, supplier_id=supplier.id)
    content = svc.ledger_to_xlsx(data)

    assert content.startswith(b"PK")
    workbook = load_workbook(BytesIO(content))
    assert workbook.sheetnames == [
        svc.LEDGER_SHEET_TITLE,
        svc.PAYMENT_SHEET_TITLE,
        svc.INVOICE_SHEET_TITLE,
    ]

    ledger = workbook[svc.LEDGER_SHEET_TITLE]
    assert ledger["A1"].value == "序号 No."
    assert [cell.value for cell in ledger[1]] == svc.LEDGER_HEADERS
    assert ledger.freeze_panes == "A2"
    total_row = ledger.max_row
    assert ledger.cell(row=total_row, column=svc.LEDGER_TOTAL_COLUMN).value == "合计 Total"
    assert ledger.cell(row=total_row, column=svc.LEDGER_TOTAL_COLUMN + 1).value == pytest.approx(
        450.25
    )
    assert ledger.cell(row=total_row, column=svc.LEDGER_TOTAL_COLUMN + 1).value == (
        sum(row[svc.LEDGER_TOTAL_COLUMN] for row in data.ledger_rows)
    )

    invoice_sheet = workbook[svc.INVOICE_SHEET_TITLE]
    assert invoice_sheet["E2"].value == po.po_number


async def test_ledger_to_csv_emits_bom_and_main_table_only(seeded_db_session):
    db = seeded_db_session
    actor = await _user(db)
    supplier = await _supplier(db)
    pr = await _ledger_pr(db, actor=actor, title="CSV")
    po, _ = await _ledger_po(
        db,
        actor=actor,
        supplier=supplier,
        pr=pr,
        items=[{"name": "A", "qty": Decimal("3"), "price": Decimal("10"), "amount": Decimal("30")}],
    )

    data = await svc.collect_procurement_ledger(db, actor=actor)
    payload = svc.ledger_to_csv(data)

    assert payload.startswith(b"\xef\xbb\xbf")
    text = payload.decode("utf-8-sig")
    assert text.splitlines()[0].startswith("序号 No.,")
    assert po.po_number in text
    assert "合计 Total" in text


def test_ledger_filename_uses_export_format():
    assert svc.ledger_filename("csv").endswith(".csv")
    assert svc.ledger_filename("xlsx").endswith(".xlsx")
    assert "procurement-ledger" in svc.ledger_filename("xlsx")


# Ledger main-sheet column indices, resolved from the declaration itself.
PO_COL = svc.LEDGER_HEADERS.index("采购订单号 PO No.")
CONTRACT_COL = svc.LEDGER_HEADERS.index("合同流程号 Contract No.")
SUPPLIER_COL = svc.LEDGER_HEADERS.index("供应商 Supplier")


def _ledger_row(row: list) -> dict[str, object]:
    """Map a ledger row to {header: value} so assertions survive column changes."""
    assert len(row) == len(svc.LEDGER_COLUMNS), (
        f"ledger row has {len(row)} values but LEDGER_COLUMNS declares "
        f"{len(svc.LEDGER_COLUMNS)}: the row builder and the column list drifted"
    )
    return dict(zip(svc.LEDGER_HEADERS, row, strict=True))


def _formula_cells(content: bytes) -> list[tuple[str, str, object]]:
    """Return every cell the spreadsheet engine would treat as a formula."""
    workbook = load_workbook(BytesIO(content))
    found: list[tuple[str, str, object]] = []
    for sheet in workbook.worksheets:
        for row in sheet.iter_rows():
            for cell in row:
                if cell.data_type == "f":
                    found.append((sheet.title, cell.coordinate, cell.value))
    return found


async def test_ledger_xlsx_neutralizes_formula_like_text(seeded_db_session):
    """User-controlled text must never be stored as an evaluable formula."""
    db = seeded_db_session
    actor = await _user(db)
    admin = (await db.execute(select(User).where(User.username == "admin"))).scalar_one()
    supplier = await _ledger_supplier(db)
    supplier.name = "=cmd|'/C calc'!A0"
    pr = await _ledger_pr(db, actor=actor, title="=1+1")
    po, items = await _ledger_po(
        db,
        actor=actor,
        supplier=supplier,
        pr=pr,
        items=[
            {
                "name": '=HYPERLINK("http://evil","x")',
                "qty": Decimal("1"),
                "price": Decimal("10"),
                "amount": Decimal("10"),
            }
        ],
    )
    await _ledger_contract(db, po=po, number="=2+2")
    db.add(
        PaymentRecord(
            payment_number="=3+3",
            po_id=po.id,
            installment_no=1,
            amount=Decimal("10.00"),
            currency="CNY",
            status=PaymentStatus.PENDING.value,
            payment_method="=5+5",
            transaction_ref="=6+6",
            notes="=4+4",
        )
    )
    await db.flush()
    invoice = await _ledger_invoice_line(db, po_item=items[0], supplier_id=supplier.id)
    invoice.internal_number = "=9+9"
    invoice.invoice_number = "=10+10"
    await db.flush()

    # it_buyer: gated columns are blanked, but must still never be formulas.
    gated = await svc.collect_procurement_ledger(db, actor=actor, supplier_id=supplier.id)
    assert _formula_cells(svc.ledger_to_xlsx(gated)) == []

    # admin: every payload reaches a cell, so the hardening is actually tested.
    data = await svc.collect_procurement_ledger(db, actor=admin, supplier_id=supplier.id)
    content = svc.ledger_to_xlsx(data)

    assert _formula_cells(content) == []

    workbook = load_workbook(BytesIO(content))
    ledger = workbook[svc.LEDGER_SHEET_TITLE]
    # row 2 is not necessarily ours (the export is unfiltered by supplier here)
    supplier_cell = next(
        ledger.cell(row=row, column=SUPPLIER_COL + 1)
        for row in range(2, ledger.max_row + 1)
        if ledger.cell(row=row, column=SUPPLIER_COL + 1).value == "=cmd|'/C calc'!A0"
    )
    assert supplier_cell.data_type == "s"

    invoice_sheet = workbook[svc.INVOICE_SHEET_TITLE]
    assert invoice_sheet["B2"].value == "=9+9"  # internal_number
    assert invoice_sheet["B2"].data_type == "s"
    assert invoice_sheet["C2"].value == "=10+10"  # invoice_number
    assert invoice_sheet["C2"].data_type == "s"
    assert invoice_sheet["J2"].value == '=HYPERLINK("http://evil","x")'  # item_name
    assert invoice_sheet["J2"].data_type == "s"

    payment_sheet = workbook[svc.PAYMENT_SHEET_TITLE]
    assert payment_sheet["K2"].value == "=5+5"  # payment_method
    assert payment_sheet["K2"].data_type == "s"
    assert payment_sheet["L2"].value == "=6+6"  # transaction_ref
    assert payment_sheet["M2"].value == "=4+4"  # notes


async def test_ledger_csv_escapes_formula_like_text(seeded_db_session):
    db = seeded_db_session
    actor = await _user(db)
    supplier = await _ledger_supplier(db)
    supplier.name = "=1+1"
    pr = await _ledger_pr(db, actor=actor, title="CSV injection")
    po, _ = await _ledger_po(
        db,
        actor=actor,
        supplier=supplier,
        pr=pr,
        items=[{"name": "X", "qty": Decimal("1"), "price": Decimal("10"), "amount": Decimal("10")}],
    )
    await _ledger_contract(db, po=po, number="@SUM(1)")
    await db.flush()

    data = await svc.collect_procurement_ledger(db, actor=actor, supplier_id=supplier.id)
    text = svc.ledger_to_csv(data).decode("utf-8-sig")

    assert "'=1+1" in text  # supplier name
    assert "'@SUM(1)" in text  # contract number

    # System-generated values and numbers must NOT be over-prefixed.
    assert f"'{po.po_number}" not in text
    assert po.po_number in text
    assert "'10.0" not in text
    assert "'CNY" not in text
    assert "'未开票" not in text


async def test_ledger_payment_sheet_gates_notes_via_static_fallback(seeded_db_session):
    """Exercise the real FIELD_PERMISSIONS fallback, not a monkeypatch."""
    db = seeded_db_session
    alice = await _user(db)
    admin = (await db.execute(select(User).where(User.username == "admin"))).scalar_one()
    supplier = await _ledger_supplier(db)
    pr = await _ledger_pr(db, actor=alice, title="Notes gating")
    po, _ = await _ledger_po(
        db,
        actor=alice,
        supplier=supplier,
        pr=pr,
        items=[{"name": "X", "qty": Decimal("1"), "price": Decimal("10"), "amount": Decimal("10")}],
    )
    db.add(
        PaymentRecord(
            payment_number="PAY-NOTES-001",
            po_id=po.id,
            installment_no=1,
            amount=Decimal("10.00"),
            currency="CNY",
            status=PaymentStatus.PENDING.value,
            payment_method="wire",
            transaction_ref="TRX-1",
            notes="SECRET-NOTE-777",
        )
    )
    await db.flush()

    # Ledger payment-sheet order:
    # 0 seq, 1 PO, 2 payment no, 3 contract, 4 installment, 5 amount, 6 currency,
    # 7 status, 8 due date, 9 paid date, 10 method, 11 ref, 12 notes
    it_buyer = await svc.collect_procurement_ledger(db, actor=alice, supplier_id=supplier.id)
    assert it_buyer.payment_rows[0][10] == ""  # payment_method
    assert it_buyer.payment_rows[0][11] == ""  # transaction_ref
    assert it_buyer.payment_rows[0][12] == ""  # notes
    assert it_buyer.payment_rows[0][5] == pytest.approx(10.0)  # amount still visible

    auditor = await svc.collect_procurement_ledger(db, actor=admin, supplier_id=supplier.id)
    assert auditor.payment_rows[0][10] == "wire"
    assert auditor.payment_rows[0][11] == "TRX-1"
    assert auditor.payment_rows[0][12] == "SECRET-NOTE-777"


async def test_ledger_contract_cell_is_sorted_not_insertion_ordered(seeded_db_session):
    db = seeded_db_session
    actor = await _user(db)
    supplier = await _ledger_supplier(db)
    pr = await _ledger_pr(db, actor=actor, title="Contract ordering")
    po, _ = await _ledger_po(
        db,
        actor=actor,
        supplier=supplier,
        pr=pr,
        items=[{"name": "X", "qty": Decimal("1"), "price": Decimal("10"), "amount": Decimal("10")}],
    )
    await _ledger_contract(db, po=po, number="ZZZ-LAST")
    await _ledger_contract(db, po=po, number="AAA-FIRST")

    data = await svc.collect_procurement_ledger(db, actor=actor, supplier_id=supplier.id)

    assert data.ledger_rows[0][CONTRACT_COL] == "AAA-FIRST / ZZZ-LAST"


async def test_ledger_contract_cell_is_sorted_across_both_link_sources(seeded_db_session):
    """A contract attached via po_contract_links must sort with the primary ones."""
    db = seeded_db_session
    actor = await _user(db)
    supplier = await _ledger_supplier(db)
    items = [{"name": "X", "qty": Decimal("1"), "price": Decimal("10"), "amount": Decimal("10")}]

    # Target PO owns the alphabetically-LAST contract through contracts.po_id.
    target_pr = await _ledger_pr(db, actor=actor, title="Target")
    target_po, _ = await _ledger_po(db, actor=actor, supplier=supplier, pr=target_pr, items=items)
    await _ledger_contract(db, po=target_po, number="ZZZ-LAST")

    # A different PO owns the alphabetically-FIRST contract, which is attached to
    # the target PO only through po_contract_links (so it is merged second).
    other_pr = await _ledger_pr(db, actor=actor, title="Other")
    other_po, _ = await _ledger_po(db, actor=actor, supplier=supplier, pr=other_pr, items=items)
    linked_contract = await _ledger_contract(db, po=other_po, number="AAA-FIRST")
    db.add(POContractLink(po_id=target_po.id, contract_id=linked_contract.id))
    await db.flush()

    data = await svc.collect_procurement_ledger(db, actor=actor, supplier_id=supplier.id)
    row = next(r for r in data.ledger_rows if r[PO_COL] == target_po.po_number)

    assert row[CONTRACT_COL] == "AAA-FIRST / ZZZ-LAST"


async def test_ledger_contract_cell_order_is_stable_across_repeated_exports(seeded_db_session):
    db = seeded_db_session
    actor = await _user(db)
    supplier = await _ledger_supplier(db)
    pr = await _ledger_pr(db, actor=actor, title="Stable ordering")
    po, _ = await _ledger_po(
        db,
        actor=actor,
        supplier=supplier,
        pr=pr,
        items=[{"name": "X", "qty": Decimal("1"), "price": Decimal("10"), "amount": Decimal("10")}],
    )
    for number in ("MMM-MID", "ZZZ-LAST", "AAA-FIRST"):
        await _ledger_contract(db, po=po, number=number)

    cells = {
        (
            await svc.collect_procurement_ledger(db, actor=actor, supplier_id=supplier.id)
        ).ledger_rows[0][CONTRACT_COL]
        for _ in range(5)
    }

    assert cells == {"AAA-FIRST / MMM-MID / ZZZ-LAST"}


async def test_payments_and_rfq_exports_neutralize_formulas(seeded_db_session):
    """The two pre-existing exporters share the same hardening.

    Uses ``admin`` so the payment method / ref / notes cells are not blanked by
    field-level gating and the formula payloads actually reach the workbook.
    """
    db = seeded_db_session
    actor = await _user(db)
    admin = (await db.execute(select(User).where(User.username == "admin"))).scalar_one()
    supplier = await _ledger_supplier(db)
    supplier.name = "=1+1"
    pr = await _ledger_pr(db, actor=actor, title="=2+2")
    po, _ = await _ledger_po(
        db,
        actor=actor,
        supplier=supplier,
        pr=pr,
        items=[
            {"name": "=3+3", "qty": Decimal("1"), "price": Decimal("10"), "amount": Decimal("10")}
        ],
    )
    db.add(
        PaymentRecord(
            payment_number="=4+4",
            po_id=po.id,
            installment_no=1,
            amount=Decimal("10.00"),
            currency="CNY",
            status=PaymentStatus.PENDING.value,
            payment_method="=5+5",
            transaction_ref="=6+6",
            notes="=7+7",
        )
    )
    await db.flush()

    await db.flush()

    # admin: no field gating, so the formula payloads reach the cells.
    payments_content = await svc.render_payments_xlsx(db, actor=admin)
    assert _formula_cells(payments_content) == []
    payments_sheet = load_workbook(BytesIO(payments_content))["Payments"]
    assert payments_sheet["I2"].value == "=5+5"  # payment_method
    assert payments_sheet["J2"].value == "=6+6"  # transaction_ref
    assert payments_sheet["L2"].value == "=7+7"  # notes
    assert payments_sheet["I2"].data_type == "s"

    rfq_content, _ = await svc.render_rfq_sheet_xlsx(db, str(pr.id))
    assert _formula_cells(rfq_content) == []


async def test_ledger_rows_match_the_declared_column_count(seeded_db_session):
    """Guard against the row builder and LEDGER_COLUMNS drifting apart."""
    db = seeded_db_session
    actor = await _user(db)
    supplier = await _ledger_supplier(db)
    pr = await _ledger_pr(db, actor=actor, title="Column count")
    po, items = await _ledger_po(
        db,
        actor=actor,
        supplier=supplier,
        pr=pr,
        items=[
            {
                "name": "服务器",
                "qty": Decimal("2"),
                "price": Decimal("1000"),
                "amount": Decimal("2000"),
            }
        ],
    )
    await _ledger_contract(db, po=po, number="CT-COUNT-1")
    item = (await db.execute(__import__("sqlalchemy").select(Item).limit(1))).scalars().first()
    if item is not None:
        items[0].item_id = item.id
        await db.flush()

    data = await svc.collect_procurement_ledger(db, actor=actor, supplier_id=supplier.id)

    assert len(svc.LEDGER_HEADERS) == len(svc.LEDGER_COLUMNS)
    assert len(svc.LEDGER_COL_WIDTHS) == len(svc.LEDGER_COLUMNS)
    assert data.ledger_rows, "expected at least one ledger row"
    for row in data.ledger_rows:
        assert len(row) == len(svc.LEDGER_COLUMNS)

    # The newly requested columns are populated and readable.
    mapped = _ledger_row(data.ledger_rows[0])
    assert mapped["申请标题 PR Title"] == pr.title
    assert mapped["需求说明 Business Reason"] == "ledger export test"
    assert mapped["品名 Item Name"] == "服务器"
    if item is not None:
        assert mapped["SKU 编码 SKU Code"] == item.code
