# pyright: reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnusedCallResult=false, reportUnusedImport=false, reportPrivateUsage=false
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.exc import NoResultFound

from app.models import POItem, POStatus, PurchaseOrder, PurchaseRequisition, Supplier, User
from app.services import export_pdf as svc


def _suffix() -> str:
    return uuid4().hex[:8].upper()


async def _user(db, username: str = "alice") -> User:
    return (await db.execute(select(User).where(User.username == username))).scalar_one()


async def _seeded_supplier(db, code: str = "SUP-DELL") -> Supplier:
    return (await db.execute(select(Supplier).where(Supplier.code == code))).scalar_one()


async def _minimal_supplier(db) -> Supplier:
    supplier = Supplier(
        code=f"SUP-PDF-{_suffix()}",
        name="Minimal PDF Supplier",
    )
    db.add(supplier)
    await db.flush()
    return supplier


async def _create_po(
    db,
    *,
    actor: User,
    supplier: Supplier,
    title: str,
    with_items: bool,
) -> PurchaseOrder:
    pr = PurchaseRequisition(
        pr_number=f"PR-PDF-{_suffix()}",
        title=title,
        business_reason="pdf export test",
        status="approved",
        requester_id=actor.id,
        company_id=actor.company_id,
        department_id=actor.department_id,
        currency="CNY",
        total_amount=Decimal("0"),
    )
    db.add(pr)
    await db.flush()

    total_amount = Decimal("0")
    if with_items:
        total_amount = Decimal("1500.00")

    po = PurchaseOrder(
        po_number=f"PO-PDF-{_suffix()}",
        pr_id=pr.id,
        supplier_id=supplier.id,
        company_id=actor.company_id,
        status=POStatus.CONFIRMED.value,
        currency="CNY",
        total_amount=total_amount,
        amount_paid=Decimal("200.00"),
        amount_invoiced=Decimal("300.00"),
        created_by_id=actor.id,
    )
    db.add(po)
    await db.flush()

    if with_items:
        db.add_all(
            [
                POItem(
                    po_id=po.id,
                    line_no=1,
                    item_name="Firewall Appliance",
                    specification="Dual PSU, 3-year support",
                    qty=Decimal("1"),
                    qty_received=Decimal("0"),
                    qty_invoiced=Decimal("0"),
                    uom="EA",
                    unit_price=Decimal("1200.00"),
                    amount=Decimal("1200.00"),
                ),
                POItem(
                    po_id=po.id,
                    line_no=2,
                    item_name="Rack Kit",
                    specification=None,
                    qty=Decimal("2"),
                    qty_received=Decimal("0"),
                    qty_invoiced=Decimal("0"),
                    uom="EA",
                    unit_price=Decimal("150.00"),
                    amount=Decimal("300.00"),
                ),
            ]
        )
        await db.flush()

    return po


@pytest.mark.parametrize(
    ("amount", "currency", "expected"),
    [
        (Decimal("1234.5"), "CNY", "CNY 1,234.50"),
        (12, "USD", "USD 12.00"),
        (1.2, "EUR", "EUR 1.20"),
    ],
)
def test_fmt_money_formats_supported_numeric_inputs(amount, currency, expected):
    assert svc._fmt_money(amount, currency) == expected


def test_ensure_cjk_font_is_idempotent(monkeypatch):
    monkeypatch.setattr(svc, "_FONT_FAMILY", None)

    first = svc._ensure_cjk_font()
    second = svc._ensure_cjk_font()

    assert first == second
    assert first in {"MicaCJK", "STSong-Light"}
    assert svc._FONT_FAMILY == first


def test_ensure_cjk_font_falls_back_when_noto_missing(monkeypatch):
    monkeypatch.setattr(svc, "_FONT_FAMILY", None)
    monkeypatch.setattr(svc, "_first_existing", lambda _paths: None)

    assert svc._ensure_cjk_font() == "STSong-Light"


def test_esc_escapes_xml_special_chars():
    assert svc._esc("A & B <c>") == "A &amp; B &lt;c&gt;"
    assert svc._esc(None) == ""
    assert svc._esc(42) == "42"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (Decimal("1.00"), "1"),
        (Decimal("1.50"), "1.5"),
        (Decimal("1.234"), "1.23"),
        (Decimal("12345"), "12,345"),
        (None, "0"),
    ],
)
def test_fmt_qty_strips_trailing_zeros(value, expected):
    assert svc._fmt_qty(value) == expected


async def test_render_po_pdf_handles_xml_special_chars_in_item_name(seeded_db_session):
    actor = await _user(seeded_db_session)
    supplier = await _minimal_supplier(seeded_db_session)
    pr = PurchaseRequisition(
        pr_number=f"PR-PDF-{_suffix()}",
        title="XML safety",
        business_reason="ensure <b>, &, > do not break Paragraph parsing",
        status="approved",
        requester_id=actor.id,
        company_id=actor.company_id,
        department_id=actor.department_id,
        currency="CNY",
        total_amount=Decimal("0"),
    )
    seeded_db_session.add(pr)
    await seeded_db_session.flush()

    po = PurchaseOrder(
        po_number=f"PO-PDF-{_suffix()}",
        pr_id=pr.id,
        supplier_id=supplier.id,
        company_id=actor.company_id,
        status=POStatus.CONFIRMED.value,
        currency="CNY",
        total_amount=Decimal("100.00"),
        amount_paid=Decimal("0"),
        amount_invoiced=Decimal("0"),
        created_by_id=actor.id,
    )
    seeded_db_session.add(po)
    await seeded_db_session.flush()

    seeded_db_session.add(
        POItem(
            po_id=po.id,
            line_no=1,
            item_name="Router <model X> & cable",
            specification="Ports > 24, tag <b>bold</b>",
            qty=Decimal("1"),
            qty_received=Decimal("0"),
            qty_invoiced=Decimal("0"),
            uom="EA",
            unit_price=Decimal("100.00"),
            amount=Decimal("100.00"),
        )
    )
    await seeded_db_session.flush()

    content = await svc.render_po_pdf(seeded_db_session, po.id)

    assert content.startswith(b"%PDF-")
    assert content.rstrip().endswith(b"%%EOF")


async def test_render_po_pdf_returns_pdf_bytes_for_populated_po(seeded_db_session):
    actor = await _user(seeded_db_session)
    supplier = await _seeded_supplier(seeded_db_session)
    po = await _create_po(
        seeded_db_session,
        actor=actor,
        supplier=supplier,
        title="Populated PDF export",
        with_items=True,
    )

    content = await svc.render_po_pdf(seeded_db_session, po.id)

    assert content.startswith(b"%PDF-")
    assert content.rstrip().endswith(b"%%EOF")
    assert len(content) > 2500


async def test_render_po_pdf_handles_empty_items_and_minimal_supplier(seeded_db_session):
    actor = await _user(seeded_db_session)
    supplier = await _minimal_supplier(seeded_db_session)
    po = await _create_po(
        seeded_db_session,
        actor=actor,
        supplier=supplier,
        title="Minimal PDF export",
        with_items=False,
    )

    content = await svc.render_po_pdf(seeded_db_session, po.id)

    assert content.startswith(b"%PDF-")
    assert content.rstrip().endswith(b"%%EOF")
    assert len(content) > 1800


async def test_render_po_pdf_raises_for_missing_po(seeded_db_session):
    with pytest.raises(NoResultFound):
        await svc.render_po_pdf(seeded_db_session, uuid4())
