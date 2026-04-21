from datetime import date
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser
from app.db import get_db
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
):
    row = await sku_svc.acknowledge_anomaly(db, user, anomaly_id, payload.notes)
    return AnomalyOut.model_validate(row)
