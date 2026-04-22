from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select

from app.models import POItem, PurchaseOrder, PurchaseRequisition, Supplier, User
from app.services import flow as flow_svc
from app.services import purchase as purchase_svc


async def _get_user(db, username="alice"):
    return (await db.execute(select(User).where(User.username == username))).scalar_one()


async def _get_supplier(db):
    return (await db.execute(select(Supplier).order_by(Supplier.code).limit(1))).scalar_one()


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
        pr_number=n1, title="test", business_reason="test", status="draft",
        requester_id=user.id, company_id=user.company_id,
        department_id=user.department_id, currency="CNY", total_amount=Decimal("100"),
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
        pr_number=f"PR-FLOW-{n1}", title="test", business_reason="test", status="draft",
        requester_id=user.id, company_id=user.company_id,
        department_id=user.department_id, currency="CNY", total_amount=Decimal("100"),
    )
    db.add(pr)
    await db.flush()
    po = PurchaseOrder(
        po_number=n1, pr_id=pr.id, supplier_id=supplier.id, company_id=user.company_id,
        status="confirmed", currency="CNY", total_amount=Decimal("100"),
        amount_paid=Decimal("0"), created_by_id=user.id,
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
        pr_number=f"PR-{year}-PROG", title="test", business_reason="test", status="draft",
        requester_id=user.id, company_id=user.company_id,
        department_id=user.department_id, currency="CNY", total_amount=Decimal("200"),
    )
    db.add(pr)
    await db.flush()
    po = PurchaseOrder(
        po_number=f"PO-{year}-PROG", pr_id=pr.id, supplier_id=supplier.id,
        company_id=user.company_id, status="confirmed", currency="CNY",
        total_amount=Decimal("200"), amount_paid=Decimal("50"), created_by_id=user.id,
    )
    db.add(po)
    await db.flush()
    db.add_all([
        POItem(po_id=po.id, line_no=1, item_name="L1", specification="S1",
               qty=Decimal("4"), qty_received=Decimal("2"), qty_invoiced=Decimal("1"),
               uom="EA", unit_price=Decimal("20"), amount=Decimal("80")),
        POItem(po_id=po.id, line_no=2, item_name="L2", specification="S2",
               qty=Decimal("6"), qty_received=Decimal("6"), qty_invoiced=Decimal("3"),
               uom="EA", unit_price=Decimal("20"), amount=Decimal("120")),
    ])
    await db.flush()

    progress = await flow_svc.po_progress(db, po.id)
    assert progress["po_number"] == po.po_number
    assert float(progress["pct_received"]) == 80.0
    assert float(progress["pct_paid"]) == 25.0
