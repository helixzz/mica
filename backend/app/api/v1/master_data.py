from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser, require_roles
from app.db import get_db
from app.models import Item, Supplier
from app.schemas import (
    CompanyCreate,
    CompanyOut,
    CompanyUpdate,
    DepartmentCreate,
    DepartmentOut,
    DepartmentUpdate,
    ItemCreate,
    ItemOut,
    ItemUpdate,
    SupplierBatchUpdate,
    SupplierCreate,
    SupplierOut,
    SupplierUpdate,
)
from app.services import master_data as master_data_svc

router = APIRouter()


@router.get("/suppliers", tags=["master-data"])
async def list_suppliers(
    _user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    search: str | None = Query(None),
    is_enabled: bool | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
) -> dict:
    from sqlalchemy import or_

    query = select(Supplier).where(Supplier.is_deleted.is_(False))
    if is_enabled is not None:
        query = query.where(Supplier.is_enabled.is_(is_enabled))
    if search:
        pattern = f"%{search}%"
        query = query.where(
            or_(
                Supplier.name.ilike(pattern),
                Supplier.code.ilike(pattern),
            )
        )

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    offset = (page - 1) * page_size
    result = await db.execute(
        query.order_by(Supplier.name).offset(offset).limit(page_size)
    )
    suppliers = result.scalars().all()
    return {
        "items": [SupplierOut.model_validate(s) for s in suppliers],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/items", response_model=dict, tags=["master-data"])
async def list_items(
    _user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    category_id: UUID | None = Query(None),
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    include_inactive: bool = Query(False),
) -> dict:
    from sqlalchemy import or_

    query = select(Item).where(Item.is_deleted.is_(False))
    if not include_inactive:
        query = query.where(Item.is_enabled.is_(True))
    if category_id:
        query = query.where(Item.category_id == category_id)
    if search:
        pattern = f"%{search}%"
        query = query.where(
            or_(
                Item.name.ilike(pattern),
                Item.code.ilike(pattern),
                Item.specification.ilike(pattern),
            )
        )

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    offset = (page - 1) * page_size
    items = (
        (await db.execute(query.order_by(Item.name).offset(offset).limit(page_size)))
        .scalars()
        .all()
    )
    return {
        "items": [ItemOut.model_validate(i) for i in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post(
    "/suppliers",
    response_model=SupplierOut,
    status_code=status.HTTP_201_CREATED,
    tags=["master-data"],
)
async def create_supplier(
    payload: SupplierCreate,
    user: Annotated[CurrentUser, Depends(require_roles("admin", "procurement_mgr", "it_buyer"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SupplierOut:
    supplier = await master_data_svc.create_supplier(db, user, payload)
    return SupplierOut.model_validate(supplier)


@router.patch("/suppliers/{supplier_id}", response_model=SupplierOut, tags=["master-data"])
async def update_supplier(
    supplier_id: UUID,
    payload: SupplierUpdate,
    user: Annotated[CurrentUser, Depends(require_roles("admin", "procurement_mgr", "it_buyer"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SupplierOut:
    supplier = await master_data_svc.update_supplier(db, user, supplier_id, payload)
    return SupplierOut.model_validate(supplier)


@router.patch("/suppliers/batch", tags=["master-data"])
async def batch_update_suppliers(
    payload: SupplierBatchUpdate,
    user: Annotated[CurrentUser, Depends(require_roles("admin", "procurement_mgr", "it_buyer"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    result = await db.execute(
        select(Supplier).where(
            Supplier.id.in_(payload.ids),
            Supplier.is_deleted.is_(False),
        )
    )
    suppliers = result.scalars().all()
    for s in suppliers:
        s.is_enabled = payload.is_enabled
    await db.commit()
    return {"updated": len(suppliers)}


@router.delete(
    "/suppliers/{supplier_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["master-data"]
)
async def delete_supplier(
    supplier_id: UUID,
    user: Annotated[CurrentUser, Depends(require_roles("admin", "procurement_mgr", "it_buyer"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    hard: bool = False,
) -> Response:
    await master_data_svc.delete_supplier(db, user, supplier_id, hard=hard)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/items",
    response_model=ItemOut,
    status_code=status.HTTP_201_CREATED,
    tags=["master-data"],
)
async def create_item(
    payload: ItemCreate,
    user: Annotated[CurrentUser, Depends(require_roles("admin", "procurement_mgr", "it_buyer"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ItemOut:
    item = await master_data_svc.create_item(db, user, payload)
    return ItemOut.model_validate(item)


@router.patch("/items/{item_id}", response_model=ItemOut, tags=["master-data"])
async def update_item(
    item_id: UUID,
    payload: ItemUpdate,
    user: Annotated[CurrentUser, Depends(require_roles("admin", "procurement_mgr", "it_buyer"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ItemOut:
    item = await master_data_svc.update_item(db, user, item_id, payload)
    return ItemOut.model_validate(item)


@router.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["master-data"])
async def delete_item(
    item_id: UUID,
    user: Annotated[CurrentUser, Depends(require_roles("admin", "procurement_mgr", "it_buyer"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    hard: bool = False,
) -> Response:
    await master_data_svc.delete_item(db, user, item_id, hard=hard)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/companies",
    response_model=CompanyOut,
    status_code=status.HTTP_201_CREATED,
    tags=["master-data"],
)
async def create_company(
    payload: CompanyCreate,
    user: Annotated[CurrentUser, Depends(require_roles("admin"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CompanyOut:
    company = await master_data_svc.create_company(db, user, payload)
    return CompanyOut.model_validate(company)


@router.patch("/companies/{company_id}", response_model=CompanyOut, tags=["master-data"])
async def update_company(
    company_id: UUID,
    payload: CompanyUpdate,
    user: Annotated[CurrentUser, Depends(require_roles("admin"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CompanyOut:
    company = await master_data_svc.update_company(db, user, company_id, payload)
    return CompanyOut.model_validate(company)


@router.delete(
    "/companies/{company_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["master-data"]
)
async def delete_company(
    company_id: UUID,
    user: Annotated[CurrentUser, Depends(require_roles("admin"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    await master_data_svc.delete_company(db, user, company_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/departments",
    response_model=DepartmentOut,
    status_code=status.HTTP_201_CREATED,
    tags=["master-data"],
)
async def create_department(
    payload: DepartmentCreate,
    user: Annotated[CurrentUser, Depends(require_roles("admin"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DepartmentOut:
    department = await master_data_svc.create_department(db, user, payload)
    return DepartmentOut.model_validate(department)


@router.patch("/departments/{department_id}", response_model=DepartmentOut, tags=["master-data"])
async def update_department(
    department_id: UUID,
    payload: DepartmentUpdate,
    user: Annotated[CurrentUser, Depends(require_roles("admin"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DepartmentOut:
    department = await master_data_svc.update_department(db, user, department_id, payload)
    return DepartmentOut.model_validate(department)


@router.delete(
    "/departments/{department_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["master-data"],
)
async def delete_department(
    department_id: UUID,
    user: Annotated[CurrentUser, Depends(require_roles("admin"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    await master_data_svc.delete_department(db, user, department_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
