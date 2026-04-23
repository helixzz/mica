from __future__ import annotations

# pyright: reportAny=false, reportExplicitAny=false, reportUnknownVariableType=false, reportArgumentType=false
import logging
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.i18n import t
from app.models import (
    ApprovalInstance,
    ApprovalRule,
    ApprovalTask,
    ApproverDelegation,
    NotificationCategory,
    User,
    UserRole,
)
from app.services.notifications import create_notification
from app.services.system_params import system_params

logger = logging.getLogger(__name__)

TASK_STATUS_PENDING = "pending"
TASK_STATUS_WAITING = "waiting"
TASK_STATUS_SKIPPED = "skipped"
INSTANCE_STATUS_PENDING = "pending"

ROLE_STAGE_NAMES = {
    UserRole.DEPT_MANAGER.value: "部门负责人审批 / Department Manager",
    UserRole.PROCUREMENT_MGR.value: "采购经理审批 / Procurement Manager",
    UserRole.ADMIN.value: "管理员审批 / Administrator",
    UserRole.FINANCE_AUDITOR.value: "财务审核 / Finance Auditor",
    UserRole.IT_BUYER.value: "IT采购审批 / IT Buyer",
}


def _as_decimal(v: Decimal | int | float | str) -> Decimal:
    return v if isinstance(v, Decimal) else Decimal(str(v))


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _normalize_stage(stage: Mapping[str, object]) -> dict[str, str | int]:
    order_raw = stage.get("order")
    if not isinstance(order_raw, int):
        order = int(str(order_raw or 0))
    else:
        order = order_raw
    approver_role = str(stage.get("approver_role") or "").strip()
    if not approver_role:
        raise HTTPException(500, "approval.rule_invalid_stage")
    stage_name = str(stage.get("stage_name") or "").strip() or ROLE_STAGE_NAMES.get(
        approver_role,
        approver_role,
    )
    return {
        "order": order,
        "approver_role": approver_role,
        "stage_name": stage_name,
    }


def _sort_stages(stages: Sequence[Mapping[str, object]]) -> list[dict[str, str | int]]:
    normalized = [_normalize_stage(stage) for stage in stages]
    normalized.sort(key=lambda item: (item["order"], item["stage_name"]))
    return normalized


async def _resolve_user_for_role(
    db: AsyncSession,
    submitter: User,
    approver_role: str,
) -> list[User]:
    stmt = select(User).where(
        User.company_id == submitter.company_id,
        User.role == approver_role,
        User.is_active.is_(True),
    )
    if approver_role == UserRole.DEPT_MANAGER.value and submitter.department_id:
        stmt = stmt.where(User.department_id == submitter.department_id)
    users = list((await db.execute(stmt)).scalars().all())
    if users:
        return users

    if approver_role != UserRole.ADMIN.value:
        admin_stmt = select(User).where(
            User.role == UserRole.ADMIN.value,
            User.is_active.is_(True),
        )
        admins = list((await db.execute(admin_stmt)).scalars().all())
        if admins:
            return admins

    raise HTTPException(500, "no_approver_found")


async def _resolve_active_delegation(
    db: AsyncSession,
    approver: User,
) -> ApproverDelegation | None:
    now = _utcnow()
    stmt = (
        select(ApproverDelegation)
        .where(
            ApproverDelegation.from_user_id == approver.id,
            ApproverDelegation.is_active.is_(True),
            ApproverDelegation.revoked_at.is_(None),
            ApproverDelegation.starts_at <= now,
            ApproverDelegation.ends_at > now,
        )
        .order_by(ApproverDelegation.starts_at.desc(), ApproverDelegation.created_at.desc())
    )
    candidates = list((await db.execute(stmt)).scalars().all())
    for delegation in candidates:
        delegate = await db.get(User, delegation.to_user_id)
        if delegate and delegate.is_active:
            return delegation
    return None


async def _resolve_stage_assignment(
    db: AsyncSession,
    submitter: User,
    approver_role: str,
) -> list[tuple[User, dict[str, object]]]:
    candidates = await _resolve_user_for_role(db, submitter, approver_role)
    assignments: list[tuple[User, dict[str, object]]] = []
    for candidate in candidates:
        delegation = await _resolve_active_delegation(db, candidate)
        if delegation is None:
            assignments.append((candidate, {}))
            continue
        delegate = await db.get(User, delegation.to_user_id)
        if delegate is None or not delegate.is_active:
            assignments.append((candidate, {}))
            continue
        assignments.append(
            (
                delegate,
                {
                    "delegation": {
                        "delegation_id": str(delegation.id),
                        "from_user_id": str(candidate.id),
                        "to_user_id": str(delegate.id),
                        "reason": delegation.reason,
                        "starts_at": delegation.starts_at.isoformat(),
                        "ends_at": delegation.ends_at.isoformat(),
                    }
                },
            )
        )
    seen_ids: set[UUID] = set()
    deduped: list[tuple[User, dict[str, object]]] = []
    for user, meta in assignments:
        if user.id not in seen_ids:
            seen_ids.add(user.id)
            deduped.append((user, meta))
    return deduped


async def _match_rule(
    db: AsyncSession,
    biz_type: str,
    amount: Decimal,
) -> ApprovalRule | None:
    stmt = (
        select(ApprovalRule)
        .where(
            ApprovalRule.biz_type == biz_type,
            ApprovalRule.is_active.is_(True),
            or_(ApprovalRule.amount_min.is_(None), ApprovalRule.amount_min <= amount),
            or_(ApprovalRule.amount_max.is_(None), ApprovalRule.amount_max > amount),
        )
        .order_by(ApprovalRule.priority.asc(), ApprovalRule.created_at.asc())
    )
    return (await db.execute(stmt)).scalars().first()


def _legacy_stage_name(role: str) -> str:
    return ROLE_STAGE_NAMES.get(role, "管理员审批 / Administrator")


def _notification_meta(instance: ApprovalInstance, task: ApprovalTask) -> dict[str, object]:
    meta: dict[str, object] = {
        "pr_no": instance.biz_number,
        "amount": str(instance.amount) if instance.amount is not None else None,
        "approval_instance_id": str(instance.id),
        "stage_name": task.stage_name,
        "stage_order": task.stage_order,
    }
    delegation = task.meta.get("delegation")
    if delegation:
        meta["delegation"] = task.meta["delegation"]
    return meta


async def _send_assignment_notification(
    db: AsyncSession,
    instance: ApprovalInstance,
    task: ApprovalTask,
) -> None:
    try:
        _ = await create_notification(
            db,
            user_id=task.assignee_id,
            category=NotificationCategory.APPROVAL,
            title=lambda current_user: t(
                "notification.approval.new_task",
                current_user.preferred_locale
                if current_user and current_user.preferred_locale
                else "zh-CN",
                title=instance.title,
            ),
            link_url="/approvals",
            biz_type="approval_task",
            biz_id=task.id,
            meta=_notification_meta(instance, task),
        )
    except Exception:
        logger.warning("failed to create approval assignment notification", exc_info=True)


async def create_instance_for_pr(
    db: AsyncSession,
    submitter: User,
    biz_type: str,
    biz_id: UUID,
    biz_number: str,
    title: str,
    amount: Decimal,
) -> ApprovalInstance:
    resolved_amount = _as_decimal(amount)
    rule = await _match_rule(db, biz_type, resolved_amount)

    if rule is None:
        approval_threshold = await system_params.get_int(db, "approval.amount_threshold_cny")
        fallback_role = (
            UserRole.PROCUREMENT_MGR.value
            if resolved_amount >= Decimal(str(approval_threshold))
            else UserRole.DEPT_MANAGER.value
        )
        stages = [
            {
                "order": 1,
                "approver_role": fallback_role,
                "stage_name": _legacy_stage_name(fallback_role),
                "legacy": True,
            }
        ]
        matched_rule_id: str | None = None
    else:
        stages = _sort_stages(rule.stages)
        matched_rule_id = str(rule.id)

    first_stage_order = stages[0]["order"]

    instance = ApprovalInstance(
        biz_type=biz_type,
        biz_id=biz_id,
        biz_number=biz_number,
        title=title,
        status=INSTANCE_STATUS_PENDING,
        current_stage=first_stage_order,
        total_stages=len(stages),
        submitter_id=submitter.id,
        company_id=submitter.company_id,
        amount=resolved_amount,
        submitted_at=_utcnow(),
    )
    db.add(instance)
    await db.flush()

    first_pending_tasks: list[ApprovalTask] = []
    for index, stage in enumerate(stages, start=1):
        stage_role = str(stage["approver_role"])
        assignees = await _resolve_stage_assignment(db, submitter, stage_role)
        stage_order = stage["order"]
        for approver, delegation_meta in assignees:
            meta = {
                **delegation_meta,
                "original_approver_role": stage_role,
            }
            if matched_rule_id is not None:
                meta["approval_rule_id"] = matched_rule_id
            task = ApprovalTask(
                instance_id=instance.id,
                stage_order=stage_order,
                stage_name=str(stage["stage_name"]),
                assignee_id=approver.id,
                assignee_role=stage_role,
                status=TASK_STATUS_PENDING if index == 1 else TASK_STATUS_WAITING,
                meta=meta,
            )
            db.add(task)
            if index == 1:
                first_pending_tasks.append(task)

    await db.flush()
    for task in first_pending_tasks:
        await _send_assignment_notification(db, instance, task)
    return instance


async def list_pending_tasks_for_user(db: AsyncSession, user_id: UUID) -> list[ApprovalTask]:
    stmt = (
        select(ApprovalTask)
        .where(ApprovalTask.assignee_id == user_id, ApprovalTask.status == TASK_STATUS_PENDING)
        .options(selectinload(ApprovalTask.instance).selectinload(ApprovalInstance.submitter))
        .order_by(ApprovalTask.assigned_at.desc())
    )
    return list((await db.execute(stmt)).scalars().all())


async def find_task_for_user(
    db: AsyncSession, instance_id: UUID, user: User
) -> ApprovalTask | None:
    stmt = select(ApprovalTask).where(
        ApprovalTask.instance_id == instance_id,
        ApprovalTask.status == TASK_STATUS_PENDING,
    )
    tasks = list((await db.execute(stmt)).scalars().all())
    for task in tasks:
        if task.assignee_id == user.id:
            return task
    if user.role == UserRole.ADMIN.value and tasks:
        return tasks[0]
    return None


async def _load_instance_with_tasks(db: AsyncSession, instance_id: UUID) -> ApprovalInstance:
    stmt = (
        select(ApprovalInstance)
        .where(ApprovalInstance.id == instance_id)
        .options(selectinload(ApprovalInstance.tasks))
    )
    instance = (await db.execute(stmt)).scalar_one()
    instance.tasks.sort(key=lambda item: item.stage_order)
    return instance


async def _advance_next_task(db: AsyncSession, instance: ApprovalInstance) -> bool:
    next_stage_order: int | None = None
    for task in instance.tasks:
        if task.status == TASK_STATUS_WAITING:
            if next_stage_order is None or task.stage_order < next_stage_order:
                next_stage_order = task.stage_order
    if next_stage_order is None:
        return False
    for task in instance.tasks:
        if task.stage_order == next_stage_order and task.status == TASK_STATUS_WAITING:
            task.status = TASK_STATUS_PENDING
            await _send_assignment_notification(db, instance, task)
    instance.current_stage = next_stage_order
    await db.flush()
    return True


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

    now = _utcnow()
    task.action = action
    task.status = (
        "approved" if action == "approve" else "rejected" if action == "reject" else "returned"
    )
    task.comment = comment
    task.acted_at = now

    instance = await _load_instance_with_tasks(db, instance_id)

    if action == "approve":
        for sibling in instance.tasks:
            if (
                sibling.id != task.id
                and sibling.stage_order == task.stage_order
                and sibling.status == TASK_STATUS_PENDING
            ):
                sibling.status = TASK_STATUS_SKIPPED
                sibling.comment = "auto-skipped: peer approved"
        advanced = await _advance_next_task(db, instance)
        if advanced:
            instance.status = INSTANCE_STATUS_PENDING
            instance.completed_at = None
        else:
            instance.status = "approved"
            instance.current_stage = instance.total_stages
            instance.completed_at = now
    elif action == "reject":
        instance.status = "rejected"
        instance.completed_at = now
        for other_task in instance.tasks:
            if other_task.id != task.id and other_task.status in (
                TASK_STATUS_WAITING,
                TASK_STATUS_PENDING,
            ):
                other_task.status = TASK_STATUS_SKIPPED
    else:
        instance.status = "returned"
        instance.completed_at = now
        for other_task in instance.tasks:
            if other_task.id != task.id and other_task.status in (
                TASK_STATUS_WAITING,
                TASK_STATUS_PENDING,
            ):
                other_task.status = TASK_STATUS_SKIPPED

    await db.flush()
    if instance.status in {"approved", "rejected", "returned"}:
        try:
            _ = await create_notification(
                db,
                user_id=instance.submitter_id,
                category=NotificationCategory.APPROVAL,
                title=lambda submitter: t(
                    "notification.approval.approved"
                    if instance.status == "approved"
                    else "notification.approval.rejected"
                    if instance.status == "rejected"
                    else "notification.approval.returned",
                    submitter.preferred_locale
                    if submitter and submitter.preferred_locale
                    else "zh-CN",
                    title=instance.title,
                ),
                body=comment,
                link_url=f"/purchase-requisitions/{instance.biz_id}",
                biz_type=instance.biz_type,
                biz_id=instance.biz_id,
                meta={
                    "approval_instance_id": str(instance.id),
                    "action": action,
                    "result": instance.status,
                    "biz_number": instance.biz_number,
                    "amount": str(instance.amount) if instance.amount is not None else None,
                    "current_stage": instance.current_stage,
                    "total_stages": instance.total_stages,
                },
            )
        except Exception:
            logger.warning("failed to create approval decision notification", exc_info=True)
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
    instance = (await db.execute(stmt)).scalars().first()
    if instance is not None:
        instance.tasks.sort(key=lambda task: task.stage_order)
    return instance


async def count_pending_for_user(db: AsyncSession, user_id: UUID) -> int:
    stmt = select(func.count(ApprovalTask.id)).where(
        ApprovalTask.assignee_id == user_id,
        ApprovalTask.status == TASK_STATUS_PENDING,
    )
    return int((await db.execute(stmt)).scalar_one())
