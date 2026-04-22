from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import select
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
    SupplierCreate,
    SupplierOut,
    SupplierUpdate,
)
from app.services import master_data as master_data_svc

router = APIRouter()


@router.get("/suppliers", response_model=list[SupplierOut], tags=["master-data"])
async def list_suppliers(
    _user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[SupplierOut]:
    result = await db.execute(
        select(Supplier).where(Supplier.is_active.is_(True)).order_by(Supplier.name)
    )
    return [SupplierOut.model_validate(s) for s in result.scalars().all()]


@router.get("/items", response_model=list[ItemOut], tags=["master-data"])
async def list_items(
    _user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[ItemOut]:
    result = await db.execute(select(Item).where(Item.is_active.is_(True)).order_by(Item.name))
    return [ItemOut.model_validate(i) for i in result.scalars().all()]


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
