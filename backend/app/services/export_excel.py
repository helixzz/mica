from __future__ import annotations

from collections.abc import Sequence
from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import PaymentRecord, PurchaseOrder

_HEADER_FILL = PatternFill(start_color="8B5E3C", end_color="8B5E3C", fill_type="solid")
_HEADER_FONT = Font(name="Arial", bold=True, color="FFFFFF", size=11)
_ZEBRA_FILL = PatternFill(start_color="F7F6F5", end_color="F7F6F5", fill_type="solid")


async def render_payments_xlsx(
    db: AsyncSession,
    *,
    po_id: str | None = None,
    status: str | None = None,
) -> bytes:
    stmt = select(PaymentRecord).options(
        selectinload(PaymentRecord.po).selectinload(PurchaseOrder.supplier)
    )
    if po_id:
        stmt = stmt.where(PaymentRecord.po_id == po_id)
    if status:
        stmt = stmt.where(PaymentRecord.status == status)
    stmt = stmt.order_by(PaymentRecord.created_at.desc())
    payments: Sequence[PaymentRecord] = (await db.execute(stmt)).scalars().all()

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
        ws.append(
            [
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
        )
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

    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()
