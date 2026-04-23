# pyright: reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnusedCallResult=false, reportOptionalMemberAccess=false, reportPrivateUsage=false

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select

from app.models import (
    Item,
    POItem,
    POStatus,
    PurchaseOrder,
    PurchaseRequisition,
    SKUPriceRecord,
    Supplier,
    User,
)
from app.services import sku_insights as svc


def _suffix() -> str:
    return uuid4().hex[:8].upper()


async def _user(db, username: str = "alice") -> User:
    return (await db.execute(select(User).where(User.username == username))).scalar_one()


async def _item(db, code: str) -> Item:
    return (await db.execute(select(Item).where(Item.code == code))).scalar_one()


async def _supplier(db, code: str) -> Supplier:
    return (await db.execute(select(Supplier).where(Supplier.code == code))).scalar_one()


async def _create_purchase(
    db,
    *,
    actor: User,
    supplier: Supplier,
    item: Item,
    unit_price: str,
    qty: str,
    created_at: datetime,
) -> PurchaseOrder:
    quantity = Decimal(qty)
    price = Decimal(unit_price)
    amount = quantity * price

    pr = PurchaseRequisition(
        pr_number=f"PR-INS-{_suffix()}",
        title="SKU insights test PR",
        business_reason="unit test",
        status="draft",
        requester_id=actor.id,
        company_id=actor.company_id,
        department_id=actor.department_id,
        currency="CNY",
        total_amount=amount,
    )
    db.add(pr)
    await db.flush()

    po = PurchaseOrder(
        po_number=f"PO-INS-{_suffix()}",
        pr_id=pr.id,
        supplier_id=supplier.id,
        company_id=actor.company_id,
        status=POStatus.CONFIRMED.value,
        currency="CNY",
        total_amount=amount,
        amount_paid=Decimal("0"),
        created_by_id=actor.id,
        created_at=created_at,
    )
    db.add(po)
    await db.flush()

    db.add(
        POItem(
            po_id=po.id,
            item_id=item.id,
            item_name=item.name,
            qty=quantity,
            unit_price=price,
            amount=amount,
            line_no=1,
            uom=item.uom,
            specification=item.specification,
        )
    )
    await db.flush()
    return po


async def _create_price_record(
    db,
    *,
    actor: User,
    item: Item,
    price: str,
    quotation_date: date,
    supplier: Supplier | None = None,
) -> SKUPriceRecord:
    record = SKUPriceRecord(
        item_id=item.id,
        supplier_id=supplier.id if supplier else None,
        price=Decimal(price),
        currency="CNY",
        quotation_date=quotation_date,
        source_type="manual",
        source_ref=f"UT-{_suffix()}",
        entered_by_id=actor.id,
        notes="unit test",
    )
    db.add(record)
    await db.flush()
    return record


def test_compute_purchase_stats_with_empty_history_returns_zeroed_summary():
    stats = svc._compute_purchase_stats([])

    assert stats == {
        "count": 0,
        "total_qty": Decimal("0"),
        "total_amount": Decimal("0"),
        "avg_price": None,
        "median_price": None,
        "min_price": None,
        "max_price": None,
    }


def test_compute_purchase_stats_with_populated_history_returns_aggregates():
    history = [
        {"unit_price": Decimal("100.00"), "qty": Decimal("2"), "amount": Decimal("200.00")},
        {"unit_price": Decimal("120.00"), "qty": Decimal("1"), "amount": Decimal("120.00")},
        {"unit_price": Decimal("80.00"), "qty": Decimal("3"), "amount": Decimal("240.00")},
    ]

    stats = svc._compute_purchase_stats(history)

    assert stats == {
        "count": 3,
        "total_qty": Decimal("6"),
        "total_amount": Decimal("560.00"),
        "avg_price": 100.0,
        "median_price": 100.0,
        "min_price": 80.0,
        "max_price": 120.0,
    }


async def test_market_stats_without_price_records_returns_none(seeded_db_session):
    item = await _item(seeded_db_session, "SKU-SRV-R750")

    stats = await svc._market_stats(seeded_db_session, item.id, date.today() - timedelta(days=30))

    assert stats is None


async def test_market_stats_with_price_records_computes_summary_and_signal(seeded_db_session):
    actor = await _user(seeded_db_session)
    supplier = await _supplier(seeded_db_session, "SUP-DELL")
    item = await _item(seeded_db_session, "SKU-NB-T14")
    today = date.today()

    await _create_price_record(
        seeded_db_session,
        actor=actor,
        item=item,
        supplier=supplier,
        price="90.00",
        quotation_date=today - timedelta(days=10),
    )
    await _create_price_record(
        seeded_db_session,
        actor=actor,
        item=item,
        supplier=supplier,
        price="100.00",
        quotation_date=today - timedelta(days=5),
    )
    await _create_price_record(
        seeded_db_session,
        actor=actor,
        item=item,
        supplier=supplier,
        price="110.00",
        quotation_date=today - timedelta(days=1),
    )

    stats = await svc._market_stats(seeded_db_session, item.id, today - timedelta(days=30))

    assert stats == {
        "sample_count": 3,
        "avg_price": 100.0,
        "median_price": 100.0,
        "min_price": 90.0,
        "max_price": 110.0,
        "volatility_pct": 10.0,
        "current_price": 110.0,
        "current_vs_avg_pct": 10.0,
        "signal": "above_avg",
    }


async def test_supplier_comparison_with_po_data_aggregates_by_supplier(seeded_db_session):
    actor = await _user(seeded_db_session)
    item = await _item(seeded_db_session, "SKU-MON-U2723")
    lower_supplier = await _supplier(seeded_db_session, "SUP-APPLE")
    higher_supplier = await _supplier(seeded_db_session, "SUP-DELL")
    now = datetime.now(UTC)

    await _create_purchase(
        seeded_db_session,
        actor=actor,
        supplier=lower_supplier,
        item=item,
        unit_price="90.00",
        qty="2",
        created_at=now - timedelta(days=8),
    )
    await _create_purchase(
        seeded_db_session,
        actor=actor,
        supplier=higher_supplier,
        item=item,
        unit_price="100.00",
        qty="1",
        created_at=now - timedelta(days=6),
    )
    await _create_purchase(
        seeded_db_session,
        actor=actor,
        supplier=higher_supplier,
        item=item,
        unit_price="110.00",
        qty="1",
        created_at=now - timedelta(days=2),
    )

    comparison = await svc._supplier_comparison(
        seeded_db_session,
        item.id,
        date.today() - timedelta(days=30),
    )

    assert comparison == [
        {
            "supplier_name": lower_supplier.name,
            "avg_price": 90.0,
            "count": 1,
            "last_date": (now - timedelta(days=8)).date().isoformat(),
        },
        {
            "supplier_name": higher_supplier.name,
            "avg_price": 105.0,
            "count": 2,
            "last_date": (now - timedelta(days=2)).date().isoformat(),
        },
    ]


async def test_get_insights_with_po_purchase_history_returns_history_and_stats(seeded_db_session):
    actor = await _user(seeded_db_session)
    supplier = await _supplier(seeded_db_session, "SUP-LENOVO")
    item = await _item(seeded_db_session, "SKU-SRV-R760")
    now = datetime.now(UTC)

    await _create_purchase(
        seeded_db_session,
        actor=actor,
        supplier=supplier,
        item=item,
        unit_price="100.00",
        qty="2",
        created_at=now - timedelta(days=7),
    )
    await _create_purchase(
        seeded_db_session,
        actor=actor,
        supplier=supplier,
        item=item,
        unit_price="120.00",
        qty="1",
        created_at=now - timedelta(days=3),
    )

    insights = await svc.get_insights(seeded_db_session, item.id, window_days=30)

    assert [row["unit_price"] for row in insights["purchase_history"]] == [
        Decimal("120.00"),
        Decimal("100.00"),
    ]
    assert insights["purchase_stats"] == {
        "count": 2,
        "total_qty": Decimal("3"),
        "total_amount": Decimal("320.00"),
        "avg_price": 110.0,
        "median_price": 110.0,
        "min_price": 100.0,
        "max_price": 120.0,
    }
    assert insights["market_stats"] is None
    assert insights["supplier_comparison"] == [
        {
            "supplier_name": supplier.name,
            "avg_price": 110.0,
            "count": 2,
            "last_date": (now - timedelta(days=3)).date().isoformat(),
        }
    ]
    assert all(row["deviation_pct"] is None for row in insights["purchase_history"])


async def test_get_insights_with_price_records_returns_market_stats_only(seeded_db_session):
    actor = await _user(seeded_db_session)
    item = await _item(seeded_db_session, "SKU-NET-S5248")
    today = date.today()

    await _create_price_record(
        seeded_db_session,
        actor=actor,
        item=item,
        price="150.00",
        quotation_date=today,
    )

    insights = await svc.get_insights(seeded_db_session, item.id, window_days=30)

    assert insights["purchase_history"] == []
    assert insights["purchase_stats"]["count"] == 0
    assert insights["market_stats"] == {
        "sample_count": 1,
        "avg_price": 150.0,
        "median_price": 150.0,
        "min_price": 150.0,
        "max_price": 150.0,
        "volatility_pct": 0.0,
        "current_price": 150.0,
        "current_vs_avg_pct": 0.0,
        "signal": "at_avg",
    }
    assert insights["supplier_comparison"] == []


async def test_get_insights_with_purchase_and_market_data_adds_deviation_pct(seeded_db_session):
    actor = await _user(seeded_db_session)
    supplier = await _supplier(seeded_db_session, "SUP-DELL")
    item = await _item(seeded_db_session, "SKU-SW-M365")
    purchase_at = datetime.now(UTC) - timedelta(days=4)

    await _create_purchase(
        seeded_db_session,
        actor=actor,
        supplier=supplier,
        item=item,
        unit_price="100.00",
        qty="5",
        created_at=purchase_at,
    )
    await _create_price_record(
        seeded_db_session,
        actor=actor,
        item=item,
        supplier=supplier,
        price="80.00",
        quotation_date=purchase_at.date(),
    )
    await _create_price_record(
        seeded_db_session,
        actor=actor,
        item=item,
        supplier=supplier,
        price="82.00",
        quotation_date=date.today(),
    )

    insights = await svc.get_insights(seeded_db_session, item.id, window_days=30)

    assert insights["market_stats"] is not None
    assert len(insights["purchase_history"]) == 1
    assert insights["purchase_history"][0]["deviation_pct"] == 25.0
