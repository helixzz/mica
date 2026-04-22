from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import new_uuid
from app.models import CostCenter, LookupValue, ProcurementCategory


async def list_cost_centers(db: AsyncSession, active_only: bool = True) -> list[CostCenter]:
    q = select(CostCenter).order_by(CostCenter.sort_order)
    if active_only:
        q = q.where(CostCenter.is_active.is_(True))
    return list((await db.execute(q)).scalars().all())


async def create_cost_center(db: AsyncSession, data: dict) -> CostCenter:
    cc = CostCenter(id=new_uuid(), **data)
    db.add(cc)
    await db.flush()
    return cc


async def update_cost_center(db: AsyncSession, cc_id: UUID, data: dict) -> CostCenter:
    cc = await db.get(CostCenter, cc_id)
    if cc is None:
        raise HTTPException(404, "cost_center.not_found")
    for k, v in data.items():
        if v is not None and hasattr(cc, k):
            setattr(cc, k, v)
    await db.flush()
    return cc


async def delete_cost_center(db: AsyncSession, cc_id: UUID) -> None:
    cc = await db.get(CostCenter, cc_id)
    if cc is None:
        raise HTTPException(404, "cost_center.not_found")
    cc.is_active = False
    await db.flush()


async def list_procurement_categories(
    db: AsyncSession,
    active_only: bool = True,
    flat: bool = False,
) -> list[ProcurementCategory]:
    q = select(ProcurementCategory).order_by(
        ProcurementCategory.level,
        ProcurementCategory.sort_order,
    )
    if active_only:
        q = q.where(ProcurementCategory.is_active.is_(True))
    if not flat:
        q = q.options(selectinload(ProcurementCategory.children))
    return list((await db.execute(q)).scalars().unique().all())


async def get_category_tree(db: AsyncSession) -> list[ProcurementCategory]:
    q = (
        select(ProcurementCategory)
        .where(ProcurementCategory.parent_id.is_(None), ProcurementCategory.is_active.is_(True))
        .options(selectinload(ProcurementCategory.children))
        .order_by(ProcurementCategory.sort_order)
    )
    return list((await db.execute(q)).scalars().unique().all())


async def create_procurement_category(db: AsyncSession, data: dict) -> ProcurementCategory:
    level = 1
    if data.get("parent_id"):
        parent = await db.get(ProcurementCategory, data["parent_id"])
        if parent is None:
            raise HTTPException(404, "parent_category.not_found")
        level = parent.level + 1
    cat = ProcurementCategory(id=new_uuid(), level=level, **data)
    db.add(cat)
    await db.flush()
    return cat


async def update_procurement_category(
    db: AsyncSession, cat_id: UUID, data: dict
) -> ProcurementCategory:
    cat = await db.get(ProcurementCategory, cat_id)
    if cat is None:
        raise HTTPException(404, "category.not_found")
    for k, v in data.items():
        if v is not None and hasattr(cat, k):
            setattr(cat, k, v)
    await db.flush()
    return cat


async def delete_procurement_category(db: AsyncSession, cat_id: UUID) -> None:
    cat = await db.get(ProcurementCategory, cat_id)
    if cat is None:
        raise HTTPException(404, "category.not_found")
    cat.is_active = False
    await db.flush()


async def list_lookup_values(
    db: AsyncSession,
    type_: str,
    active_only: bool = True,
) -> list[LookupValue]:
    q = select(LookupValue).where(LookupValue.type == type_).order_by(LookupValue.sort_order)
    if active_only:
        q = q.where(LookupValue.is_active.is_(True))
    return list((await db.execute(q)).scalars().all())


async def create_lookup_value(db: AsyncSession, data: dict) -> LookupValue:
    lv = LookupValue(id=new_uuid(), **data)
    db.add(lv)
    await db.flush()
    return lv


async def update_lookup_value(db: AsyncSession, lv_id: UUID, data: dict) -> LookupValue:
    lv = await db.get(LookupValue, lv_id)
    if lv is None:
        raise HTTPException(404, "lookup_value.not_found")
    for k, v in data.items():
        if v is not None and hasattr(lv, k):
            setattr(lv, k, v)
    await db.flush()
    return lv


async def delete_lookup_value(db: AsyncSession, lv_id: UUID) -> None:
    lv = await db.get(LookupValue, lv_id)
    if lv is None:
        raise HTTPException(404, "lookup_value.not_found")
    lv.is_active = False
    await db.flush()
