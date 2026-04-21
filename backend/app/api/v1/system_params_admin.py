from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser, require_roles
from app.db import get_db
from app.schemas import SystemParameterOut, SystemParameterUpdate
from app.services.system_params import system_params

router = APIRouter(prefix="/admin", dependencies=[Depends(require_roles("admin"))])


@router.get("/system-params", response_model=list[SystemParameterOut], tags=["admin"])
async def list_system_params(
    db: Annotated[AsyncSession, Depends(get_db)],
    category: str | None = None,
):
    rows = await system_params.get_all(db, category)
    return [SystemParameterOut.model_validate(row) for row in rows]


@router.get("/system-params/{key}", response_model=SystemParameterOut, tags=["admin"])
async def get_system_param(
    key: str,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    row = await system_params.get_param(db, key)
    if row is not None:
        return SystemParameterOut.model_validate(row)
    raise HTTPException(404, f"system_parameter.not_found:{key}")


@router.put("/system-params/{key}", response_model=SystemParameterOut, tags=["admin"])
async def update_system_param(
    key: str,
    payload: SystemParameterUpdate,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    row = await system_params.update(db, key, payload.value, str(user.id))
    await db.commit()
    await db.refresh(row)
    return SystemParameterOut.model_validate(row)


@router.post("/system-params/{key}/reset", response_model=SystemParameterOut, tags=["admin"])
async def reset_system_param(
    key: str,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    row = await system_params.reset(db, key, str(user.id))
    await db.commit()
    await db.refresh(row)
    return SystemParameterOut.model_validate(row)
