# pyright: reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnusedCallResult=false, reportOptionalMemberAccess=false

from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app.models import Item, Supplier, User
from app.services import sku as sku_svc


async def _get_alice(db) -> User:
    return (await db.execute(select(User).where(User.username == "alice"))).scalar_one()


async def _get_items(db) -> list[Item]:
    return list((await db.execute(select(Item).order_by(Item.code))).scalars().all())


async def _get_supplier(db) -> Supplier:
    return (await db.execute(select(Supplier))).scalars().first()


async def _record_price(
    db,
    *,
    actor: User,
    item_id,
    price: str,
    quotation_date: date,
    supplier_id=None,
    source_type: str = "manual",
):
    return await sku_svc.record_price(
        db,
        actor=actor,
        item_id=item_id,
        price=Decimal(price),
        quotation_date=quotation_date,
        supplier_id=supplier_id,
        source_type=source_type,
    )


async def _create_anomaly(db, *, actor: User, item_id, supplier_id=None):
    today = date.today()
    await _record_price(
        db,
        actor=actor,
        item_id=item_id,
        price="100.00",
        quotation_date=today - timedelta(days=2),
        supplier_id=supplier_id,
    )
    await _record_price(
        db,
        actor=actor,
        item_id=item_id,
        price="100.00",
        quotation_date=today - timedelta(days=1),
        supplier_id=supplier_id,
    )
    return await _record_price(
        db,
        actor=actor,
        item_id=item_id,
        price="300.00",
        quotation_date=today,
        supplier_id=supplier_id,
    )


async def test_record_price_basic_recording(seeded_db_session):
    alice = await _get_alice(seeded_db_session)
    item = (await seeded_db_session.execute(select(Item))).scalars().first()

    record, anomaly = await _record_price(
        seeded_db_session,
        actor=alice,
        item_id=item.id,
        price="100.00",
        quotation_date=date.today(),
    )

    assert record.item_id == item.id
    assert record.price == Decimal("100.00")
    assert record.currency == "CNY"
    assert record.source_type == "manual"
    assert anomaly is None


async def test_record_price_detects_anomaly_when_price_far_from_benchmark(seeded_db_session):
    alice = await _get_alice(seeded_db_session)
    item = (await seeded_db_session.execute(select(Item))).scalars().first()
    supplier = await _get_supplier(seeded_db_session)

    record, anomaly = await _create_anomaly(
        seeded_db_session,
        actor=alice,
        item_id=item.id,
        supplier_id=supplier.id,
    )

    assert record.price == Decimal("300.00")
    assert anomaly is not None
    assert anomaly.item_id == item.id
    assert anomaly.price_record_id == record.id
    assert anomaly.observed_price == Decimal("300.00")
    assert anomaly.severity == "critical"
    assert anomaly.status == "new"
    assert anomaly.deviation_pct > Decimal("20")


async def test_record_price_missing_item_raises_404(seeded_db_session):
    alice = await _get_alice(seeded_db_session)

    with pytest.raises(HTTPException) as exc:
        await _record_price(
            seeded_db_session,
            actor=alice,
            item_id=uuid4(),
            price="100.00",
            quotation_date=date.today(),
        )

    assert exc.value.status_code == 404
    assert exc.value.detail == "item.not_found"


async def test_list_price_records_without_filter_returns_all_records(seeded_db_session):
    alice = await _get_alice(seeded_db_session)
    items = await _get_items(seeded_db_session)
    first, _ = await _record_price(
        seeded_db_session,
        actor=alice,
        item_id=items[0].id,
        price="100.00",
        quotation_date=date.today() - timedelta(days=1),
    )
    second, _ = await _record_price(
        seeded_db_session,
        actor=alice,
        item_id=items[1].id,
        price="200.00",
        quotation_date=date.today(),
    )

    rows = await sku_svc.list_price_records(seeded_db_session)

    assert {first.id, second.id}.issubset({row.id for row in rows})


async def test_list_price_records_with_item_filter_returns_matching_rows(seeded_db_session):
    alice = await _get_alice(seeded_db_session)
    items = await _get_items(seeded_db_session)
    target_item = items[0]
    other_item = items[1]
    target_record, _ = await _record_price(
        seeded_db_session,
        actor=alice,
        item_id=target_item.id,
        price="101.00",
        quotation_date=date.today(),
    )
    await _record_price(
        seeded_db_session,
        actor=alice,
        item_id=other_item.id,
        price="202.00",
        quotation_date=date.today(),
    )

    rows = await sku_svc.list_price_records(seeded_db_session, item_id=target_item.id)

    assert [row.id for row in rows] == [target_record.id]
    assert all(row.item_id == target_item.id for row in rows)


async def test_get_benchmark_returns_none_when_no_prices_exist(seeded_db_session):
    item = (await seeded_db_session.execute(select(Item))).scalars().first()

    benchmark = await sku_svc.get_benchmark(seeded_db_session, item.id)

    assert benchmark is None


async def test_get_benchmark_returns_created_benchmark_from_recorded_prices(seeded_db_session):
    alice = await _get_alice(seeded_db_session)
    item = (await seeded_db_session.execute(select(Item))).scalars().first()
    today = date.today()
    await _record_price(
        seeded_db_session,
        actor=alice,
        item_id=item.id,
        price="100.00",
        quotation_date=today - timedelta(days=2),
    )
    await _record_price(
        seeded_db_session,
        actor=alice,
        item_id=item.id,
        price="110.00",
        quotation_date=today - timedelta(days=1),
    )
    await _record_price(
        seeded_db_session,
        actor=alice,
        item_id=item.id,
        price="90.00",
        quotation_date=today,
    )

    benchmark = await sku_svc.get_benchmark(seeded_db_session, item.id)

    assert benchmark is not None
    assert benchmark.item_id == item.id
    assert benchmark.window_days == 90
    assert benchmark.sample_size == 3
    assert benchmark.avg_price == Decimal("100.0000")
    assert benchmark.median_price == Decimal("100.0000")
    assert benchmark.min_price == Decimal("90.0000")
    assert benchmark.max_price == Decimal("110.0000")


async def test_get_benchmark_reflects_updates_after_more_prices(seeded_db_session):
    alice = await _get_alice(seeded_db_session)
    item = (await seeded_db_session.execute(select(Item))).scalars().first()
    today = date.today()
    first_record = None
    for days_ago in (3, 2, 1):
        record, _ = await _record_price(
            seeded_db_session,
            actor=alice,
            item_id=item.id,
            price="100.00",
            quotation_date=today - timedelta(days=days_ago),
        )
        if first_record is None:
            first_record = record

    first = await sku_svc.get_benchmark(seeded_db_session, item.id)
    assert first is not None
    assert first.sample_size == 3
    assert first.avg_price == Decimal("100.0000")
    assert first.last_refreshed_at >= first_record.created_at

    await _record_price(
        seeded_db_session,
        actor=alice,
        item_id=item.id,
        price="130.00",
        quotation_date=today,
    )
    updated = await sku_svc.get_benchmark(seeded_db_session, item.id)

    assert updated is not None
    assert updated.sample_size == 4
    assert updated.avg_price == Decimal("107.5000")
    assert updated.max_price == Decimal("130.0000")


async def test_list_anomalies_without_status_filter_returns_all_rows(seeded_db_session):
    alice = await _get_alice(seeded_db_session)
    items = await _get_items(seeded_db_session)

    _, first_anomaly = await _create_anomaly(
        seeded_db_session,
        actor=alice,
        item_id=items[0].id,
    )
    _, second_anomaly = await _create_anomaly(
        seeded_db_session,
        actor=alice,
        item_id=items[1].id,
    )

    rows = await sku_svc.list_anomalies(seeded_db_session)

    assert first_anomaly is not None
    assert second_anomaly is not None
    assert {first_anomaly.id, second_anomaly.id}.issubset({row.id for row in rows})


async def test_list_anomalies_with_status_filter_returns_matching_rows(seeded_db_session):
    alice = await _get_alice(seeded_db_session)
    items = await _get_items(seeded_db_session)
    _, first_anomaly = await _create_anomaly(
        seeded_db_session,
        actor=alice,
        item_id=items[0].id,
    )
    _, second_anomaly = await _create_anomaly(
        seeded_db_session,
        actor=alice,
        item_id=items[1].id,
    )
    acknowledged = await sku_svc.acknowledge_anomaly(
        seeded_db_session,
        actor=alice,
        anomaly_id=first_anomaly.id,
        notes="reviewed",
    )

    new_rows = await sku_svc.list_anomalies(seeded_db_session, status="new")
    acknowledged_rows = await sku_svc.list_anomalies(seeded_db_session, status="acknowledged")

    assert second_anomaly.id in {row.id for row in new_rows}
    assert acknowledged.id not in {row.id for row in new_rows}
    assert [row.id for row in acknowledged_rows] == [acknowledged.id]


async def test_acknowledge_anomaly_success_updates_status_and_notes(seeded_db_session):
    alice = await _get_alice(seeded_db_session)
    item = (await seeded_db_session.execute(select(Item))).scalars().first()
    _, anomaly = await _create_anomaly(seeded_db_session, actor=alice, item_id=item.id)

    updated = await sku_svc.acknowledge_anomaly(
        seeded_db_session,
        actor=alice,
        anomaly_id=anomaly.id,
        notes="handled",
    )

    assert updated.status == "acknowledged"
    assert updated.acknowledged_by_id == alice.id
    assert updated.acknowledged_at is not None
    assert updated.notes == "handled"


async def test_acknowledge_anomaly_not_found_raises_404(seeded_db_session):
    alice = await _get_alice(seeded_db_session)

    with pytest.raises(HTTPException) as exc:
        await sku_svc.acknowledge_anomaly(seeded_db_session, actor=alice, anomaly_id=uuid4())

    assert exc.value.status_code == 404
    assert exc.value.detail == "anomaly.not_found"


async def test_price_trend_returns_price_history_in_date_order(seeded_db_session):
    alice = await _get_alice(seeded_db_session)
    supplier = await _get_supplier(seeded_db_session)
    item = (await seeded_db_session.execute(select(Item))).scalars().first()
    today = date.today()
    await _record_price(
        seeded_db_session,
        actor=alice,
        item_id=item.id,
        price="120.00",
        quotation_date=today,
        supplier_id=supplier.id,
        source_type="manual",
    )
    await _record_price(
        seeded_db_session,
        actor=alice,
        item_id=item.id,
        price="100.00",
        quotation_date=today - timedelta(days=2),
        supplier_id=supplier.id,
        source_type="manual",
    )
    await _record_price(
        seeded_db_session,
        actor=alice,
        item_id=item.id,
        price="110.00",
        quotation_date=today - timedelta(days=1),
        supplier_id=supplier.id,
        source_type="manual",
    )

    trend = await sku_svc.price_trend(seeded_db_session, item.id)

    assert [row["date"] for row in trend] == [
        (today - timedelta(days=2)).isoformat(),
        (today - timedelta(days=1)).isoformat(),
        today.isoformat(),
    ]
    assert [row["price"] for row in trend] == ["100.0000", "110.0000", "120.0000"]
    assert all(row["supplier_id"] == str(supplier.id) for row in trend)
    assert all(row["source_type"] == "manual" for row in trend)


async def test_price_trend_respects_days_filter(seeded_db_session):
    alice = await _get_alice(seeded_db_session)
    item = (await seeded_db_session.execute(select(Item))).scalars().first()
    today = date.today()
    await _record_price(
        seeded_db_session,
        actor=alice,
        item_id=item.id,
        price="90.00",
        quotation_date=today - timedelta(days=40),
    )
    await _record_price(
        seeded_db_session,
        actor=alice,
        item_id=item.id,
        price="95.00",
        quotation_date=today - timedelta(days=5),
    )

    trend = await sku_svc.price_trend(seeded_db_session, item.id, days=30)

    assert trend == [
        {
            "date": (today - timedelta(days=5)).isoformat(),
            "price": "95.0000",
            "supplier_id": None,
            "source_type": "manual",
        }
    ]
