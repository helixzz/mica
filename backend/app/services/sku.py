"""SKU market price tracking, benchmark computation, anomaly detection."""
from __future__ import annotations

import statistics
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    AuditLog,
    Item,
    SKUPriceAnomaly,
    SKUPriceBenchmark,
    SKUPriceRecord,
    User,
)


def _as_decimal(v) -> Decimal:
    return v if isinstance(v, Decimal) else Decimal(str(v))


DEFAULT_WINDOW_DAYS = 90
DEFAULT_ANOMALY_THRESHOLD_PCT = Decimal("20")


async def record_price(
    db: AsyncSession,
    actor: User,
    item_id: UUID,
    price: Decimal,
    quotation_date: date,
    supplier_id: UUID | None = None,
    source_type: str = "manual",
    source_ref: str | None = None,
    notes: str | None = None,
    anomaly_threshold_pct: Decimal = DEFAULT_ANOMALY_THRESHOLD_PCT,
) -> tuple[SKUPriceRecord, SKUPriceAnomaly | None]:
    item = await db.get(Item, item_id)
    if item is None:
        raise HTTPException(404, "item.not_found")

    record = SKUPriceRecord(
        item_id=item_id,
        supplier_id=supplier_id,
        price=_as_decimal(price),
        currency="CNY",
        quotation_date=quotation_date,
        source_type=source_type,
        source_ref=source_ref,
        entered_by_id=actor.id,
        notes=notes,
    )
    db.add(record)
    await db.flush()

    benchmark = await _refresh_benchmark(db, item_id, window_days=DEFAULT_WINDOW_DAYS)
    anomaly: SKUPriceAnomaly | None = None
    if benchmark and benchmark.sample_size >= 3:
        dev_pct = (
            (_as_decimal(price) - benchmark.avg_price) / benchmark.avg_price * Decimal("100")
        ).quantize(Decimal("0.0001"))
        if abs(dev_pct) >= anomaly_threshold_pct:
            severity = "critical" if abs(dev_pct) >= anomaly_threshold_pct * 2 else "warning"
            anomaly = SKUPriceAnomaly(
                item_id=item_id,
                price_record_id=record.id,
                baseline_avg_price=benchmark.avg_price,
                observed_price=_as_decimal(price),
                deviation_pct=dev_pct,
                severity=severity,
                status="new",
            )
            db.add(anomaly)

    db.add(
        AuditLog(
            actor_id=actor.id,
            actor_name=actor.display_name,
            event_type="sku.price_recorded",
            resource_type="sku_price_record",
            resource_id=str(record.id),
            metadata_json={
                "item_id": str(item_id),
                "price": str(price),
                "source": source_type,
                "anomaly": anomaly is not None,
            },
        )
    )
    await db.commit()
    await db.refresh(record)
    if anomaly:
        await db.refresh(anomaly)
    return record, anomaly


async def _refresh_benchmark(
    db: AsyncSession, item_id: UUID, window_days: int = DEFAULT_WINDOW_DAYS
) -> SKUPriceBenchmark | None:
    since = datetime.now(timezone.utc).date() - timedelta(days=window_days)
    rows = (
        await db.execute(
            select(SKUPriceRecord.price).where(
                SKUPriceRecord.item_id == item_id,
                SKUPriceRecord.quotation_date >= since,
            )
        )
    ).scalars().all()
    if not rows:
        return None

    prices = [float(p) for p in rows]
    avg = statistics.mean(prices)
    med = statistics.median(prices)
    std = statistics.stdev(prices) if len(prices) >= 2 else 0.0
    mn = min(prices)
    mx = max(prices)

    existing = (
        await db.execute(
            select(SKUPriceBenchmark).where(
                SKUPriceBenchmark.item_id == item_id,
                SKUPriceBenchmark.window_days == window_days,
            )
        )
    ).scalar_one_or_none()
    if existing is None:
        bm = SKUPriceBenchmark(
            item_id=item_id,
            window_days=window_days,
            avg_price=Decimal(str(avg)).quantize(Decimal("0.0001")),
            median_price=Decimal(str(med)).quantize(Decimal("0.0001")),
            stddev=Decimal(str(std)).quantize(Decimal("0.0001")),
            min_price=Decimal(str(mn)).quantize(Decimal("0.0001")),
            max_price=Decimal(str(mx)).quantize(Decimal("0.0001")),
            sample_size=len(prices),
            last_refreshed_at=datetime.now(timezone.utc),
        )
        db.add(bm)
        await db.flush()
        return bm
    existing.avg_price = Decimal(str(avg)).quantize(Decimal("0.0001"))
    existing.median_price = Decimal(str(med)).quantize(Decimal("0.0001"))
    existing.stddev = Decimal(str(std)).quantize(Decimal("0.0001"))
    existing.min_price = Decimal(str(mn)).quantize(Decimal("0.0001"))
    existing.max_price = Decimal(str(mx)).quantize(Decimal("0.0001"))
    existing.sample_size = len(prices)
    existing.last_refreshed_at = datetime.now(timezone.utc)
    await db.flush()
    return existing


async def list_price_records(
    db: AsyncSession, item_id: UUID | None = None, limit: int = 200
) -> list[SKUPriceRecord]:
    stmt = select(SKUPriceRecord).order_by(SKUPriceRecord.quotation_date.desc()).limit(limit)
    if item_id:
        stmt = stmt.where(SKUPriceRecord.item_id == item_id)
    return list((await db.execute(stmt)).scalars().all())


async def get_benchmark(
    db: AsyncSession, item_id: UUID, window_days: int = DEFAULT_WINDOW_DAYS
) -> SKUPriceBenchmark | None:
    return (
        await db.execute(
            select(SKUPriceBenchmark).where(
                SKUPriceBenchmark.item_id == item_id,
                SKUPriceBenchmark.window_days == window_days,
            )
        )
    ).scalar_one_or_none()


async def list_anomalies(
    db: AsyncSession, status: str | None = None, limit: int = 100
) -> list[SKUPriceAnomaly]:
    stmt = select(SKUPriceAnomaly).order_by(SKUPriceAnomaly.created_at.desc()).limit(limit)
    if status:
        stmt = stmt.where(SKUPriceAnomaly.status == status)
    return list((await db.execute(stmt)).scalars().all())


async def acknowledge_anomaly(
    db: AsyncSession, actor: User, anomaly_id: UUID, notes: str | None = None
) -> SKUPriceAnomaly:
    row = await db.get(SKUPriceAnomaly, anomaly_id)
    if row is None:
        raise HTTPException(404, "anomaly.not_found")
    row.status = "acknowledged"
    row.acknowledged_by_id = actor.id
    row.acknowledged_at = datetime.now(timezone.utc)
    if notes:
        row.notes = notes
    await db.commit()
    await db.refresh(row)
    return row


async def price_trend(
    db: AsyncSession, item_id: UUID, days: int = 180
) -> list[dict]:
    since = datetime.now(timezone.utc).date() - timedelta(days=days)
    rows = (
        await db.execute(
            select(SKUPriceRecord).where(
                SKUPriceRecord.item_id == item_id,
                SKUPriceRecord.quotation_date >= since,
            ).order_by(SKUPriceRecord.quotation_date)
        )
    ).scalars().all()
    return [
        {
            "date": r.quotation_date.isoformat(),
            "price": str(r.price),
            "supplier_id": str(r.supplier_id) if r.supplier_id else None,
            "source_type": r.source_type,
        }
        for r in rows
    ]
