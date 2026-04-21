from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import ApprovalInstance, ApprovalTask, User, UserRole


def _as_decimal(v: Any) -> Decimal:
    return v if isinstance(v, Decimal) else Decimal(str(v))


async def _resolve_approver(db: AsyncSession, submitter: User, amount: Decimal) -> User:
    if amount >= Decimal("100000"):
        stmt = select(User).where(
            User.company_id == submitter.company_id,
            User.role == UserRole.PROCUREMENT_MGR.value,
            User.is_active.is_(True),
        )
        result = (await db.execute(stmt)).scalar_one_or_none()
        if result:
            return result

    stmt = select(User).where(
        User.company_id == submitter.company_id,
        User.role == UserRole.DEPT_MANAGER.value,
        User.is_active.is_(True),
    )
    if submitter.department_id:
        stmt = stmt.where(User.department_id == submitter.department_id)
    result = (await db.execute(stmt)).scalar_one_or_none()
    if result:
        return result

    stmt = select(User).where(User.role == UserRole.ADMIN.value, User.is_active.is_(True))
    result = (await db.execute(stmt)).scalar_one_or_none()
    if not result:
        raise HTTPException(500, "no_approver_found")
    return result


async def create_instance_for_pr(
    db: AsyncSession,
    submitter: User,
    biz_type: str,
    biz_id: UUID,
    biz_number: str,
    title: str,
    amount: Decimal,
) -> ApprovalInstance:
    approver = await _resolve_approver(db, submitter, amount)
    stage_name = "部门负责人审批 / Department Manager" \
        if approver.role == UserRole.DEPT_MANAGER.value \
        else "采购经理审批 / Procurement Manager" \
        if approver.role == UserRole.PROCUREMENT_MGR.value \
        else "管理员审批 / Administrator"

    instance = ApprovalInstance(
        biz_type=biz_type,
        biz_id=biz_id,
        biz_number=biz_number,
        title=title,
        status="pending",
        current_stage=1,
        total_stages=1,
        submitter_id=submitter.id,
        company_id=submitter.company_id,
        amount=_as_decimal(amount),
        submitted_at=datetime.now(timezone.utc),
    )
    db.add(instance)
    await db.flush()

    task = ApprovalTask(
        instance_id=instance.id,
        stage_order=1,
        stage_name=stage_name,
        assignee_id=approver.id,
        assignee_role=approver.role,
        status="pending",
    )
    db.add(task)
    await db.flush()
    return instance


async def list_pending_tasks_for_user(
    db: AsyncSession, user_id: UUID
) -> list[ApprovalTask]:
    stmt = (
        select(ApprovalTask)
        .where(ApprovalTask.assignee_id == user_id, ApprovalTask.status == "pending")
        .options(selectinload(ApprovalTask.instance))
        .order_by(ApprovalTask.assigned_at.desc())
    )
    return list((await db.execute(stmt)).scalars().all())


async def find_task_for_user(
    db: AsyncSession, instance_id: UUID, user: User
) -> ApprovalTask | None:
    stmt = select(ApprovalTask).where(
        ApprovalTask.instance_id == instance_id,
        ApprovalTask.status == "pending",
    )
    tasks = list((await db.execute(stmt)).scalars().all())
    for t in tasks:
        if t.assignee_id == user.id:
            return t
    if user.role == UserRole.ADMIN.value and tasks:
        return tasks[0]
    return None


async def act_on_task(
    db: AsyncSession,
    user: User,
    instance_id: UUID,
    action: str,
    comment: str | None,
) -> ApprovalInstance:
    if action not in {"approve", "reject", "return"}:
        raise HTTPException(422, "invalid_action")
    task = await find_task_for_user(db, instance_id, user)
    if task is None:
        raise HTTPException(403, "no_pending_task_for_you")

    task.action = action
    task.status = "approved" if action == "approve" else "rejected" if action == "reject" else "returned"
    task.comment = comment
    task.acted_at = datetime.now(timezone.utc)

    instance = (
        await db.execute(
            select(ApprovalInstance).where(ApprovalInstance.id == instance_id)
        )
    ).scalar_one()
    if action == "approve":
        instance.status = "approved"
    elif action == "reject":
        instance.status = "rejected"
    else:
        instance.status = "returned"
    instance.completed_at = datetime.now(timezone.utc)
    return instance


async def get_instance_for_biz(
    db: AsyncSession, biz_type: str, biz_id: UUID
) -> ApprovalInstance | None:
    stmt = (
        select(ApprovalInstance)
        .where(
            ApprovalInstance.biz_type == biz_type,
            ApprovalInstance.biz_id == biz_id,
        )
        .options(selectinload(ApprovalInstance.tasks))
        .order_by(ApprovalInstance.submitted_at.desc())
    )
    return (await db.execute(stmt)).scalars().first()


async def count_pending_for_user(db: AsyncSession, user_id: UUID) -> int:
    stmt = select(func.count(ApprovalTask.id)).where(
        ApprovalTask.assignee_id == user_id,
        ApprovalTask.status == "pending",
    )
    return int((await db.execute(stmt)).scalar_one())
