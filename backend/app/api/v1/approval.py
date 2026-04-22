from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser
from app.db import get_db
from app.models import ApprovalTask
from app.schemas import ApprovalInstanceOut, ApprovalTaskOut, PRDecisionIn
from app.services import approval as svc

router = APIRouter()


@router.get("/approval/pending", response_model=list[ApprovalTaskOut], tags=["approval"])
async def my_pending(user: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]):
    tasks = await svc.list_pending_tasks_for_user(db, user.id)
    result = []
    for t in tasks:
        out = ApprovalTaskOut.model_validate(t)
        if t.instance:
            out.biz_id = t.instance.biz_id
            out.biz_number = t.instance.biz_number
            out.biz_title = t.instance.title
            out.biz_amount = t.instance.amount
            if hasattr(t.instance, "submitter") and t.instance.submitter:
                out.submitter_name = t.instance.submitter.display_name
        result.append(out)
    return result


@router.get(
    "/approval/instances/by-biz", response_model=ApprovalInstanceOut | None, tags=["approval"]
)
async def get_by_biz(
    biz_type: str,
    biz_id: str,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    inst = await svc.get_instance_for_biz(db, biz_type, UUID(biz_id))
    if inst is None:
        return None
    return ApprovalInstanceOut.model_validate(inst)


@router.post(
    "/approval/tasks/{task_id}/action", response_model=ApprovalInstanceOut, tags=["approval"]
)
async def act_on_task(
    task_id: UUID,
    payload: PRDecisionIn,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    task = await db.get(ApprovalTask, task_id)
    if task is None:
        raise HTTPException(404, "approval.task_not_found")
    instance = await svc.act_on_task(db, user, task.instance_id, payload.action, payload.comment)
    await db.commit()
    await db.refresh(instance)
    return ApprovalInstanceOut.model_validate(instance)
