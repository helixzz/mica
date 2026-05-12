"""Mica scheduler — runs periodic background jobs.

Jobs:
- daily_digest: every day at 09:00 Asia/Shanghai (email + Feishu digest)
- approval_reminders: every hour (nudge pending approvers)
- sla_escalation: every 30 minutes (escalate overdue approvals)
- contract_expiry: every day at 10:00 (notify about expiring contracts)
"""

from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

logger = logging.getLogger("mica.scheduler")


def build_scheduler(session_factory: async_sessionmaker[AsyncSession]) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")

    async def _run_daily_digest():
        from app.services.daily_digest import send_daily_digest

        async with session_factory() as db:
            try:
                result = await send_daily_digest(db)
                logger.info("daily_digest completed: %s", result)
            except Exception:
                logger.exception("daily_digest failed")

    async def _run_approval_reminders():
        from app.services.approval_reminder import send_reminders

        async with session_factory() as db:
            try:
                result = await send_reminders(db)
                logger.info(
                    "approval_reminders: scanned=%d reminded=%d",
                    result.get("scanned", 0),
                    result.get("reminded", 0),
                )
            except Exception:
                logger.exception("approval_reminders failed")

    async def _run_sla_escalation():
        from app.services.sla_escalation import check_overdue_approvals

        async with session_factory() as db:
            try:
                result = await check_overdue_approvals(db)
                await db.commit()
                logger.info("sla_escalation: escalated=%d", result.get("escalated", 0))
            except Exception:
                logger.exception("sla_escalation failed")

    async def _run_contract_expiry_check():
        from app.models import NotificationCategory, User, UserRole
        from app.services import contracts as contract_svc
        from app.services.notifications import create_notification
        from app.services.system_params import notification_enabled

        async with session_factory() as db:
            try:
                from sqlalchemy import select

                expiring = await contract_svc.expiring_contracts(db, within_days=30)
                if not expiring:
                    logger.info("contract_expiry_check: no expiring contracts")
                    return

                if not await notification_enabled(db, "contract_expiring"):
                    logger.info(
                        "contract_expiry_check: notification disabled, skipping %d contracts",
                        len(expiring),
                    )
                    return

                admins = (
                    (
                        await db.execute(
                            select(User).where(
                                User.role.in_(
                                    [UserRole.ADMIN.value, UserRole.PROCUREMENT_MGR.value]
                                ),
                                User.is_active.is_(True),
                            )
                        )
                    )
                    .scalars()
                    .all()
                )

                notified = 0
                for c in expiring:
                    for admin in admins:
                        try:
                            await create_notification(
                                db,
                                user_id=admin.id,
                                category=NotificationCategory.SYSTEM,
                                title=f"Contract {c.contract_number} expires on {c.expiry_date}",
                                body=(
                                    f"**Contract**: {c.contract_number}\n"
                                    f"**Title**: {c.title}\n"
                                    f"**Supplier**: {c.supplier.name if c.supplier else '—'}\n"
                                    f"**Expiry**: {c.expiry_date}\n"
                                    f"**Status**: {c.status}\n"
                                    f"Please review and renew if needed."
                                ),
                                link_url=f"/contracts/{c.id}",
                                biz_type="contract_expiry",
                                biz_id=c.id,
                            )
                            notified += 1
                        except Exception:
                            logger.warning(
                                "contract_expiry notification failed for admin %s", admin.id
                            )
                await db.commit()
                logger.info(
                    "contract_expiry_check: %d contracts expiring, %d notifications sent",
                    len(expiring),
                    notified,
                )
            except Exception:
                logger.exception("contract_expiry_check failed")

    scheduler.add_job(
        _run_daily_digest,
        CronTrigger(hour=9, minute=0),
        id="daily_digest",
        name="Daily digest (email + Feishu)",
        misfire_grace_time=300,
    )

    scheduler.add_job(
        _run_approval_reminders,
        IntervalTrigger(hours=1),
        id="approval_reminders",
        name="Approval reminders",
        misfire_grace_time=300,
    )

    scheduler.add_job(
        _run_sla_escalation,
        IntervalTrigger(minutes=30),
        id="sla_escalation",
        name="SLA escalation check",
        misfire_grace_time=300,
    )

    scheduler.add_job(
        _run_contract_expiry_check,
        CronTrigger(hour=10, minute=0),
        id="contract_expiry_check",
        name="Contract expiry notifications",
        misfire_grace_time=300,
    )

    return scheduler
