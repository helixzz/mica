from __future__ import annotations

import statistics
from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    POItem,
    PurchaseOrder,
    SKUPriceRecord,
    Supplier,
)


async def get_insights(db: AsyncSession, item_id: UUID, window_days: int = 365) -> dict:
    cutoff = date.today() - timedelta(days=window_days)

    purchase_history = await _purchase_history(db, item_id, cutoff)
    purchase_stats = _compute_purchase_stats(purchase_history)
    market_stats = await _market_stats(db, item_id, cutoff)
    supplier_comparison = await _supplier_comparison(db, item_id, cutoff)

    if market_stats and purchase_history:
        for row in purchase_history:
            closest_market = await _closest_market_price(db, item_id, row["date"])
            if closest_market is not None and closest_market > 0:
                row["deviation_pct"] = round(
                    float((row["unit_price"] - closest_market) / closest_market * 100), 2
                )
            else:
                row["deviation_pct"] = None

    return {
        "purchase_history": purchase_history,
        "purchase_stats": purchase_stats,
        "market_stats": market_stats,
        "supplier_comparison": supplier_comparison,
    }


async def _purchase_history(db: AsyncSession, item_id: UUID, cutoff: date) -> list[dict]:
    stmt = (
        select(
            PurchaseOrder.created_at.label("po_date"),
            PurchaseOrder.po_number,
            POItem.unit_price,
            POItem.qty,
            POItem.amount,
            Supplier.name.label("supplier_name"),
        )
        .join(PurchaseOrder, POItem.po_id == PurchaseOrder.id)
        .outerjoin(Supplier, PurchaseOrder.supplier_id == Supplier.id)
        .where(POItem.item_id == item_id, PurchaseOrder.created_at >= cutoff)
        .order_by(PurchaseOrder.created_at.desc())
    )
    rows = (await db.execute(stmt)).all()
    return [
        {
            "date": r.po_date.date().isoformat()
            if hasattr(r.po_date, "date")
            else str(r.po_date)[:10],
            "supplier_name": r.supplier_name or "-",
            "unit_price": r.unit_price,
            "qty": r.qty,
            "amount": r.amount,
            "po_number": r.po_number,
            "deviation_pct": None,
        }
        for r in rows
    ]


def _compute_purchase_stats(history: list[dict]) -> dict:
    if not history:
        return {
            "count": 0,
            "total_qty": Decimal("0"),
            "total_amount": Decimal("0"),
            "avg_price": None,
            "median_price": None,
            "min_price": None,
            "max_price": None,
        }
    prices = [float(h["unit_price"]) for h in history]
    return {
        "count": len(history),
        "total_qty": sum(h["qty"] for h in history),
        "total_amount": sum(h["amount"] for h in history),
        "avg_price": round(statistics.mean(prices), 2),
        "median_price": round(statistics.median(prices), 2),
        "min_price": round(min(prices), 2),
        "max_price": round(max(prices), 2),
    }


async def _market_stats(db: AsyncSession, item_id: UUID, cutoff: date) -> dict | None:
    stmt = select(SKUPriceRecord.price).where(
        SKUPriceRecord.item_id == item_id,
        SKUPriceRecord.quotation_date >= cutoff,
    )
    rows = (await db.execute(stmt)).scalars().all()
    if not rows:
        return None

    prices = [float(p) for p in rows]
    avg = statistics.mean(prices)
    std = statistics.stdev(prices) if len(prices) > 1 else 0.0
    volatility = round(std / avg * 100, 2) if avg > 0 else 0.0

    latest_stmt = (
        select(SKUPriceRecord.price)
        .where(SKUPriceRecord.item_id == item_id)
        .order_by(SKUPriceRecord.quotation_date.desc())
        .limit(1)
    )
    latest_price = float((await db.execute(latest_stmt)).scalar() or avg)
    current_vs_avg = round((latest_price - avg) / avg * 100, 2) if avg > 0 else 0.0

    if current_vs_avg < -3:
        signal = "below_avg"
    elif current_vs_avg > 3:
        signal = "above_avg"
    else:
        signal = "at_avg"

    return {
        "sample_count": len(prices),
        "avg_price": round(avg, 2),
        "median_price": round(statistics.median(prices), 2),
        "min_price": round(min(prices), 2),
        "max_price": round(max(prices), 2),
        "volatility_pct": volatility,
        "current_price": round(latest_price, 2),
        "current_vs_avg_pct": current_vs_avg,
        "signal": signal,
    }


async def _supplier_comparison(db: AsyncSession, item_id: UUID, cutoff: date) -> list[dict]:
    stmt = (
        select(
            Supplier.name.label("supplier_name"),
            func.avg(POItem.unit_price).label("avg_price"),
            func.count(POItem.id).label("count"),
            func.max(PurchaseOrder.created_at).label("last_date"),
        )
        .join(PurchaseOrder, POItem.po_id == PurchaseOrder.id)
        .join(Supplier, PurchaseOrder.supplier_id == Supplier.id)
        .where(POItem.item_id == item_id, PurchaseOrder.created_at >= cutoff)
        .group_by(Supplier.name)
        .order_by(func.avg(POItem.unit_price))
    )
    rows = (await db.execute(stmt)).all()
    return [
        {
            "supplier_name": r.supplier_name,
            "avg_price": round(float(r.avg_price), 2),
            "count": r.count,
            "last_date": r.last_date.date().isoformat()
            if hasattr(r.last_date, "date")
            else str(r.last_date)[:10],
        }
        for r in rows
    ]


async def _closest_market_price(
    db: AsyncSession, item_id: UUID, purchase_date_str: str
) -> Decimal | None:
    purchase_date = date.fromisoformat(purchase_date_str)
    stmt = (
        select(SKUPriceRecord.price)
        .where(SKUPriceRecord.item_id == item_id)
        .order_by(func.abs(SKUPriceRecord.quotation_date - purchase_date))
        .limit(1)
    )
    result = (await db.execute(stmt)).scalar()
    return Decimal(str(result)) if result is not None else None
