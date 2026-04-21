from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser
from app.db import get_db
from app.schemas import ApprovalInstanceOut, ApprovalTaskOut
from app.services import approval as svc


router = APIRouter()


@router.get("/approval/pending", response_model=list[ApprovalTaskOut], tags=["approval"])
async def my_pending(
    user: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]
):
    tasks = await svc.list_pending_tasks_for_user(db, user.id)
    return [ApprovalTaskOut.model_validate(t) for t in tasks]


@router.get("/approval/instances/by-biz", response_model=ApprovalInstanceOut | None, tags=["approval"])
async def get_by_biz(
    biz_type: str, biz_id: str,
    user: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)],
):
    from uuid import UUID
    inst = await svc.get_instance_for_biz(db, biz_type, UUID(biz_id))
    if inst is None:
        return None
    return ApprovalInstanceOut.model_validate(inst)
