from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser
from app.db import get_db
from app.models import Item, Supplier
from app.schemas import ItemOut, SupplierOut

router = APIRouter()


@router.get("/suppliers", response_model=list[SupplierOut], tags=["master-data"])
async def list_suppliers(
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[SupplierOut]:
    result = await db.execute(select(Supplier).where(Supplier.is_active == True).order_by(Supplier.name))  # noqa: E712
    return [SupplierOut.model_validate(s) for s in result.scalars().all()]


@router.get("/items", response_model=list[ItemOut], tags=["master-data"])
async def list_items(
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[ItemOut]:
    result = await db.execute(select(Item).where(Item.is_active == True).order_by(Item.name))  # noqa: E712
    return [ItemOut.model_validate(i) for i in result.scalars().all()]
