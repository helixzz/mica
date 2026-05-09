from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.i18n import t
from app.models import (
    ApprovalInstance,
    NotificationCategory,
    User,
)
from app.services.notifications import create_notification
from app.services.system_params import system_params

logger = logging.getLogger(__name__)

TASK_STATUS_PENDING = "pending"
INSTANCE_STATUS_PENDING = "pending"


def _locale(user: User | None) -> str:
    return user.preferred_locale if user and user.preferred_locale else "zh-CN"


async def send_reminders(db: AsyncSession) -> dict[str, int | str | bool]:
    enabled = await system_params.get(db, "approval.reminder_enabled", True)
    if not enabled:
        return {"scanned": 0, "reminded": 0, "notifications": 0, "reminder_disabled": True}

    hours = await system_params.get_int_or(db, "approval.reminder_hours", 4)
    cutoff = datetime.now(UTC) - timedelta(hours=hours)

    stmt = (
        select(ApprovalInstance)
        .where(
            ApprovalInstance.status == INSTANCE_STATUS_PENDING,
            ApprovalInstance.submitted_at < cutoff,
        )
        .options(selectinload(ApprovalInstance.tasks))
        .order_by(ApprovalInstance.submitted_at.asc())
    )
    instances = list((await db.execute(stmt)).scalars().all())

    reminded_instances = 0
    total_notifications = 0

    for instance in instances:
        pending_tasks = [task for task in instance.tasks if task.status == TASK_STATUS_PENDING]
        if not pending_tasks:
            continue

        for task in pending_tasks:
            try:
                notification = await create_notification(
                    db,
                    user_id=task.assignee_id,
                    category=NotificationCategory.SYSTEM,
                    title=lambda user, _instance=instance, _hours=hours: t(
                        "notification.reminder.pending",
                        _locale(user),
                        title=_instance.title,
                        hours=_hours,
                    ),
                    body=lambda user, _instance=instance, _stage=task.stage_name, _hours=hours: t(
                        "notification.reminder.pending_body",
                        _locale(user),
                        biz_number=_instance.biz_number or "",
                        title=_instance.title,
                        stage=_stage,
                        hours=_hours,
                    ),
                    link_url="/approvals",
                    biz_type="approval_reminder",
                    biz_id=instance.id,
                    meta={
                        "approval_instance_id": str(instance.id),
                        "biz_number": instance.biz_number,
                        "title": instance.title,
                        "reminder_hours": hours,
                        "pending_stage": task.stage_name,
                        "task_id": str(task.id),
                    },
                )
                if notification is not None:
                    total_notifications += 1
            except Exception:
                logger.warning(
                    "failed to create reminder notification for task %s (instance %s)",
                    task.id,
                    instance.id,
                    exc_info=True,
                )

        reminded_instances += 1

    return {
        "scanned": len(instances),
        "reminded": reminded_instances,
        "notifications": total_notifications,
        "reminder_hours": hours,
        "cutoff": cutoff.isoformat(),
    }
