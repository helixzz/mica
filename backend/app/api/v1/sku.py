from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser, require_roles
from app.db import get_db
from app.i18n import t
from app.services import sku as sku_svc

router = APIRouter()


class PriceRecordIn(BaseModel):
    item_id: UUID
    price: Decimal = Field(..., gt=0)
    quotation_date: date
    supplier_id: UUID | None = None
    source_type: Literal["manual", "quote", "actual_po", "market_research"] = "manual"
    source_ref: str | None = None
    notes: str | None = None


class PriceRecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    item_id: UUID
    supplier_id: UUID | None
    price: Decimal
    currency: str
    quotation_date: date
    source_type: str
    source_ref: str | None
    entered_by_id: UUID | None
    notes: str | None


class BenchmarkOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    item_id: UUID
    window_days: int
    avg_price: Decimal
    median_price: Decimal
    stddev: Decimal
    min_price: Decimal
    max_price: Decimal
    sample_size: int


class AnomalyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    item_id: UUID
    price_record_id: UUID | None
    baseline_avg_price: Decimal
    observed_price: Decimal
    deviation_pct: Decimal
    severity: str
    status: str
    notes: str | None


class AnomalyAckIn(BaseModel):
    notes: str | None = None


@router.post("/sku/prices", status_code=201, tags=["sku"])
async def record_price(
    payload: PriceRecordIn,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    _role: Annotated[None, Depends(require_roles("admin", "it_buyer", "procurement_mgr"))],
):
    record, anomaly = await sku_svc.record_price(
        db,
        user,
        item_id=payload.item_id,
        price=payload.price,
        quotation_date=payload.quotation_date,
        supplier_id=payload.supplier_id,
        source_type=payload.source_type,
        source_ref=payload.source_ref,
        notes=payload.notes,
    )
    return {
        "record": PriceRecordOut.model_validate(record).model_dump(mode="json"),
        "anomaly": AnomalyOut.model_validate(anomaly).model_dump(mode="json") if anomaly else None,
    }


@router.get("/sku/prices", response_model=list[PriceRecordOut], tags=["sku"])
async def list_prices(
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    item_id: UUID | None = None,
):
    rows = await sku_svc.list_price_records(db, item_id)
    return [PriceRecordOut.model_validate(r) for r in rows]


@router.get("/sku/benchmarks/{item_id}", response_model=BenchmarkOut | None, tags=["sku"])
async def get_benchmark(
    item_id: UUID,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    window_days: int | None = None,
):
    bm = await sku_svc.get_benchmark(db, item_id, window_days)
    if bm is None:
        return None
    return BenchmarkOut.model_validate(bm)


@router.get("/sku/trend/{item_id}", tags=["sku"])
async def get_trend(
    item_id: UUID,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    days: int | None = None,
):
    return await sku_svc.price_trend(db, item_id, days)


@router.get("/sku/anomalies", response_model=list[AnomalyOut], tags=["sku"])
async def list_anomalies(
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    status: str | None = None,
):
    rows = await sku_svc.list_anomalies(db, status)
    return [AnomalyOut.model_validate(a) for a in rows]


@router.post("/sku/anomalies/{anomaly_id}/acknowledge", response_model=AnomalyOut, tags=["sku"])
async def ack_anomaly(
    anomaly_id: UUID,
    payload: AnomalyAckIn,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    _role: Annotated[None, Depends(require_roles("admin", "it_buyer", "procurement_mgr"))],
):
    row = await sku_svc.acknowledge_anomaly(db, user, anomaly_id, payload.notes)
    return AnomalyOut.model_validate(row)


@router.get("/sku/insights/{item_id}", tags=["sku"])
async def get_insights(
    item_id: UUID,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    window_days: int = 365,
):
    from app.services.sku_insights import get_insights

    return await get_insights(db, item_id, window_days)


@router.get("/sku/reference-prices", tags=["sku"])
async def get_reference_prices(
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    item_ids: str = "",
):
    from sqlalchemy import func, select

    from app.models import SKUPriceRecord

    ids = [i.strip() for i in item_ids.split(",") if i.strip()]
    if not ids:
        return {}

    result = {}
    for item_id in ids:
        try:
            uid = UUID(item_id)
        except ValueError:
            continue

        latest_q = (
            select(SKUPriceRecord.price)
            .where(SKUPriceRecord.item_id == uid)
            .order_by(SKUPriceRecord.quotation_date.desc())
            .limit(1)
        )
        latest = (await db.execute(latest_q)).scalar()

        avg_q = select(func.avg(SKUPriceRecord.price)).where(SKUPriceRecord.item_id == uid)
        avg = (await db.execute(avg_q)).scalar()

        if latest is not None or avg is not None:
            result[item_id] = {
                "latest_price": float(latest) if latest else None,
                "avg_price": round(float(avg), 2) if avg else None,
            }
    return result


@router.get("/sku/reference-price/{item_id}", tags=["sku"])
async def get_reference_price(
    item_id: UUID,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    from sqlalchemy import select

    from app.models import SKUPriceRecord

    latest_q = (
        select(SKUPriceRecord.price)
        .where(SKUPriceRecord.item_id == item_id)
        .order_by(SKUPriceRecord.quotation_date.desc())
        .limit(1)
    )
    latest = (await db.execute(latest_q)).scalar()
    return {"price": float(latest) if latest is not None else None}


@router.get("/sku/{item_id}/forecast", tags=["sku"])
async def sku_price_forecast(
    item_id: UUID,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    from sqlalchemy import select

    from app.models import SKUPriceRecord

    since = datetime.now(UTC).date() - timedelta(days=90)
    rows = (
        (
            await db.execute(
                select(SKUPriceRecord)
                .where(
                    SKUPriceRecord.item_id == item_id,
                    SKUPriceRecord.quotation_date >= since,
                )
                .order_by(SKUPriceRecord.quotation_date)
            )
        )
        .scalars()
        .all()
    )

    if len(rows) < 3:
        return {
            "trend": "flat",
            "trend_label": t("sku.forecast.insufficient_data", user.preferred_locale),
            "next_month_prediction": None,
            "ma_7d": None,
            "ma_30d": None,
            "sample_size": len(rows),
        }

    date_prices: dict[date, list[float]] = defaultdict(list)
    for r in rows:
        date_prices[r.quotation_date].append(float(r.price))

    daily_avg = {d: sum(ps) / len(ps) for d, ps in sorted(date_prices.items())}
    dates = list(daily_avg.keys())
    prices = [daily_avg[d] for d in dates]

    def sma(values: list[float], window: int) -> list[float | None]:
        if len(values) < window:
            return [None] * len(values)
        result: list[float | None] = [None] * (window - 1)
        for i in range(window - 1, len(values)):
            result.append(sum(values[i - window + 1 : i + 1]) / window)
        return result

    ma7 = sma(prices, 7)
    ma30 = sma(prices, 30)

    last_ma7 = ma7[-1] if ma7[-1] is not None else prices[-1]
    recent_window = 15
    if len(prices) >= recent_window * 2:
        older_avg = sum(prices[-recent_window * 2 : -recent_window]) / recent_window
        recent_avg = sum(prices[-recent_window:]) / recent_window
    else:
        half = max(len(prices) // 2, 1)
        older_avg = sum(prices[:half]) / half
        recent_avg = sum(prices[half:]) / (len(prices) - half)

    change_pct = (recent_avg - older_avg) / older_avg * 100 if older_avg else 0
    if change_pct > 3:
        trend = "up"
    elif change_pct < -3:
        trend = "down"
    else:
        trend = "flat"

    prediction: float | None = None
    if len(prices) >= 5:
        daily_changes = [prices[i] - prices[i - 1] for i in range(1, len(prices))]
        avg_change = sum(daily_changes) / len(daily_changes)
        prediction = round(last_ma7 + avg_change * 30, 2)

    return {
        "trend": trend,
        "change_pct": round(change_pct, 2),
        "next_month_prediction": prediction,
        "ma_7d": round(last_ma7, 2),
        "ma_30d": round(ma30[-1], 2) if ma30[-1] is not None else None,
        "recent_avg": round(recent_avg, 2),
        "sample_size": len(rows),
    }
