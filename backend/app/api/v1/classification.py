from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser, require_roles
from app.db import get_db
from app.services import classification as svc

router = APIRouter()


class CostCenterOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    code: str
    label_zh: str
    label_en: str
    sort_order: int
    is_enabled: bool
    is_deleted: bool
    budget_amount: float | None = None
    annual_budget: float | None = None
    budget_start_date: str | None = None
    budget_end_date: str | None = None


class CostCenterIn(BaseModel):
    code: str
    label_zh: str
    label_en: str
    sort_order: int = 0
    is_enabled: bool | None = None
    annual_budget: float | None = None
    budget_start_date: str | None = None
    budget_end_date: str | None = None


class ProcurementCategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    code: str
    label_zh: str
    label_en: str
    sort_order: int
    is_enabled: bool
    is_deleted: bool
    parent_id: UUID | None = None
    level: int


class ProcurementCategoryTreeOut(ProcurementCategoryOut):
    children: list[ProcurementCategoryOut] = []


class ProcurementCategoryIn(BaseModel):
    code: str
    label_zh: str
    label_en: str
    sort_order: int = 0
    parent_id: UUID | None = None


class LookupValueOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    type: str
    code: str
    label_zh: str
    label_en: str
    sort_order: int
    is_enabled: bool
    is_deleted: bool


class LookupValueIn(BaseModel):
    type: str
    code: str
    label_zh: str
    label_en: str
    sort_order: int = 0


@router.get("/cost-centers", response_model=list[CostCenterOut], tags=["classification"])
async def list_cost_centers(
    _user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    enabled_only: bool = True,
    include_deleted: bool = False,
):
    return await svc.list_cost_centers(
        db, enabled_only=enabled_only, include_deleted=include_deleted
    )


@router.post(
    "/admin/cost-centers", response_model=CostCenterOut, status_code=201, tags=["classification"]
)
async def create_cost_center(
    body: CostCenterIn,
    _user: Annotated[None, Depends(require_roles("admin", "procurement_mgr"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    cc = await svc.create_cost_center(db, body.model_dump())
    await db.commit()
    return cc


@router.put("/admin/cost-centers/{cc_id}", response_model=CostCenterOut, tags=["classification"])
async def update_cost_center(
    cc_id: UUID,
    body: CostCenterIn,
    _user: Annotated[None, Depends(require_roles("admin", "procurement_mgr"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    cc = await svc.update_cost_center(db, cc_id, body.model_dump())
    await db.commit()
    return cc


@router.delete("/admin/cost-centers/{cc_id}", status_code=204, tags=["classification"])
async def delete_cost_center(
    cc_id: UUID,
    _user: Annotated[None, Depends(require_roles("admin", "procurement_mgr"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await svc.delete_cost_center(db, cc_id)
    await db.commit()


@router.get(
    "/procurement-categories", response_model=list[ProcurementCategoryOut], tags=["classification"]
)
async def list_procurement_categories(
    _user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    active: bool = True,
):
    return await svc.list_procurement_categories(db, active_only=active, flat=True)


@router.get(
    "/procurement-categories/tree",
    response_model=list[ProcurementCategoryTreeOut],
    tags=["classification"],
)
async def get_category_tree(
    _user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await svc.get_category_tree(db)


@router.post(
    "/admin/procurement-categories",
    response_model=ProcurementCategoryOut,
    status_code=201,
    tags=["classification"],
)
async def create_procurement_category(
    body: ProcurementCategoryIn,
    _user: Annotated[None, Depends(require_roles("admin", "procurement_mgr"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    cat = await svc.create_procurement_category(db, body.model_dump())
    await db.commit()
    return cat


@router.put(
    "/admin/procurement-categories/{cat_id}",
    response_model=ProcurementCategoryOut,
    tags=["classification"],
)
async def update_procurement_category(
    cat_id: UUID,
    body: ProcurementCategoryIn,
    _user: Annotated[None, Depends(require_roles("admin", "procurement_mgr"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    cat = await svc.update_procurement_category(db, cat_id, body.model_dump())
    await db.commit()
    return cat


@router.delete("/admin/procurement-categories/{cat_id}", status_code=204, tags=["classification"])
async def delete_procurement_category(
    cat_id: UUID,
    _user: Annotated[None, Depends(require_roles("admin", "procurement_mgr"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await svc.delete_procurement_category(db, cat_id)
    await db.commit()


@router.get("/lookup-values", response_model=list[LookupValueOut], tags=["classification"])
async def list_lookup_values(
    _user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    type: Annotated[str, Query()],
    active: bool = True,
):
    return await svc.list_lookup_values(db, type_=type, active_only=active)


@router.post(
    "/admin/lookup-values", response_model=LookupValueOut, status_code=201, tags=["classification"]
)
async def create_lookup_value(
    body: LookupValueIn,
    _user: Annotated[None, Depends(require_roles("admin", "procurement_mgr"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    lv = await svc.create_lookup_value(db, body.model_dump())
    await db.commit()
    return lv


@router.put("/admin/lookup-values/{lv_id}", response_model=LookupValueOut, tags=["classification"])
async def update_lookup_value(
    lv_id: UUID,
    body: LookupValueIn,
    _user: Annotated[None, Depends(require_roles("admin", "procurement_mgr"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    lv = await svc.update_lookup_value(db, lv_id, body.model_dump())
    await db.commit()
    return lv


@router.delete("/admin/lookup-values/{lv_id}", status_code=204, tags=["classification"])
async def delete_lookup_value(
    lv_id: UUID,
    _user: Annotated[None, Depends(require_roles("admin", "procurement_mgr"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await svc.delete_lookup_value(db, lv_id)
    await db.commit()
