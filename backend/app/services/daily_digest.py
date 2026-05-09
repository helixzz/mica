"""Daily digest service: compiles a summary email for admin/procurement roles.

Includes pending approvals count, expiring contracts, and price anomalies.
Designed to be triggered by a cron job or manual admin endpoint.
"""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Contract,
    PRStatus,
    PurchaseRequisition,
    SKUPriceAnomaly,
    User,
    UserRole,
)
from app.services import contracts as contract_svc
from app.services.email_service import send_email
from app.services.system_params import system_params

logger = logging.getLogger("mica.daily_digest")


async def send_daily_digest(db: AsyncSession) -> dict:
    """Compile and send daily digest email to admin and procurement managers.

    Returns a summary dict with counts and per-recipient send status.
    Email failures are logged and swallowed — this is fire-and-forget.
    """
    today = datetime.now(UTC).date()

    pending_approvals = await _count_pending_approvals(db)

    expire_days = await system_params.get_int_or(db, "contract.expiry_reminder_days", 30)
    expiring_contracts = await contract_svc.expiring_contracts(db, within_days=expire_days)
    expiring_count = len(expiring_contracts)

    anomaly_days = await system_params.get_int_or(db, "sku.anomaly_lookback_days", 7)
    anomaly_since = today - timedelta(days=anomaly_days)
    sku_anomalies = await _count_recent_anomalies(db, since=anomaly_since)

    expiry_rows_html = _build_expiry_rows(expiring_contracts)
    anomaly_detail_html = await _build_anomaly_detail(db, since=anomaly_since)

    body = _build_email_body(
        pending_approvals=pending_approvals,
        expiring_count=expiring_count,
        expiry_rows_html=expiry_rows_html,
        sku_anomalies=sku_anomalies,
        anomaly_detail_html=anomaly_detail_html,
        today=today,
    )

    subject = f"Mica Daily Digest — {today.isoformat()}"

    recipients = await _get_digest_recipients(db)
    sent_count = 0
    failed_recipients: list[str] = []
    for user in recipients:
        if not user.email:
            continue
        try:
            ok = await send_email(db, user.email, subject, body)
            if ok:
                sent_count += 1
            else:
                failed_recipients.append(user.email)
        except Exception:
            logger.warning("Daily digest send failed for %s", user.email, exc_info=True)
            failed_recipients.append(user.email)

        # Also send via Feishu if enabled
        try:
            await _send_feishu_digest(
                db, user, pending_approvals, expiring_count, sku_anomalies
            )
        except Exception:
            logger.debug("Feishu digest skipped for %s", user.email)

    summary = {
        "pending_approvals": pending_approvals,
        "expiring_contracts": expiring_count,
        "sku_anomalies": sku_anomalies,
        "recipients_total": len(recipients),
        "sent_successfully": sent_count,
        "failed_recipients": failed_recipients,
    }

    logger.info("Daily digest sent: %s", summary)
    return summary


async def _count_pending_approvals(db: AsyncSession) -> int:
    result = await db.execute(
        select(func.count(PurchaseRequisition.id)).where(
            PurchaseRequisition.status == PRStatus.SUBMITTED.value
        )
    )
    return int(result.scalar_one() or 0)


async def _count_recent_anomalies(db: AsyncSession, since: date | None = None) -> int:
    stmt = select(func.count(SKUPriceAnomaly.id)).where(SKUPriceAnomaly.status == "new")
    if since is not None:
        since_dt = datetime.combine(since, datetime.min.time(), tzinfo=UTC)
        stmt = stmt.where(SKUPriceAnomaly.created_at >= since_dt)
    result = await db.execute(stmt)
    return int(result.scalar_one() or 0)


async def _get_digest_recipients(db: AsyncSession) -> list[User]:
    result = await db.execute(
        select(User)
        .where(
            User.role.in_([UserRole.ADMIN.value, UserRole.PROCUREMENT_MGR.value]),
            User.is_active.is_(True),
        )
        .order_by(User.username)
    )
    return list(result.scalars().all())


def _build_expiry_rows(contracts: list[Contract]) -> str:
    if not contracts:
        return "<p><em>No contracts expiring in the configured window.</em></p>"

    rows = ""
    for c in contracts:
        expiry_str = c.expiry_date.isoformat() if c.expiry_date else "N/A"
        amount = f"¥{float(c.total_amount):,.2f}" if c.total_amount else "—"
        rows += (
            f"<tr>"
            f"<td>{c.contract_number}</td>"
            f"<td>{c.title}</td>"
            f"<td>{expiry_str}</td>"
            f"<td>{amount}</td>"
            f"</tr>"
        )
    return (
        f'<table border="1" cellpadding="6" cellspacing="0" '
        f'style="border-collapse:collapse;width:100%">'
        f"<thead><tr>"
        f"<th>Contract #</th><th>Title</th><th>Expiry</th><th>Amount</th>"
        f"</tr></thead><tbody>{rows}</tbody></table>"
    )


async def _build_anomaly_detail(db: AsyncSession, since: date | None = None) -> str:
    from app.models import Item

    stmt = (
        select(SKUPriceAnomaly, Item)
        .join(Item, Item.id == SKUPriceAnomaly.item_id)
        .where(SKUPriceAnomaly.status == "new")
        .order_by(SKUPriceAnomaly.created_at.desc())
        .limit(20)
    )
    if since is not None:
        since_dt = datetime.combine(since, datetime.min.time(), tzinfo=UTC)
        stmt = stmt.where(SKUPriceAnomaly.created_at >= since_dt)

    rows = (await db.execute(stmt)).all()
    if not rows:
        return "<p><em>No recent price anomalies found.</em></p>"

    html = ""
    for anomaly, item in rows:
        observed = f"¥{float(anomaly.observed_price):,.2f}" if anomaly.observed_price else "—"
        baseline = (
            f"¥{float(anomaly.baseline_avg_price):,.2f}" if anomaly.baseline_avg_price else "—"
        )
        deviation = (
            f"{float(anomaly.deviation_pct):+.2f}%" if anomaly.deviation_pct is not None else "—"
        )
        html += (
            f"<tr>"
            f"<td>{item.name}</td>"
            f"<td>{observed}</td>"
            f"<td>{baseline}</td>"
            f"<td>{deviation}</td>"
            f"<td>{anomaly.severity}</td>"
            f"</tr>"
        )
    return (
        f'<table border="1" cellpadding="6" cellspacing="0" '
        f'style="border-collapse:collapse;width:100%">'
        f"<thead><tr>"
        f"<th>Item</th><th>Observed</th><th>Baseline</th><th>Deviation</th><th>Severity</th>"
        f"</tr></thead><tbody>{html}</tbody></table>"
    )


def _build_email_body(
    *,
    pending_approvals: int,
    expiring_count: int,
    expiry_rows_html: str,
    sku_anomalies: int,
    anomaly_detail_html: str,
    today: date,
) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"></head>
<body style="font-family:Inter,sans-serif;color:#333;max-width:700px;margin:0 auto">
<h2 style="color:#8B5E3C">🦦 Mica Daily Digest</h2>
<p style="color:#666">{today.isoformat()}</p>

<h3 style="color:#8B5E3C">📋 Pending Approvals: {pending_approvals}</h3>
<p>{pending_approvals} purchase request(s) are awaiting approval.</p>

<h3 style="color:#8B5E3C">📄 Expiring Contracts: {expiring_count}</h3>
{expiry_rows_html}

<h3 style="color:#8B5E3C">⚠️ Price Anomalies (last 7 days): {sku_anomalies}</h3>
{anomaly_detail_html}

<hr style="border:1px solid #eee;margin:24px 0">
<p style="font-size:12px;color:#999">
This digest was automatically generated by Mica (觅采).
<a href="http://localhost:8900/admin" style="color:#8B5E3C">Manage notification settings</a>.
</p>
</body>
</html>"""


async def _send_feishu_digest(
    db: AsyncSession,
    user: User,
    pending_approvals: int,
    expiring_count: int,
    sku_anomalies: int,
) -> None:
    from app.services.feishu.client import FeishuClient
    from app.services.system_params import system_params

    enabled = await system_params.get(db, "auth.feishu.enabled", False)
    if not enabled:
        return
    if not user.feishu_union_id and not user.feishu_open_id:
        return

    body = (
        f"**待审批**: {pending_approvals} 个采购申请\n"
        f"**即将到期合同**: {expiring_count} 份\n"
        f"**价格异常**: {sku_anomalies} 条\n\n"
        f"[查看仪表盘](https://mica.jqdomain.com/dashboard) ｜ "
        f"[查看审批](https://mica.jqdomain.com/approvals)"
    )

    card = {
        "header": {"title": {"tag": "plain_text", "content": "Mica Daily Digest"}, "template": "blue"},
        "elements": [{"tag": "markdown", "content": body}],
    }

    client = FeishuClient(db)
    try:
        if user.feishu_union_id:
            await client.send_card("union_id", user.feishu_union_id, card)
        elif user.feishu_open_id:
            await client.send_card("open_id", user.feishu_open_id, card)
    except Exception:
        pass
