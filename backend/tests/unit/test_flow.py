# pyright: reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportPrivateUsage=false, reportUnusedCallResult=false, reportCallInDefaultInitializer=false

from datetime import UTC, datetime
from decimal import Decimal

from app.models import Company, POItem, PurchaseOrder, PurchaseRequisition, Supplier, User, UserRole
from app.services import flow as flow_svc
from app.services import purchase as purchase_svc


async def _create_user(db_session, username: str = "alice") -> User:
    company = Company(
        code=f"FLOW-{username}-{datetime.now(UTC).microsecond}",
        name_zh="流程测试公司",
        name_en="Flow Test Company",
        default_locale="zh-CN",
        default_currency="CNY",
    )
    db_session.add(company)
    await db_session.flush()

    user = User(
        username=username,
        email=f"{username}@flow.local",
        display_name=username.title(),
        role=UserRole.IT_BUYER.value,
        company_id=company.id,
        preferred_locale="zh-CN",
    )
    db_session.add(user)
    await db_session.flush()
    return user


async def _create_supplier(db_session) -> Supplier:
    supplier = Supplier(code=f"SUP-{datetime.now(UTC).microsecond}", name="Flow Supplier")
    db_session.add(supplier)
    await db_session.flush()
    return supplier


async def _create_pr(
    db_session,
    requester: User,
    pr_number: str,
    total_amount: Decimal = Decimal("1000"),
) -> PurchaseRequisition:
    pr = PurchaseRequisition(
        pr_number=pr_number,
        title="Flow test PR",
        business_reason="unit test",
        status="draft",
        requester_id=requester.id,
        company_id=requester.company_id,
        department_id=requester.department_id,
        currency="CNY",
        total_amount=total_amount,
    )
    db_session.add(pr)
    await db_session.flush()
    return pr


async def _create_po(
    db_session,
    requester: User,
    supplier: Supplier,
    pr: PurchaseRequisition,
    po_number: str,
    total_amount: Decimal = Decimal("200"),
) -> PurchaseOrder:
    po = PurchaseOrder(
        po_number=po_number,
        pr_id=pr.id,
        supplier_id=supplier.id,
        company_id=requester.company_id,
        status="confirmed",
        currency="CNY",
        total_amount=total_amount,
        amount_paid=Decimal("50"),
        created_by_id=requester.id,
    )
    db_session.add(po)
    await db_session.flush()
    return po


async def test_next_pr_number_starts_with_first_sequence(db_session):
    year = datetime.now(UTC).year

    number = await purchase_svc._next_pr_number(db_session)

    assert number == f"PR-{year}-0001"


async def test_next_pr_number_increments_existing_rows(db_session):
    requester = await _create_user(db_session)
    year = datetime.now(UTC).year
    _ = await _create_pr(db_session, requester, f"PR-{year}-0001")

    number = await purchase_svc._next_pr_number(db_session)

    assert number == f"PR-{year}-0002"


async def test_next_po_number_increments_existing_rows(db_session):
    requester = await _create_user(db_session)
    supplier = await _create_supplier(db_session)
    year = datetime.now(UTC).year
    pr = await _create_pr(db_session, requester, f"PR-{year}-0001")
    _ = await _create_po(db_session, requester, supplier, pr, f"PO-{year}-0001")

    number = await purchase_svc._next_po_number(db_session)

    assert number == f"PO-{year}-0002"


def test_compute_line_amount_quantizes_to_four_decimals():
    amount = purchase_svc._compute_line_amount(Decimal("3"), Decimal("19.99995"))

    assert amount == Decimal("59.9998")


async def test_po_progress_summarizes_received_invoiced_and_paid(db_session):
    requester = await _create_user(db_session)
    supplier = await _create_supplier(db_session)
    year = datetime.now(UTC).year
    pr = await _create_pr(db_session, requester, f"PR-{year}-0099", Decimal("200"))
    po = await _create_po(
        db_session,
        requester,
        supplier,
        pr,
        f"PO-{year}-0099",
        Decimal("200"),
    )
    db_session.add_all(
        [
            POItem(
                po_id=po.id,
                line_no=1,
                item_name="Line 1",
                specification="Spec 1",
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
                item_name="Line 2",
                specification="Spec 2",
                qty=Decimal("6"),
                qty_received=Decimal("6"),
                qty_invoiced=Decimal("3"),
                uom="EA",
                unit_price=Decimal("20"),
                amount=Decimal("120"),
            ),
        ]
    )
    await db_session.flush()

    progress = await flow_svc.po_progress(db_session, po.id)

    assert progress["po_number"] == po.po_number
    assert progress["total_qty"] == "10.0000"
    assert progress["qty_received"] == "8.0000"
    assert progress["qty_invoiced"] == "4.0000"
    assert progress["amount_invoiced"] == "80.0000"
    assert progress["pct_received"] == 80.0
    assert progress["pct_invoiced"] == 40.0
    assert progress["pct_paid"] == 25.0
