from __future__ import annotations

from decimal import Decimal
from io import BytesIO
from uuid import UUID

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import PurchaseOrder

_CJK_FONT_REGISTERED = False


def _ensure_cjk_font() -> str:
    global _CJK_FONT_REGISTERED
    name = "STSong-Light"
    if not _CJK_FONT_REGISTERED:
        pdfmetrics.registerFont(UnicodeCIDFont(name))
        _CJK_FONT_REGISTERED = True
    return name


def _fmt_money(amount: Decimal | float | int, currency: str = "CNY") -> str:
    q = Decimal(amount).quantize(Decimal("0.01"))
    return f"{currency} {q:,.2f}"


async def render_po_pdf(db: AsyncSession, po_id: UUID) -> bytes:
    stmt = (
        select(PurchaseOrder)
        .where(PurchaseOrder.id == po_id)
        .options(
            selectinload(PurchaseOrder.supplier),
            selectinload(PurchaseOrder.company),
            selectinload(PurchaseOrder.items),
        )
    )
    po = (await db.execute(stmt)).scalar_one()

    font = _ensure_cjk_font()
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title=f"Purchase Order {po.po_number}",
    )

    base_styles = getSampleStyleSheet()
    h1 = ParagraphStyle(
        "CJKTitle",
        parent=base_styles["Title"],
        fontName=font,
        fontSize=20,
        leading=26,
        spaceAfter=6 * mm,
    )
    h2 = ParagraphStyle(
        "CJKHeading",
        parent=base_styles["Heading3"],
        fontName=font,
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#8B5E3C"),
        spaceBefore=4 * mm,
        spaceAfter=2 * mm,
    )
    normal = ParagraphStyle(
        "CJKNormal",
        parent=base_styles["BodyText"],
        fontName=font,
        fontSize=10,
        leading=14,
    )
    small = ParagraphStyle(
        "CJKSmall",
        parent=normal,
        fontSize=9,
        textColor=colors.grey,
    )

    story: list = [
        Paragraph("采购订单 · Purchase Order", h1),
        Paragraph(f"单号 PO No.: <b>{po.po_number}</b>", normal),
        Paragraph(f"货币 Currency: {po.currency} &nbsp;&nbsp; 状态 Status: {po.status}", normal),
        Spacer(1, 4 * mm),
    ]

    header_data = [
        [Paragraph("<b>采购方 Buyer</b>", normal), Paragraph("<b>供应商 Supplier</b>", normal)],
        [
            Paragraph(
                (po.company.name_zh if po.company else "-"),
                normal,
            ),
            Paragraph(po.supplier.name if po.supplier else "-", normal),
        ],
    ]
    supplier_lines: list[str] = []
    if po.supplier:
        if po.supplier.tax_number:
            supplier_lines.append(f"税号: {po.supplier.tax_number}")
        if po.supplier.contact_name:
            supplier_lines.append(f"联系人: {po.supplier.contact_name}")
        if po.supplier.contact_phone:
            supplier_lines.append(f"电话: {po.supplier.contact_phone}")
        if po.supplier.contact_email:
            supplier_lines.append(f"邮箱: {po.supplier.contact_email}")
    if supplier_lines:
        header_data.append([Paragraph("", normal), Paragraph("<br/>".join(supplier_lines), small)])

    header = Table(header_data, colWidths=[85 * mm, 85 * mm])
    header.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOX", (0, 0), (-1, -1), 0.25, colors.HexColor("#DFDBD7")),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#EFECE9")),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F7F6F5")),
                ("FONTNAME", (0, 0), (-1, -1), font),
                ("LEFTPADDING", (0, 0), (-1, -1), 4 * mm),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4 * mm),
                ("TOPPADDING", (0, 0), (-1, -1), 2 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2 * mm),
            ]
        )
    )
    story.append(header)

    story.append(Paragraph("物料明细 Line Items", h2))

    line_rows = [
        ["#", "编码 Code", "名称 / 规格 Name / Spec", "数量 Qty", "单价 Unit", "金额 Amount"]
    ]
    for it in po.items:
        spec = it.specification or ""
        name_cell = it.item_name + (
            f"<br/><font size=8 color='#6F6861'>{spec}</font>" if spec else ""
        )
        line_rows.append(
            [
                str(it.line_no),
                "-",
                Paragraph(name_cell, normal),
                f"{it.qty} {it.uom}",
                _fmt_money(it.unit_price, po.currency),
                _fmt_money(it.amount, po.currency),
            ]
        )

    items_tbl = Table(
        line_rows,
        colWidths=[10 * mm, 22 * mm, 70 * mm, 22 * mm, 23 * mm, 23 * mm],
        repeatRows=1,
    )
    items_tbl.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), font),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#8B5E3C")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (3, 1), (-1, -1), "RIGHT"),
                ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#DFDBD7")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7F6F5")]),
                ("LEFTPADDING", (0, 0), (-1, -1), 3 * mm),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3 * mm),
                ("TOPPADDING", (0, 0), (-1, -1), 2 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2 * mm),
            ]
        )
    )
    story.append(items_tbl)
    story.append(Spacer(1, 4 * mm))

    totals = Table(
        [
            ["合计 Subtotal", _fmt_money(po.total_amount, po.currency)],
            ["已开票 Invoiced", _fmt_money(po.amount_invoiced, po.currency)],
            ["已付款 Paid", _fmt_money(po.amount_paid, po.currency)],
        ],
        colWidths=[140 * mm, 30 * mm],
        hAlign="RIGHT",
    )
    totals.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), font),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("ALIGN", (0, 0), (0, -1), "RIGHT"),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("LINEABOVE", (0, 0), (-1, 0), 0.5, colors.HexColor("#AFA9A3")),
                ("LINEABOVE", (0, -1), (-1, -1), 0.5, colors.HexColor("#AFA9A3")),
                ("FONTNAME", (0, 0), (-1, 0), font),
                ("FONTSIZE", (0, 0), (-1, 0), 12),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#8B5E3C")),
            ]
        )
    )
    story.append(totals)

    story.append(Paragraph("条款 Terms &amp; Signatures", h2))
    story.append(
        Paragraph(
            "1. 本订单一经双方盖章签字即具有法律效力。<br/>"
            "2. 质量标准、交付方式及违约责任以相关合同为准。<br/>"
            "3. 如对本订单有疑问，请在 3 个工作日内联系采购方。",
            normal,
        )
    )
    story.append(Spacer(1, 12 * mm))

    sig_table = Table(
        [
            ["采购方签章 Buyer Signature", "供应商签章 Supplier Signature"],
            ["", ""],
            ["日期 Date: ____________________", "日期 Date: ____________________"],
        ],
        colWidths=[85 * mm, 85 * mm],
        rowHeights=[6 * mm, 20 * mm, 6 * mm],
    )
    sig_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), font),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOX", (0, 0), (0, -1), 0.25, colors.HexColor("#DFDBD7")),
                ("BOX", (1, 0), (1, -1), 0.25, colors.HexColor("#DFDBD7")),
            ]
        )
    )
    story.append(sig_table)

    doc.build(story)
    return buf.getvalue()
