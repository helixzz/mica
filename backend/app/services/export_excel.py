from __future__ import annotations

import asyncio
import csv
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from decimal import Decimal
from io import BytesIO, StringIO
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.cerbos_client import check_field_access
from app.models import (
    Contract,
    Invoice,
    InvoiceLine,
    PaymentRecord,
    POContractLink,
    PurchaseOrder,
    PurchaseRequisition,
    Supplier,
    User,
)

_HEADER_FILL = PatternFill(start_color="8B5E3C", end_color="8B5E3C", fill_type="solid")
_HEADER_FONT = Font(name="Arial", bold=True, color="FFFFFF", size=11)
_ZEBRA_FILL = PatternFill(start_color="F7F6F5", end_color="F7F6F5", fill_type="solid")

# Spreadsheet apps treat text starting with one of these characters as a
# formula (or a DDE payload) rather than as data.
_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def _neutralize_workbook(wb: Workbook) -> None:
    """Store formula-looking text as literal strings.

    openpyxl writes any string starting with ``=`` with ``data_type == "f"``,
    which Excel then *evaluates*. Supplier names, contract numbers, invoice
    numbers and notes are user-controlled, so they must never end up as a
    formula in a generated document.
    """
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for cell in row:
                value = cell.value
                if isinstance(value, str) and value.startswith(_FORMULA_PREFIXES):
                    cell.data_type = "s"


def _csv_safe(value: Any) -> Any:
    """Prefix formula-looking text so spreadsheet apps treat it as text.

    Unlike XLSX, a CSV has no cell type information: Excel/LibreOffice decide
    from the leading character on import, so the value has to be neutralised.
    """
    if isinstance(value, str) and value.startswith(_FORMULA_PREFIXES):
        return "'" + value
    return value


def _workbook_bytes(wb: Workbook) -> bytes:
    _neutralize_workbook(wb)
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


async def render_payments_xlsx(
    db: AsyncSession,
    *,
    actor: User | None = None,
    po_id: str | None = None,
    status: str | None = None,
) -> bytes:
    """Render the payments workbook.

    When *actor* is given, row-level scoping and field-level gating are
    applied — callers serving HTTP requests must pass it, otherwise every
    payment in the system is exported regardless of who asked.
    """
    stmt = select(PaymentRecord).options(
        selectinload(PaymentRecord.po).selectinload(PurchaseOrder.supplier)
    )
    if po_id:
        stmt = stmt.where(PaymentRecord.po_id == po_id)
    if status:
        stmt = stmt.where(PaymentRecord.status == status)
    if actor is not None:
        from app.core.scoping import visible_po_id_subquery

        visible_po_ids = await visible_po_id_subquery(db, actor)
        if visible_po_ids is not None:
            stmt = stmt.where(PaymentRecord.po_id.in_(visible_po_ids))
    stmt = stmt.order_by(PaymentRecord.created_at.desc())
    payments: Sequence[PaymentRecord] = (await db.execute(stmt)).scalars().all()

    allowed: set[str] | None = None
    if actor is not None:
        allowed = await _allowed_fields(actor, "payment_record", _PAYMENT_SHEET_FIELDS)

    wb = Workbook()
    ws = wb.active
    ws.title = "Payments"

    headers = [
        "付款编号 Payment No.",
        "采购订单 PO No.",
        "供应商 Supplier",
        "分期 Installment",
        "金额 Amount",
        "币种 Currency",
        "应付日期 Due Date",
        "实付日期 Paid Date",
        "付款方式 Method",
        "交易号 Ref",
        "状态 Status",
        "备注 Notes",
        "创建时间 Created",
    ]
    ws.append(headers)
    for col_idx, _ in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=col_idx)
        cell.fill = _HEADER_FILL
        cell.font = _HEADER_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center")

    for row_idx, p in enumerate(payments, start=2):
        supplier_name = p.po.supplier.name if p.po and p.po.supplier else "-"
        po_number = p.po.po_number if p.po else "-"
        rows: list[Any] = [
            p.payment_number,
            po_number,
            supplier_name,
            p.installment_no,
            float(p.amount),
            p.currency,
            p.due_date.isoformat() if p.due_date else "",
            p.payment_date.isoformat() if p.payment_date else "",
            p.payment_method,
            p.transaction_ref or "",
            p.status,
            p.notes or "",
            p.created_at.strftime("%Y-%m-%d %H:%M") if p.created_at else "",
        ]
        if allowed is not None:
            rows[8] = _gated(allowed, "payment_method", rows[8])
            rows[9] = _gated(allowed, "transaction_ref", rows[9])
            rows[11] = _gated(allowed, "notes", rows[11])
        ws.append(rows)
        if row_idx % 2 == 0:
            for col_idx in range(1, len(headers) + 1):
                ws.cell(row=row_idx, column=col_idx).fill = _ZEBRA_FILL

    col_widths = [20, 18, 28, 12, 14, 10, 14, 14, 16, 20, 14, 24, 18]
    for idx, w in enumerate(col_widths, start=1):
        ws.column_dimensions[get_column_letter(idx)].width = w

    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions

    ws.cell(row=len(payments) + 3, column=4).value = "合计 Total"
    ws.cell(row=len(payments) + 3, column=4).font = Font(bold=True)
    ws.cell(row=len(payments) + 3, column=5).value = sum(float(p.amount) for p in payments)
    ws.cell(row=len(payments) + 3, column=5).font = Font(bold=True)

    return _workbook_bytes(wb)


async def render_rfq_sheet_xlsx(
    db: AsyncSession,
    pr_id: str,
) -> tuple[bytes, str]:
    from datetime import UTC, datetime

    pr = (
        await db.execute(
            select(PurchaseRequisition)
            .where(PurchaseRequisition.id == pr_id)
            .options(
                selectinload(PurchaseRequisition.items),
                selectinload(PurchaseRequisition.company),
            )
        )
    ).scalar_one_or_none()
    if pr is None:
        raise ValueError("pr.not_found")

    wb = Workbook()
    ws = wb.active
    ws.title = "RFQ Sheet"

    ws.merge_cells("A1:H1")
    title_cell = ws.cell(row=1, column=1)
    title_cell.value = "询价表 Request for Quotation"
    title_cell.font = Font(name="Arial", bold=True, size=14)
    title_cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 28

    info_rows = [
        (
            "公司 Company:",
            pr.company.name_zh if pr.company else "-",
            "日期 Date:",
            datetime.now(UTC).strftime("%Y-%m-%d"),
        ),
        ("币种 Currency:", pr.currency, "", ""),
    ]
    for i, (l1, v1, l2, v2) in enumerate(info_rows, start=3):
        ws.cell(row=i, column=1, value=l1).font = Font(bold=True, size=10)
        ws.cell(row=i, column=2, value=v1)
        if l2:
            ws.cell(row=i, column=4, value=l2).font = Font(bold=True, size=10)
            ws.cell(row=i, column=5, value=v2)

    header_row = 6
    headers = [
        "行号\nLine",
        "物料名称\nItem Name",
        "规格描述\nSpecification",
        "数量\nQty",
        "单位\nUOM",
        "报价单价（供应商填写）\nUnit Price",
        "交期（供应商填写）\nLead Time",
        "备注（供应商填写）\nRemarks",
    ]
    for col_idx, h in enumerate(headers, start=1):
        cell = ws.cell(row=header_row, column=col_idx, value=h)
        cell.fill = _HEADER_FILL
        cell.font = _HEADER_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    ws.row_dimensions[header_row].height = 36

    for row_idx, item in enumerate(pr.items, start=header_row + 1):
        ws.append(
            [
                item.line_no,
                item.item_name,
                item.specification or "",
                float(item.qty),
                item.uom,
                "",
                "",
                "",
            ]
        )
        if (row_idx - header_row) % 2 == 0:
            for col_idx in range(1, len(headers) + 1):
                ws.cell(row=row_idx, column=col_idx).fill = _ZEBRA_FILL

    col_widths = [8, 36, 40, 10, 8, 18, 16, 24]
    for idx, w in enumerate(col_widths, start=1):
        ws.column_dimensions[get_column_letter(idx)].width = w

    ws.freeze_panes = f"A{header_row + 1}"

    footer_row = header_row + len(pr.items) + 3
    ws.cell(row=footer_row, column=1, value="供应商签章 Supplier Stamp:").font = Font(
        bold=True, size=10
    )
    ws.cell(row=footer_row, column=6, value="日期 Date:").font = Font(bold=True, size=10)
    ws.cell(
        row=footer_row + 2,
        column=1,
        value='注：请在"报价单价""交期""备注"列填写后回传。如有任何疑问请联系采购负责人。',
    )
    ref_cell = ws.cell(row=footer_row + 4, column=1, value=f"参考编号 Ref: {pr.pr_number}")
    ref_cell.font = Font(name="Arial", color="888888", size=9)

    buf = BytesIO()
    _neutralize_workbook(wb)
    wb.save(buf)
    filename = f"RFQ-{pr.pr_number}-{datetime.now(UTC).strftime('%Y%m%d')}.xlsx"
    return buf.getvalue(), filename


# --------------------------------------------------------------------------
# Procurement ledger export (v1.52.0)
#
# A cross-entity "采购台账" workbook: one row per PO line item, enriched with
# its PR header, contract numbers, payment numbers and derived progress
# statuses. Two companion sheets carry the underlying payment and invoice-line
# detail so nothing is lost by keeping the main sheet at POItem granularity.
#
# Access control (AGENTS §5.13 / §5.19):
#   * row level  — ``core.scoping.visible_po_id_subquery``
#   * field level — Cerbos ``check_field_access`` (one check per resource kind,
#     never per row, so an export costs a constant number of HTTP calls)
# --------------------------------------------------------------------------

LEDGER_SHEET_TITLE = "采购台账 Ledger"
PAYMENT_SHEET_TITLE = "付款明细 Payments"
INVOICE_SHEET_TITLE = "发票明细 Invoice Lines"

LEDGER_HEADERS: list[str] = [
    "序号 No.",
    "申请单号 PR No.",
    "申请人 Requester",
    "成本中心 Cost Center",
    "公司 Company",
    "供应商 Supplier",
    "合同流程号 Contract No.",
    "数量 Qty",
    "单价 Unit Price",
    "总金额 Amount",
    "币种 Currency",
    "采购订单号 PO No.",
    "采购付款单号 Payment No.",
    "开票状态 Invoice Status",
    "到货状态 Delivery Status",
    "OA付款单号 OA Payment No.",
    "备注 Notes",
]

PAYMENT_HEADERS: list[str] = [
    "序号 No.",
    "采购订单号 PO No.",
    "付款单号 Payment No.",
    "合同流程号 Contract No.",
    "期次 Installment",
    "金额 Amount",
    "币种 Currency",
    "状态 Status",
    "应付日期 Due Date",
    "实付日期 Paid Date",
    "付款方式 Method",
    "流水号 Ref",
    "备注 Notes",
]

INVOICE_HEADERS: list[str] = [
    "序号 No.",
    "内部编号 Internal No.",
    "发票号码 Invoice No.",
    "供应商 Supplier",
    "关联采购订单号 PO No.",
    "发票日期 Invoice Date",
    "金额 Amount",
    "币种 Currency",
    "状态 Status",
    "行物料 Line Item",
    "行数量 Line Qty",
    "行金额 Line Amount",
]

LEDGER_COL_WIDTHS = [6, 16, 18, 14, 28, 30, 22, 10, 14, 16, 8, 16, 26, 16, 16, 18, 30]
PAYMENT_COL_WIDTHS = [6, 16, 26, 22, 10, 14, 8, 12, 12, 12, 16, 22, 24]
INVOICE_COL_WIDTHS = [6, 18, 20, 28, 16, 12, 14, 8, 12, 30, 12, 14]

_INVOICE_STATUS_LABELS = ("未开票 Not Invoiced", "部分开票 Partially Invoiced", "已开票 Invoiced")
_DELIVERY_STATUS_LABELS = (
    "未交付 Not Delivered",
    "部分到货 Partially Delivered",
    "已到货 Delivered",
)

# Cerbos resource kind -> the fields whose read access gates ledger columns.
# Keys are the policy actions that actually exist in deploy/cerbos-policies/*.yaml.
_PO_GATE_FIELDS = ["total_amount"]
_PAYMENT_SHEET_FIELDS = [
    "payment_number",
    "amount",
    "currency",
    "status",
    "due_date",
    "payment_date",
    "payment_method",
    "transaction_ref",
    "notes",
]
_INVOICE_SHEET_FIELDS = [
    "internal_number",
    "invoice_number",
    "invoice_date",
    "total_amount",
    "currency",
    "status",
]


@dataclass(frozen=True)
class LedgerWorkbook:
    """Rendered-in-memory ledger data shared by the XLSX and CSV writers."""

    ledger_rows: list[list[Any]]
    payment_rows: list[list[Any]]
    invoice_rows: list[list[Any]]
    ledger_total: Decimal
    amount_visible: bool


def _num(value: Decimal | int | float | None) -> float | str:
    if value is None:
        return ""
    return float(value)


def _progress_label(
    done: Decimal | None, total: Decimal | None, labels: tuple[str, str, str]
) -> str:
    done_value = done or Decimal("0")
    total_value = total or Decimal("0")
    if total_value > 0 and done_value >= total_value:
        return labels[2]
    if done_value > 0:
        return labels[1]
    return labels[0]


def _join_cell(values: Sequence[str]) -> str:
    """Join multiple codes into one cell, dropping blanks and duplicates."""
    seen: list[str] = []
    for value in values:
        text = (value or "").strip()
        if text and text not in seen:
            seen.append(text)
    return " / ".join(seen)


def _gated(allowed: set[str], field_name: str, value: Any) -> Any:
    """Return *value* only when the principal may read *field_name*."""
    return value if field_name in allowed else ""


async def _allowed_fields(actor: User, resource_kind: str, fields: list[str]) -> set[str]:
    """Single Cerbos check per resource kind, never per row.

    ``resource_id`` is a constant because the shipped policies are role-only
    (no attribute conditions on the resource id).
    """
    return await check_field_access(
        principal_id=str(actor.id),
        principal_role=actor.role,
        resource_kind=resource_kind,
        resource_id="ledger-export",
        fields=fields,
    )


def _apply_po_filters(
    stmt,
    *,
    date_from: date | None,
    date_to: date | None,
    statuses: Sequence[str] | None,
    supplier_id: UUID | None,
    keyword: str | None,
):
    if date_from is not None:
        stmt = stmt.where(
            PurchaseOrder.created_at >= datetime.combine(date_from, time.min, tzinfo=UTC)
        )
    if date_to is not None:
        # Use time.max rather than date_to + 1 day: adding a day to date.max
        # overflows and would turn a valid filter into an HTTP 500.
        stmt = stmt.where(
            PurchaseOrder.created_at <= datetime.combine(date_to, time.max, tzinfo=UTC)
        )
    if statuses:
        stmt = stmt.where(PurchaseOrder.status.in_(list(statuses)))
    if supplier_id is not None:
        stmt = stmt.where(PurchaseOrder.supplier_id == supplier_id)
    if keyword:
        pattern = f"%{keyword.strip()}%"
        stmt = stmt.join(PurchaseOrder.pr).join(PurchaseOrder.supplier)
        stmt = stmt.where(
            or_(
                PurchaseOrder.po_number.ilike(pattern),
                PurchaseRequisition.pr_number.ilike(pattern),
                Supplier.name.ilike(pattern),
            )
        )
    return stmt


async def _load_contract_numbers(db: AsyncSession, po_ids: Sequence[UUID]) -> dict[UUID, list[str]]:
    """Map PO id -> contract numbers, mirroring ``flow.list_contracts``.

    A contract belongs to a PO either through its primary ``po_id`` or through
    the many-to-many ``po_contract_links`` table. Rows are ordered by contract
    number so the joined cell is deterministic across calls.
    """
    mapping: dict[UUID, list[str]] = {}
    if not po_ids:
        return mapping

    primary = (
        await db.execute(
            select(Contract.po_id, Contract.contract_number)
            .where(Contract.po_id.in_(list(po_ids)))
            .order_by(Contract.contract_number.asc())
        )
    ).all()
    for po_id, contract_number in primary:
        mapping.setdefault(po_id, []).append(contract_number)

    linked = (
        await db.execute(
            select(POContractLink.po_id, Contract.contract_number)
            .join(Contract, Contract.id == POContractLink.contract_id)
            .where(POContractLink.po_id.in_(list(po_ids)))
            .order_by(Contract.contract_number.asc())
        )
    ).all()
    for po_id, contract_number in linked:
        mapping.setdefault(po_id, []).append(contract_number)

    # Ordering each source in SQL is not enough: a contract attached through
    # ``po_contract_links`` would still be appended after one attached through
    # ``contracts.po_id``. Sort the merged list so the joined cell is globally
    # ordered and reproducible regardless of how a contract is attached.
    return {po_id: sorted(numbers) for po_id, numbers in mapping.items()}


async def collect_procurement_ledger(
    db: AsyncSession,
    *,
    actor: User,
    date_from: date | None = None,
    date_to: date | None = None,
    statuses: Sequence[str] | None = None,
    supplier_id: UUID | None = None,
    keyword: str | None = None,
    max_rows: int = 5000,
) -> LedgerWorkbook:
    """Collect the procurement ledger (and its detail sheets) for *actor*."""
    from app.core.scoping import visible_po_id_subquery

    po_stmt = (
        select(PurchaseOrder)
        .options(
            selectinload(PurchaseOrder.supplier),
            selectinload(PurchaseOrder.company),
            selectinload(PurchaseOrder.pr).selectinload(PurchaseRequisition.requester),
            selectinload(PurchaseOrder.pr).selectinload(PurchaseRequisition.cost_center),
            selectinload(PurchaseOrder.items),
        )
        .order_by(PurchaseOrder.created_at.asc(), PurchaseOrder.po_number.asc())
    )
    visible_po_ids = await visible_po_id_subquery(db, actor)
    if visible_po_ids is not None:
        po_stmt = po_stmt.where(PurchaseOrder.id.in_(visible_po_ids))
    po_stmt = _apply_po_filters(
        po_stmt,
        date_from=date_from,
        date_to=date_to,
        statuses=statuses,
        supplier_id=supplier_id,
        keyword=keyword,
    )
    pos = list((await db.execute(po_stmt)).scalars().all())
    po_ids = [po.id for po in pos]

    contracts_by_po = await _load_contract_numbers(db, po_ids)

    payments_by_po: dict[UUID, list[PaymentRecord]] = {}
    if po_ids:
        payment_stmt = (
            select(PaymentRecord)
            .where(PaymentRecord.po_id.in_(po_ids))
            .order_by(PaymentRecord.installment_no.asc(), PaymentRecord.payment_number.asc())
        )
        for payment in (await db.execute(payment_stmt)).scalars().all():
            payments_by_po.setdefault(payment.po_id, []).append(payment)

    po_items = [item for po in pos for item in po.items]
    po_item_ids = [item.id for item in po_items]
    po_number_by_item: dict[UUID, str] = {item.id: po.po_number for po in pos for item in po.items}

    invoice_lines: list[InvoiceLine] = []
    if po_item_ids:
        invoice_stmt = (
            select(InvoiceLine)
            .where(InvoiceLine.po_item_id.in_(po_item_ids))
            .options(selectinload(InvoiceLine.invoice).selectinload(Invoice.supplier))
            .order_by(InvoiceLine.invoice_id.asc(), InvoiceLine.line_no.asc())
        )
        invoice_lines = list((await db.execute(invoice_stmt)).scalars().all())

    # One Cerbos round-trip per resource kind, executed concurrently.
    po_allowed, payment_allowed, invoice_allowed = await asyncio.gather(
        _allowed_fields(actor, "purchase_order", _PO_GATE_FIELDS),
        _allowed_fields(actor, "payment_record", [*_PAYMENT_SHEET_FIELDS, "payment_number"]),
        _allowed_fields(actor, "invoice", _INVOICE_SHEET_FIELDS),
    )
    amount_visible = "total_amount" in po_allowed
    payment_number_visible = "payment_number" in payment_allowed

    ledger_rows: list[list[Any]] = []
    ledger_total = Decimal("0")
    for po in pos:
        pr = po.pr
        company_name = po.company.name_zh if po.company else ""
        supplier_name = po.supplier.name if po.supplier else ""
        requester_name = pr.requester.display_name if pr and pr.requester else ""
        cost_center = pr.cost_center.label_zh if pr and pr.cost_center else ""
        contract_cell = _join_cell(contracts_by_po.get(po.id, []))
        payment_cell = (
            _join_cell([p.payment_number for p in payments_by_po.get(po.id, [])])
            if payment_number_visible
            else ""
        )
        for item in po.items:
            ledger_total += item.amount or Decimal("0")
            ledger_rows.append(
                [
                    len(ledger_rows) + 1,
                    pr.pr_number if pr else "",
                    requester_name,
                    cost_center,
                    company_name,
                    supplier_name,
                    contract_cell,
                    _num(item.qty),
                    _num(item.unit_price) if amount_visible else "",
                    _num(item.amount) if amount_visible else "",
                    po.currency,
                    po.po_number,
                    payment_cell,
                    _progress_label(item.qty_invoiced, item.qty, _INVOICE_STATUS_LABELS),
                    _progress_label(item.qty_received, item.qty, _DELIVERY_STATUS_LABELS),
                    "",
                    "",
                ]
            )

    payment_rows: list[list[Any]] = []
    for po in pos:
        contracts = contracts_by_po.get(po.id, [])
        for payment in payments_by_po.get(po.id, []):
            payment_rows.append(
                [
                    len(payment_rows) + 1,
                    po.po_number,
                    _gated(payment_allowed, "payment_number", payment.payment_number),
                    _join_cell(contracts),
                    payment.installment_no,
                    _gated(payment_allowed, "amount", _num(payment.amount)),
                    _gated(payment_allowed, "currency", payment.currency),
                    _gated(payment_allowed, "status", payment.status),
                    _gated(
                        payment_allowed,
                        "due_date",
                        payment.due_date.isoformat() if payment.due_date else "",
                    ),
                    _gated(
                        payment_allowed,
                        "payment_date",
                        payment.payment_date.isoformat() if payment.payment_date else "",
                    ),
                    _gated(payment_allowed, "payment_method", payment.payment_method),
                    _gated(payment_allowed, "transaction_ref", payment.transaction_ref or ""),
                    _gated(payment_allowed, "notes", payment.notes or ""),
                ]
            )

    invoice_rows: list[list[Any]] = []
    for line in invoice_lines:
        invoice = line.invoice
        invoice_rows.append(
            [
                len(invoice_rows) + 1,
                _gated(
                    invoice_allowed, "internal_number", invoice.internal_number if invoice else ""
                ),
                _gated(
                    invoice_allowed, "invoice_number", invoice.invoice_number if invoice else ""
                ),
                invoice.supplier.name if invoice and invoice.supplier else "",
                po_number_by_item.get(line.po_item_id, "") if line.po_item_id else "",
                _gated(
                    invoice_allowed,
                    "invoice_date",
                    invoice.invoice_date.isoformat() if invoice else "",
                ),
                _gated(
                    invoice_allowed, "total_amount", _num(invoice.total_amount) if invoice else ""
                ),
                _gated(invoice_allowed, "currency", invoice.currency if invoice else ""),
                _gated(invoice_allowed, "status", invoice.status if invoice else ""),
                line.item_name,
                _num(line.qty),
                _num(line.subtotal),
            ]
        )

    for rows in (ledger_rows, payment_rows, invoice_rows):
        if len(rows) > max_rows:
            raise HTTPException(400, "export.too_many_rows")

    return LedgerWorkbook(
        ledger_rows=ledger_rows,
        payment_rows=payment_rows,
        invoice_rows=invoice_rows,
        ledger_total=ledger_total,
        amount_visible=amount_visible,
    )


def _write_sheet(
    ws,
    headers: list[str],
    rows: list[list[Any]],
    widths: list[int],
    *,
    total_label_row: tuple[list[Any], int] | None = None,
) -> None:
    ws.append(headers)
    for col_idx, _ in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=col_idx)
        cell.fill = _HEADER_FILL
        cell.font = _HEADER_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    for row_idx, row in enumerate(rows, start=2):
        ws.append(row)
        if row_idx % 2 == 0:
            for col_idx in range(1, len(headers) + 1):
                ws.cell(row=row_idx, column=col_idx).fill = _ZEBRA_FILL

    for idx, width in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(idx)].width = width

    ws.freeze_panes = "A2"
    if rows:
        ws.auto_filter.ref = ws.dimensions

    if total_label_row is not None:
        row_values, label_col = total_label_row
        total_row = len(rows) + 3
        ws.cell(row=total_row, column=label_col, value=row_values[0]).font = Font(bold=True)
        ws.cell(row=total_row, column=label_col + 1, value=row_values[1]).font = Font(bold=True)


def ledger_to_xlsx(data: LedgerWorkbook) -> bytes:
    wb = Workbook()
    ledger_ws = wb.active
    ledger_ws.title = LEDGER_SHEET_TITLE
    total_label = "合计 Total" if data.amount_visible else ""
    total_value: Any = float(data.ledger_total) if data.amount_visible else ""
    _write_sheet(
        ledger_ws,
        LEDGER_HEADERS,
        data.ledger_rows,
        LEDGER_COL_WIDTHS,
        total_label_row=([total_label, total_value], 9),
    )

    payment_ws = wb.create_sheet(PAYMENT_SHEET_TITLE)
    _write_sheet(payment_ws, PAYMENT_HEADERS, data.payment_rows, PAYMENT_COL_WIDTHS)

    invoice_ws = wb.create_sheet(INVOICE_SHEET_TITLE)
    _write_sheet(invoice_ws, INVOICE_HEADERS, data.invoice_rows, INVOICE_COL_WIDTHS)

    return _workbook_bytes(wb)


def ledger_to_csv(data: LedgerWorkbook) -> bytes:
    """Render the main ledger sheet as CSV (UTF-8 BOM for Excel).

    CSV has no concept of multiple sheets, so only the main 采购台账 table is
    exported; the payment / invoice detail lives in the XLSX variant.
    """
    buf = StringIO(newline="")
    writer = csv.writer(buf)
    writer.writerow(LEDGER_HEADERS)
    for row in data.ledger_rows:
        writer.writerow([_csv_safe(cell) for cell in row])
    if data.amount_visible:
        writer.writerow(["", "", "", "", "", "", "", "", "合计 Total", float(data.ledger_total)])
    return buf.getvalue().encode("utf-8-sig")


def ledger_filename(fmt: str) -> str:
    stamp = datetime.now(UTC).strftime("%Y%m%d")
    return f"mica-procurement-ledger-{stamp}.{'csv' if fmt == 'csv' else 'xlsx'}"
