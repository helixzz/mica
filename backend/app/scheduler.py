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
        from datetime import UTC, datetime

        from app.core.dates import fmt_date
        from app.core.money import fmt_amount
        from app.i18n import t
        from app.models import User, UserRole
        from app.services import contracts as contract_svc
        from app.services.notifications import emit_event_notification, user_locale
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
                    days_remaining = (
                        (c.expiry_date - datetime.now(UTC).date()).days if c.expiry_date else 0
                    )
                    for admin in admins:
                        try:
                            locale = user_locale(admin)
                            await emit_event_notification(
                                db,
                                user_id=admin.id,
                                event="contract_expiring",
                                title=t(
                                    "notification.contract.expiring",
                                    locale,
                                    name=c.contract_number,
                                ),
                                link_url=f"/contracts/{c.id}",
                                biz_type="contract",
                                biz_id=c.id,
                                fields=[
                                    (
                                        t("notification.label.contract", locale),
                                        c.contract_number,
                                    ),
                                    (
                                        t("notification.label.supplier", locale),
                                        c.supplier.name if c.supplier else "—",
                                    ),
                                    (
                                        t("notification.label.expires", locale),
                                        fmt_date(c.expiry_date, locale),
                                    ),
                                    (
                                        t("notification.label.days_remaining", locale),
                                        str(days_remaining),
                                    ),
                                    (
                                        t("notification.label.amount", locale),
                                        fmt_amount(c.total_amount, c.currency),
                                    ),
                                ],
                                summary=str(c.notes or ""),
                                fingerprint_parts=("expiring", c.expiry_date),
                                status="warning" if days_remaining <= 7 else "action",
                                meta={
                                    "contract_number": c.contract_number,
                                    "expiry_date": c.expiry_date.isoformat()
                                    if c.expiry_date
                                    else None,
                                    "days_remaining": days_remaining,
                                    "supplier": c.supplier.name if c.supplier else "",
                                    "amount": str(c.total_amount),
                                    "currency": c.currency,
                                },
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

    async def _run_price_anomaly_scan():
        from app.core.money import fmt_amount
        from app.i18n import t
        from app.models import Item, NotificationCategory, SKUPriceAnomaly, User, UserRole
        from app.services.notifications import emit_event_notification, user_locale
        from app.services.sku import scan_all_anomalies
        from app.services.system_params import notification_enabled

        async with session_factory() as db:
            try:
                from sqlalchemy import select

                result = await scan_all_anomalies(db)
                scanned = result["scanned"]
                anomalies_found = result["anomalies_found"]
                logger.info(
                    "price_anomaly_scan: scanned=%d anomalies=%d",
                    scanned,
                    anomalies_found,
                )

                if anomalies_found == 0:
                    return

                if not await notification_enabled(db, "sku_price_anomaly"):
                    logger.info("price_anomaly_scan: notifications disabled for sku_price_anomaly")
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

                new_anomalies = (
                    (
                        await db.execute(
                            select(SKUPriceAnomaly)
                            .where(SKUPriceAnomaly.status == "new")
                            .order_by(SKUPriceAnomaly.created_at.desc())
                            .limit(anomalies_found)
                        )
                    )
                    .scalars()
                    .all()
                )

                notified = 0
                for anomaly in new_anomalies:
                    item = await db.get(Item, anomaly.item_id)
                    item_name = item.name if item else str(anomaly.item_id)[:8]

                    for admin in admins:
                        try:
                            locale = user_locale(admin)
                            await emit_event_notification(
                                db,
                                user_id=admin.id,
                                event="price_anomaly",
                                title=t("notification.price.anomaly", locale, item=item_name),
                                link_url=f"/sku/items/{anomaly.item_id}",
                                biz_type="sku_price_anomaly",
                                biz_id=anomaly.id,
                                fields=[
                                    (t("notification.label.item", locale), item_name),
                                    (
                                        t("notification.label.observed_price", locale),
                                        fmt_amount(anomaly.observed_price),
                                    ),
                                    (
                                        t("notification.label.baseline_price", locale),
                                        fmt_amount(anomaly.baseline_avg_price),
                                    ),
                                    (
                                        t("notification.label.deviation", locale),
                                        f"{anomaly.deviation_pct}%",
                                    ),
                                    (
                                        t("notification.label.severity", locale),
                                        str(anomaly.severity),
                                    ),
                                ],
                                fingerprint_parts=("new", anomaly.observed_price),
                                status="warning",
                                category=NotificationCategory.PRICE_ANOMALY,
                                meta={
                                    "observed_price": str(anomaly.observed_price),
                                    "baseline_avg_price": str(anomaly.baseline_avg_price),
                                    "deviation_pct": str(anomaly.deviation_pct),
                                    "severity": anomaly.severity,
                                    "item_id": str(anomaly.item_id),
                                },
                            )
                            notified += 1
                        except Exception:
                            logger.warning(
                                "price_anomaly notification failed for admin %s",
                                admin.id,
                            )
                await db.commit()
                logger.info(
                    "price_anomaly_scan: %d anomalies, %d notifications sent",
                    anomalies_found,
                    notified,
                )
            except Exception:
                logger.exception("price_anomaly_scan failed")

    async def _run_delivery_retry():
        from app.services.notifications import retry_failed_feishu_deliveries

        async with session_factory() as db:
            try:
                result = await retry_failed_feishu_deliveries(db)
                if result.get("retried"):
                    logger.info("delivery_retry: %s", result)
            except Exception:
                logger.exception("delivery_retry failed")

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
        _run_delivery_retry,
        IntervalTrigger(minutes=15),
        id="notification_delivery_retry",
        name="Retry failed notification deliveries",
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

    scheduler.add_job(
        _run_price_anomaly_scan,
        CronTrigger(hour=8, minute=0),
        id="price_anomaly_scan",
        name="SKU price anomaly detection",
        misfire_grace_time=300,
    )

    async def _run_weekly_insights_digest():
        from app.services.weekly_insights import send_weekly_insights_digest

        async with session_factory() as db:
            try:
                result = await send_weekly_insights_digest(db)
                logger.info(
                    "weekly_insights_digest: sent=%d failed=%d",
                    result.get("sent", 0),
                    result.get("failed", 0),
                )
            except Exception:
                logger.exception("weekly_insights_digest failed")

    # APScheduler keeps jobs in memory and the scheduler container is recreated on
    # every deploy, so a cron slot that fell inside a restart never ran — silently, with
    # no error and no notification. Both jobs below are idempotent (the anomaly scan
    # skips price records it already flagged; the expiry check only notifies for
    # contracts still expiring), so running them once after startup closes that gap.
    from datetime import UTC, datetime, timedelta

    from apscheduler.triggers.date import DateTrigger

    catch_up_at = datetime.now(UTC) + timedelta(seconds=90)
    for job_fn, catchup_id in (
        (_run_price_anomaly_scan, "price_anomaly_scan_catchup"),
        (_run_contract_expiry_check, "contract_expiry_catchup"),
    ):
        scheduler.add_job(
            job_fn,
            DateTrigger(run_date=catch_up_at),
            id=catchup_id,
            name=f"{catchup_id} (once after startup)",
            misfire_grace_time=600,
        )

    scheduler.add_job(
        _run_weekly_insights_digest,
        CronTrigger(day_of_week="mon", hour=9, minute=0),
        id="weekly_insights_digest",
        name="Weekly insights digest (email + Feishu)",
        misfire_grace_time=600,
    )

    return scheduler
