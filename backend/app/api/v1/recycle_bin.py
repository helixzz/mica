from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser, require_roles
from app.db import get_db
from app.models import (
    AuditLog,
    Company,
    CostCenter,
    Department,
    Item,
    LookupValue,
    ProcurementCategory,
    Supplier,
)

router = APIRouter(
    prefix="/admin/recycle-bin",
    tags=["admin"],
    dependencies=[Depends(require_roles("admin"))],
)

ENTITY_MAP: dict[str, type] = {
    "company": Company,
    "department": Department,
    "cost_center": CostCenter,
    "procurement_category": ProcurementCategory,
    "lookup_value": LookupValue,
    "supplier": Supplier,
    "item": Item,
}

LABEL_FIELDS: dict[str, tuple[str, str]] = {
    "company": ("code", "name_zh"),
    "department": ("code", "name_zh"),
    "cost_center": ("code", "label_zh"),
    "procurement_category": ("code", "label_zh"),
    "lookup_value": ("code", "label_zh"),
    "supplier": ("code", "name"),
    "item": ("code", "name"),
}


class RecycleBinItem(BaseModel):
    entity_type: str
    entity_id: str
    code: str
    label: str
    deleted_at: str | None = None


@router.get("", response_model=list[RecycleBinItem])
async def list_deleted(
    _user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    results: list[RecycleBinItem] = []
    for entity_type, model in ENTITY_MAP.items():
        code_field, label_field = LABEL_FIELDS[entity_type]
        rows = (await db.execute(select(model).where(model.is_deleted.is_(True)))).scalars().all()
        for row in rows:
            results.append(
                RecycleBinItem(
                    entity_type=entity_type,
                    entity_id=str(row.id),
                    code=getattr(row, code_field, ""),
                    label=getattr(row, label_field, ""),
                    deleted_at=row.updated_at.isoformat()
                    if hasattr(row, "updated_at") and row.updated_at
                    else None,
                )
            )
    return results


@router.post("/{entity_type}/{entity_id}/restore")
async def restore_entity(
    entity_type: str,
    entity_id: UUID,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    model = ENTITY_MAP.get(entity_type)
    if model is None:
        raise HTTPException(404, "recycle_bin.unknown_entity_type")
    entity = await db.get(model, entity_id)
    if entity is None:
        raise HTTPException(404, "recycle_bin.entity_not_found")
    if not entity.is_deleted:
        raise HTTPException(400, "recycle_bin.not_deleted")
    entity.is_deleted = False
    entity.is_enabled = True
    db.add(
        AuditLog(
            actor_id=user.id,
            actor_name=user.display_name,
            event_type=f"{entity_type}.restored",
            resource_type=entity_type,
            resource_id=str(entity_id),
        )
    )
    await db.commit()
    return {"status": "restored", "entity_type": entity_type, "entity_id": str(entity_id)}
