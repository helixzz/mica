"""SLA escalation: when an approval instance exceeds the configured SLA hours
without a decision, notify procurement managers and admins to take action.
"""

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
    UserRole,
)
from app.services.notifications import bulk_notify_role, create_notification
from app.services.system_params import notification_enabled, system_params

logger = logging.getLogger(__name__)

TASK_STATUS_PENDING = "pending"
INSTANCE_STATUS_PENDING = "pending"


def _locale(user: User | None) -> str:
    return user.preferred_locale if user and user.preferred_locale else "zh-CN"


async def check_overdue_approvals(db: AsyncSession) -> dict[str, object]:
    """Find approval instances that exceeded SLA and send escalation notifications.

    Reads approval.sla_hours and approval.sla_alert_enabled from system_params.
    Returns a summary dict with counts.
    """
    enabled = await system_params.get(db, "approval.sla_alert_enabled", True)
    if not enabled:
        return {"scanned": 0, "escalated": 0, "notifications": 0, "sla_disabled": True}

    sla_hours = await system_params.get_int_or(db, "approval.sla_hours", 24)
    cutoff = datetime.now(UTC) - timedelta(hours=sla_hours)

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

    escalated_instances = 0
    total_notifications = 0

    for instance in instances:
        pending_tasks = [task for task in instance.tasks if task.status == TASK_STATUS_PENDING]
        if not pending_tasks:
            continue

        stage_names = sorted({task.stage_name for task in pending_tasks})

        if not await notification_enabled(db, "sla_escalation"):
            escalated_instances += 1
            continue

        try:
            notification = await create_notification(
                db,
                user_id=instance.submitter_id,
                category=NotificationCategory.SYSTEM,
                title=lambda user, _instance=instance, _sla_hours=sla_hours: t(
                    "notification.sla.escalated_submitter",
                    _locale(user),
                    title=_instance.title,
                    hours=_sla_hours,
                ),
                body=lambda user, _instance=instance, _sla_hours=sla_hours, _stage_names=stage_names: (
                    t(
                        "notification.sla.escalated_submitter_body",
                        _locale(user),
                        title=_instance.title,
                        hours=_sla_hours,
                        stage=",".join(_stage_names),
                    )
                ),
                link_url="/approvals",
                biz_type="approval_escalation_submitter",
                biz_id=instance.id,
                meta={
                    "approval_instance_id": str(instance.id),
                    "biz_number": instance.biz_number,
                    "title": instance.title,
                    "sla_hours": sla_hours,
                    "pending_stages": stage_names,
                },
            )
            if notification is not None:
                total_notifications += 1
        except Exception:
            logger.warning(
                "failed to create submitter escalation notification for instance %s",
                instance.id,
                exc_info=True,
            )

        try:
            manager_notifications = await bulk_notify_role(
                db,
                role=UserRole.PROCUREMENT_MGR,
                company_id=instance.company_id,
                category=NotificationCategory.SYSTEM,
                title=lambda user, _instance=instance, _sla_hours=sla_hours: t(
                    "notification.sla.escalated_manager",
                    _locale(user),
                    title=_instance.title,
                    hours=_sla_hours,
                ),
                body=lambda user, _instance=instance, _sla_hours=sla_hours, _stage_names=stage_names: (
                    t(
                        "notification.sla.escalated_manager_body",
                        _locale(user),
                        title=_instance.title,
                        hours=_sla_hours,
                        biz_number=_instance.biz_number or "",
                        stage=",".join(_stage_names),
                    )
                ),
                link_url="/approvals",
                biz_type="approval_escalation",
                biz_id=instance.id,
                meta={
                    "approval_instance_id": str(instance.id),
                    "biz_number": instance.biz_number,
                    "title": instance.title,
                    "sla_hours": sla_hours,
                    "pending_stages": stage_names,
                },
            )
            total_notifications += len(manager_notifications)
        except Exception:
            logger.warning(
                "failed to create manager escalation notification for instance %s",
                instance.id,
                exc_info=True,
            )

        try:
            admin_notifications = await bulk_notify_role(
                db,
                role=UserRole.ADMIN,
                company_id=instance.company_id,
                category=NotificationCategory.SYSTEM,
                title=lambda user, _instance=instance, _sla_hours=sla_hours: t(
                    "notification.sla.escalated_admin",
                    _locale(user),
                    title=_instance.title,
                    hours=_sla_hours,
                ),
                body=lambda user, _instance=instance, _sla_hours=sla_hours, _stage_names=stage_names: (
                    t(
                        "notification.sla.escalated_admin_body",
                        _locale(user),
                        title=_instance.title,
                        hours=_sla_hours,
                        biz_number=_instance.biz_number or "",
                        stage=",".join(_stage_names),
                    )
                ),
                link_url="/approvals",
                biz_type="approval_escalation",
                biz_id=instance.id,
                meta={
                    "approval_instance_id": str(instance.id),
                    "biz_number": instance.biz_number,
                    "title": instance.title,
                    "sla_hours": sla_hours,
                    "pending_stages": stage_names,
                },
            )
            total_notifications += len(admin_notifications)
        except Exception:
            logger.warning(
                "failed to create admin escalation notification for instance %s",
                instance.id,
                exc_info=True,
            )

        escalated_instances += 1

    return {
        "scanned": len(instances),
        "escalated": escalated_instances,
        "notifications": total_notifications,
        "sla_hours": sla_hours,
        "cutoff": cutoff.isoformat(),
    }
