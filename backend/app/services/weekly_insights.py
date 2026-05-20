from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.money import fmt_amount
from app.models import (
    ApprovalTask,
    PurchaseOrder,
    PurchaseRequisition,
    Shipment,
    SKUPriceAnomaly,
    User,
    UserRole,
)
from app.services.email_service import send_email
from app.services.system_params import notification_enabled

logger = logging.getLogger("mica.weekly_insights")


async def send_weekly_insights_digest(db: AsyncSession) -> dict:
    if not await notification_enabled(db, "weekly_insights_digest"):
        logger.info("weekly_insights_digest: disabled via system_params")
        return {"sent": 0, "failed": 0, "skipped": True}

    today = datetime.now(UTC).date()
    week_start = today - timedelta(days=7)

    metrics = await _gather_weekly_metrics(db, week_start, today)

    recipients = (
        (
            await db.execute(
                select(User).where(
                    User.is_active.is_(True),
                    User.role.in_(
                        [
                            UserRole.ADMIN.value,
                            UserRole.PROCUREMENT_MGR.value,
                            UserRole.IT_BUYER.value,
                            UserRole.DEPT_MANAGER.value,
                            UserRole.FINANCE_AUDITOR.value,
                        ]
                    ),
                )
            )
        )
        .scalars()
        .all()
    )

    sent = 0
    failed = 0
    for user in recipients:
        if not user.email:
            continue
        try:
            body = _build_digest_body(metrics, user)
            subject = f"Mica 周报洞察 · {week_start.isoformat()} ~ {today.isoformat()}"
            ok = await send_email(db, user.email, subject, body)
            if ok:
                sent += 1
            else:
                failed += 1
        except Exception:
            logger.warning("Weekly digest send failed for %s", user.email, exc_info=True)
            failed += 1

    return {"sent": sent, "failed": failed}


async def _gather_weekly_metrics(db: AsyncSession, week_start, today) -> dict:
    new_prs = (
        await db.execute(
            select(func.count(PurchaseRequisition.id)).where(
                PurchaseRequisition.created_at
                >= datetime.combine(week_start, datetime.min.time()).replace(tzinfo=UTC)
            )
        )
    ).scalar_one() or 0

    new_pos = (
        await db.execute(
            select(func.count(PurchaseOrder.id)).where(
                PurchaseOrder.created_at
                >= datetime.combine(week_start, datetime.min.time()).replace(tzinfo=UTC)
            )
        )
    ).scalar_one() or 0

    po_amount = (
        await db.execute(
            select(func.coalesce(func.sum(PurchaseOrder.total_amount), 0)).where(
                PurchaseOrder.created_at
                >= datetime.combine(week_start, datetime.min.time()).replace(tzinfo=UTC)
            )
        )
    ).scalar_one() or Decimal("0")

    shipments_received = (
        await db.execute(
            select(func.count(Shipment.id)).where(
                Shipment.actual_date >= week_start,
                Shipment.actual_date.isnot(None),
            )
        )
    ).scalar_one() or 0

    pending_approvals = (
        await db.execute(
            select(func.count(ApprovalTask.id)).where(ApprovalTask.status == "pending")
        )
    ).scalar_one() or 0

    new_anomalies = (
        await db.execute(
            select(func.count(SKUPriceAnomaly.id)).where(
                SKUPriceAnomaly.created_at
                >= datetime.combine(week_start, datetime.min.time()).replace(tzinfo=UTC)
            )
        )
    ).scalar_one() or 0

    return {
        "week_start": week_start.isoformat(),
        "week_end": today.isoformat(),
        "new_prs": new_prs,
        "new_pos": new_pos,
        "po_amount": po_amount,
        "shipments_received": shipments_received,
        "pending_approvals": pending_approvals,
        "new_anomalies": new_anomalies,
    }


def _build_digest_body(metrics: dict, user: User) -> str:
    locale = getattr(user, "preferred_locale", "zh-CN") or "zh-CN"
    is_zh = locale.startswith("zh")
    base_url = get_settings().app_base_url.rstrip("/")

    po_amount_str = fmt_amount(metrics["po_amount"])

    if is_zh:
        lines = [
            f"<h2>Mica 周报洞察 · {metrics['week_start']} ~ {metrics['week_end']}</h2>",
            "<table border='1' cellpadding='8' cellspacing='0' style='border-collapse:collapse;'>",
            "<tr><th>指标</th><th>本周数据</th></tr>",
            f"<tr><td>新增采购申请</td><td><strong>{metrics['new_prs']}</strong> 单</td></tr>",
            f"<tr><td>新增采购订单</td><td><strong>{metrics['new_pos']}</strong> 单 · {po_amount_str}</td></tr>",
            f"<tr><td>到货批次</td><td><strong>{metrics['shipments_received']}</strong> 批</td></tr>",
            f"<tr><td>待审批任务</td><td><strong>{metrics['pending_approvals']}</strong> 项</td></tr>",
            f"<tr><td>价格异常</td><td><strong>{metrics['new_anomalies']}</strong> 项</td></tr>",
            "</table>",
            "<br/>",
            "<p>登录 <a href='" + base_url + "/insights'>数据洞察</a> 查看详情。</p>",
        ]
    else:
        lines = [
            f"<h2>Mica Weekly Insights · {metrics['week_start']} ~ {metrics['week_end']}</h2>",
            "<table border='1' cellpadding='8' cellspacing='0' style='border-collapse:collapse;'>",
            "<tr><th>Metric</th><th>This Week</th></tr>",
            f"<tr><td>New PRs</td><td><strong>{metrics['new_prs']}</strong></td></tr>",
            f"<tr><td>New POs</td><td><strong>{metrics['new_pos']}</strong> · {po_amount_str}</td></tr>",
            f"<tr><td>Shipments Received</td><td><strong>{metrics['shipments_received']}</strong></td></tr>",
            f"<tr><td>Pending Approvals</td><td><strong>{metrics['pending_approvals']}</strong></td></tr>",
            f"<tr><td>Price Anomalies</td><td><strong>{metrics['new_anomalies']}</strong></td></tr>",
            "</table>",
            "<br/>",
            "<p>Visit <a href='" + base_url + "/insights'>Insights</a> for details.</p>",
        ]

    return "\n".join(lines)
