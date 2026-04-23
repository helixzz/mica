from __future__ import annotations

import html
import logging
import os
from decimal import Decimal
from io import BytesIO
from uuid import UUID

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfbase.pdfmetrics import registerFontFamily
from reportlab.pdfbase.ttfonts import TTFont
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

logger = logging.getLogger(__name__)

# Use WenQuanYi Micro Hei (TrueType outlines, reportlab-compatible) via the
# fonts-wqy-microhei apt package. Noto Sans CJK looks nicer but ships as an
# OpenType Collection with CFF/PostScript outlines which reportlab's TTFont
# class does not support. The previous CID font STSong-Light had no bold
# variant, so reportlab synthesized bold via over-striking — that caused
# the visible text-overlap bug on headings.

_FONT_FAMILY: str | None = None
_CJK_TTF_PATHS = [
    "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
]
_CJK_TTC_SUBFONT_INDEX = 0


def _first_existing(paths: list[str]) -> str | None:
    for p in paths:
        if os.path.exists(p):
            return p
    return None


def _ensure_cjk_font() -> str:
    global _FONT_FAMILY
    if _FONT_FAMILY is not None:
        return _FONT_FAMILY

    ttf_path = _first_existing(_CJK_TTF_PATHS)
    if ttf_path is not None:
        try:
            is_ttc = ttf_path.endswith(".ttc")
            kwargs = {"subfontIndex": _CJK_TTC_SUBFONT_INDEX} if is_ttc else {}
            pdfmetrics.registerFont(TTFont("MicaCJK", ttf_path, **kwargs))
            # Intentional: map bold role to the same regular glyphs so <b>
            # tags do not trigger reportlab's synthesized-bold over-striking.
            pdfmetrics.registerFont(TTFont("MicaCJK-Bold", ttf_path, **kwargs))
            registerFontFamily(
                "MicaCJK",
                normal="MicaCJK",
                bold="MicaCJK-Bold",
                italic="MicaCJK",
                boldItalic="MicaCJK-Bold",
            )
            _FONT_FAMILY = "MicaCJK"
            logger.info("PDF export: registered WenQuanYi family from %s", ttf_path)
            return _FONT_FAMILY
        except Exception:
            logger.exception("PDF export: WenQuanYi registration failed, using STSong-Light")

    # STSong-Light has no bold variant; map both roles to it to suppress
    # synthesized-bold over-striking (the original overlap bug).
    pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
    try:
        registerFontFamily(
            "STSong-Light",
            normal="STSong-Light",
            bold="STSong-Light",
            italic="STSong-Light",
            boldItalic="STSong-Light",
        )
    except Exception:
        pass
    _FONT_FAMILY = "STSong-Light"
    return _FONT_FAMILY


def _fmt_money(amount: Decimal | float | int | None, currency: str = "CNY") -> str:
    if amount is None:
        return f"{currency} 0.00"
    q = Decimal(amount).quantize(Decimal("0.01"))
    return f"{currency} {q:,.2f}"


def _fmt_qty(qty: Decimal | float | int | None) -> str:
    if qty is None:
        return "0"
    d = Decimal(qty).quantize(Decimal("0.01"))
    s = f"{d:,.2f}".rstrip("0").rstrip(".")
    return s or "0"


def _esc(text: object) -> str:
    return html.escape(str(text) if text is not None else "", quote=True)


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
    cell = ParagraphStyle(
        "CJKCell",
        parent=normal,
        fontSize=9,
        leading=12,
        spaceBefore=0,
        spaceAfter=0,
    )
    cell_right = ParagraphStyle(
        "CJKCellRight",
        parent=cell,
        alignment=TA_RIGHT,
    )
    cell_center = ParagraphStyle(
        "CJKCellCenter",
        parent=cell,
        alignment=TA_CENTER,
    )
    header_cell = ParagraphStyle(
        "CJKHeaderCell",
        parent=cell,
        textColor=colors.white,
        alignment=TA_CENTER,
        fontSize=9,
        leading=12,
    )
    small = ParagraphStyle(
        "CJKSmall",
        parent=normal,
        fontSize=9,
        leading=12,
        textColor=colors.grey,
    )

    story: list = [
        Paragraph("采购订单 · Purchase Order", h1),
        Paragraph(f"单号 PO No.: <b>{_esc(po.po_number)}</b>", normal),
        Paragraph(
            f"货币 Currency: {_esc(po.currency)} &nbsp;&nbsp; 状态 Status: {_esc(po.status)}",
            normal,
        ),
        Spacer(1, 4 * mm),
    ]

    header_data = [
        [Paragraph("<b>采购方 Buyer</b>", normal), Paragraph("<b>供应商 Supplier</b>", normal)],
        [
            Paragraph(_esc(po.company.name_zh) if po.company else "-", normal),
            Paragraph(_esc(po.supplier.name) if po.supplier else "-", normal),
        ],
    ]
    supplier_lines: list[str] = []
    if po.supplier:
        if po.supplier.tax_number:
            supplier_lines.append(f"税号: {_esc(po.supplier.tax_number)}")
        if po.supplier.contact_name:
            supplier_lines.append(f"联系人: {_esc(po.supplier.contact_name)}")
        if po.supplier.contact_phone:
            supplier_lines.append(f"电话: {_esc(po.supplier.contact_phone)}")
        if po.supplier.contact_email:
            supplier_lines.append(f"邮箱: {_esc(po.supplier.contact_email)}")
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

    line_rows: list[list] = [
        [
            Paragraph("#", header_cell),
            Paragraph("编码 Code", header_cell),
            Paragraph("名称 / 规格 Name / Spec", header_cell),
            Paragraph("数量 Qty", header_cell),
            Paragraph("单价 Unit", header_cell),
            Paragraph("金额 Amount", header_cell),
        ]
    ]
    for it in po.items:
        name_html = _esc(it.item_name)
        if it.specification:
            name_html += f"<br/><font size=8 color='#6F6861'>{_esc(it.specification)}</font>"
        line_rows.append(
            [
                Paragraph(str(it.line_no), cell_center),
                Paragraph("-", cell_center),
                Paragraph(name_html, cell),
                Paragraph(f"{_fmt_qty(it.qty)} {_esc(it.uom)}", cell_right),
                Paragraph(_fmt_money(it.unit_price, po.currency), cell_right),
                Paragraph(_fmt_money(it.amount, po.currency), cell_right),
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
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
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

    totals_label = ParagraphStyle(
        "CJKTotalsLabel",
        parent=normal,
        fontSize=10,
        alignment=2,
    )
    totals_value = ParagraphStyle(
        "CJKTotalsValue",
        parent=normal,
        fontSize=10,
        alignment=2,
    )
    totals_label_big = ParagraphStyle(
        "CJKTotalsLabelBig",
        parent=totals_label,
        fontSize=12,
        textColor=colors.HexColor("#8B5E3C"),
    )
    totals_value_big = ParagraphStyle(
        "CJKTotalsValueBig",
        parent=totals_value,
        fontSize=12,
        textColor=colors.HexColor("#8B5E3C"),
    )

    totals = Table(
        [
            [
                Paragraph("合计 Subtotal", totals_label_big),
                Paragraph(_fmt_money(po.total_amount, po.currency), totals_value_big),
            ],
            [
                Paragraph("已开票 Invoiced", totals_label),
                Paragraph(_fmt_money(po.amount_invoiced, po.currency), totals_value),
            ],
            [
                Paragraph("已付款 Paid", totals_label),
                Paragraph(_fmt_money(po.amount_paid, po.currency), totals_value),
            ],
        ],
        colWidths=[140 * mm, 30 * mm],
        hAlign="RIGHT",
    )
    totals.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), font),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LINEABOVE", (0, 0), (-1, 0), 0.5, colors.HexColor("#AFA9A3")),
                ("LINEABOVE", (0, -1), (-1, -1), 0.5, colors.HexColor("#AFA9A3")),
                ("TOPPADDING", (0, 0), (-1, -1), 2 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2 * mm),
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
            [
                Paragraph("采购方签章 Buyer Signature", normal),
                Paragraph("供应商签章 Supplier Signature", normal),
            ],
            ["", ""],
            [
                Paragraph("日期 Date: ____________________", normal),
                Paragraph("日期 Date: ____________________", normal),
            ],
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
