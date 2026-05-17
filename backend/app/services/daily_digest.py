"""Daily digest service: compiles a summary email for admin/procurement roles.

Includes pending approvals count, expiring contracts, and price anomalies.
Designed to be triggered by a cron job or manual admin endpoint.
"""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.i18n import t
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
    Email body is built per-recipient to honour each user's preferred locale.
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

    today_po_count, today_po_amount = await _count_today_pos(db)
    upcoming_pay_count, upcoming_pay_amount = await _count_upcoming_payments(db, today)
    overdue_count = await _count_overdue_approvals(db)

    # Pre-fetch anomaly rows once for reuse across recipients
    anomaly_rows = await _fetch_anomaly_rows(db, since=anomaly_since)

    recipients = await _get_digest_recipients(db)
    sent_count = 0
    failed_recipients: list[str] = []
    for user in recipients:
        if not user.email:
            continue
        locale = user.preferred_locale or "zh-CN"
        subject = t("digest.email_title", locale, date=today.isoformat())

        expiry_rows_html = _build_expiry_rows(expiring_contracts, locale)
        anomaly_detail_html = _build_anomaly_detail_html(anomaly_rows, locale)

        body = _build_email_body(
            pending_approvals=pending_approvals,
            expiring_count=expiring_count,
            expiry_rows_html=expiry_rows_html,
            sku_anomalies=sku_anomalies,
            anomaly_detail_html=anomaly_detail_html,
            today_po_count=today_po_count,
            today_po_amount=today_po_amount,
            upcoming_pay_count=upcoming_pay_count,
            upcoming_pay_amount=upcoming_pay_amount,
            overdue_count=overdue_count,
            today=today,
            locale=locale,
        )

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
                db,
                user,
                pending_approvals,
                expiring_count,
                sku_anomalies,
                today_po_count,
                today_po_amount,
                upcoming_pay_count,
                upcoming_pay_amount,
                overdue_count,
            )
        except Exception:
            logger.warning("Feishu digest skipped for user %s", user.email, exc_info=True)

    summary = {
        "pending_approvals": pending_approvals,
        "expiring_contracts": expiring_count,
        "sku_anomalies": sku_anomalies,
        "today_po_count": today_po_count,
        "today_po_amount": today_po_amount,
        "upcoming_payments": upcoming_pay_count,
        "upcoming_pay_amount": upcoming_pay_amount,
        "overdue_approvals": overdue_count,
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


async def _count_today_pos(db: AsyncSession) -> tuple[int, float]:
    from app.models import PurchaseOrder

    today = datetime.now(UTC).date()
    start = datetime.combine(today, datetime.min.time(), tzinfo=UTC)
    end = datetime.combine(today, datetime.max.time(), tzinfo=UTC)

    result = await db.execute(
        select(
            func.count(PurchaseOrder.id),
            func.coalesce(func.sum(PurchaseOrder.total_amount), 0),
        ).where(
            PurchaseOrder.created_at >= start,
            PurchaseOrder.created_at <= end,
        )
    )
    row = result.one()
    return int(row[0] or 0), float(row[1] or 0)


async def _count_upcoming_payments(db: AsyncSession, today: date) -> tuple[int, float]:
    from app.models import PaymentSchedule

    end_date = today + timedelta(days=7)
    result = await db.execute(
        select(
            func.count(PaymentSchedule.id),
            func.coalesce(func.sum(PaymentSchedule.planned_amount), 0),
        ).where(
            PaymentSchedule.planned_date >= today,
            PaymentSchedule.planned_date <= end_date,
            PaymentSchedule.status != "paid",
        )
    )
    row = result.one()
    return int(row[0] or 0), float(row[1] or 0)


async def _count_overdue_approvals(db: AsyncSession) -> int:
    sla_hours = await system_params.get_int_or(db, "approval.sla_hours", 24)
    cutoff = datetime.now(UTC) - timedelta(hours=sla_hours)

    from app.models import ApprovalInstance

    result = await db.execute(
        select(func.count(ApprovalInstance.id)).where(
            ApprovalInstance.status == "pending",
            ApprovalInstance.submitted_at < cutoff,
        )
    )
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


def _build_expiry_rows(contracts: list[Contract], locale: str) -> str:
    if not contracts:
        return f"<p><em>{t('digest.no_expiring_contracts', locale)}</em></p>"

    th_num = t("digest.table_header_contract_number", locale)
    th_title = t("digest.table_header_title", locale)
    th_expiry = t("digest.table_header_expiry", locale)
    th_amount = t("digest.table_header_amount", locale)

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
        f"<th>{th_num}</th><th>{th_title}</th><th>{th_expiry}</th><th>{th_amount}</th>"
        f"</tr></thead><tbody>{rows}</tbody></table>"
    )


async def _fetch_anomaly_rows(db: AsyncSession, since: date | None = None) -> list:
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

    return list((await db.execute(stmt)).all())


def _build_anomaly_detail_html(rows: list, locale: str) -> str:
    if not rows:
        return f"<p><em>{t('digest.no_recent_anomalies', locale)}</em></p>"

    th_item = t("digest.table_header_item", locale)
    th_observed = t("digest.table_header_observed", locale)
    th_baseline = t("digest.table_header_baseline", locale)
    th_deviation = t("digest.table_header_deviation", locale)
    th_severity = t("digest.table_header_severity", locale)

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
        f"<th>{th_item}</th><th>{th_observed}</th><th>{th_baseline}</th>"
        f"<th>{th_deviation}</th><th>{th_severity}</th>"
        f"</tr></thead><tbody>{html}</tbody></table>"
    )


def _build_email_body(
    *,
    pending_approvals: int,
    expiring_count: int,
    expiry_rows_html: str,
    sku_anomalies: int,
    anomaly_detail_html: str,
    today_po_count: int,
    today_po_amount: float,
    upcoming_pay_count: int,
    upcoming_pay_amount: float,
    overdue_count: int,
    today: date,
    locale: str,
) -> str:
    base_url = get_settings().app_base_url.rstrip("/")
    email_title = t("digest.email_title", locale)
    po_amount_fmt = f"¥{today_po_amount:,.2f}"
    pay_amount_fmt = f"¥{upcoming_pay_amount:,.2f}"

    today_overview_label = t("digest.email_title_today_overview", locale)
    today_po_text = t("digest.today_po_text", locale, count=today_po_count, amount=po_amount_fmt)
    upcoming_pay_text = t(
        "digest.upcoming_payments_text",
        locale,
        count=upcoming_pay_count,
        amount=pay_amount_fmt,
    )

    pending_label = t("digest.email_title_pending_approvals", locale, count=pending_approvals)
    pending_text = t("digest.pending_approvals_text", locale, count=pending_approvals)
    view_approvals = t("digest.view_pending_approvals_link", locale)

    overdue_label = t("digest.email_title_overdue_approvals", locale, count=overdue_count)
    overdue_text = t("digest.overdue_approvals_text", locale, count=overdue_count)

    expiring_label = t("digest.email_title_expiring_contracts", locale, count=expiring_count)
    view_contracts = t("digest.view_all_contracts_link", locale)
    anomalies_label = t("digest.price_anomalies_header", locale, count=sku_anomalies)
    footer = t("digest.email_footer", locale)
    manage_settings = t("digest.manage_settings_link", locale)

    today_overview_rows = ""
    if today_po_count > 0:
        today_overview_rows += f"<li>{today_po_text}</li>"
    if upcoming_pay_count > 0:
        today_overview_rows += f"<li>{upcoming_pay_text}</li>"

    overdue_html = ""
    if overdue_count > 0:
        overdue_html = f'<h3 style="color:#8B5E3C">{overdue_label}</h3>\n<p>{overdue_text}</p>\n'

    today_overview_html = ""
    if today_overview_rows:
        today_overview_html = (
            f'<h3 style="color:#8B5E3C">{today_overview_label}</h3>\n'
            f"<ul>{today_overview_rows}</ul>\n"
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"></head>
<body style="font-family:Inter,sans-serif;color:#333;max-width:700px;margin:0 auto">
<h2 style="color:#8B5E3C">{email_title}</h2>
<p style="color:#666">{today.isoformat()}</p>

{today_overview_html}
<h3 style="color:#8B5E3C">{pending_label}</h3>
<p>{pending_text}
<a href="{base_url}/approvals" style="color:#8B5E3C">{view_approvals} →</a></p>

{overdue_html}
<h3 style="color:#8B5E3C">{expiring_label}</h3>
{expiry_rows_html}
<p style="margin-top:8px"><a href="{base_url}/contracts" style="color:#8B5E3C">{view_contracts} →</a></p>

<h3 style="color:#8B5E3C">{anomalies_label}</h3>
{anomaly_detail_html}

<hr style="border:1px solid #eee;margin:24px 0">
<p style="font-size:12px;color:#999">
{footer}
<a href="{base_url}/admin" style="color:#8B5E3C">{manage_settings}</a>.
</p>
</body>
</html>"""


async def _send_feishu_digest(
    db: AsyncSession,
    user: User,
    pending_approvals: int,
    expiring_count: int,
    sku_anomalies: int,
    today_po_count: int,
    today_po_amount: float,
    upcoming_pay_count: int,
    upcoming_pay_amount: float,
    overdue_count: int,
) -> None:
    from app.services.feishu.client import FeishuClient
    from app.services.system_params import system_params

    enabled = await system_params.get(db, "auth.feishu.enabled", False)
    if not enabled:
        return
    if not user.feishu_union_id and not user.feishu_open_id:
        return

    locale = user.preferred_locale or "zh-CN"
    base_url = get_settings().app_base_url.rstrip("/")

    po_amount_fmt = f"¥{today_po_amount:,.2f}"
    pay_amount_fmt = f"¥{upcoming_pay_amount:,.2f}"

    today_po_line = t("digest.feishu.today_pos", locale, count=today_po_count, amount=po_amount_fmt)
    pay_line = t(
        "digest.feishu.upcoming_payments", locale, count=upcoming_pay_count, amount=pay_amount_fmt
    )

    lines = []
    if today_po_count > 0 or upcoming_pay_count > 0:
        lines.append(t("digest.feishu.today_overview", locale))
        if today_po_count > 0:
            lines.append(f"• {today_po_line}")
        if upcoming_pay_count > 0:
            lines.append(f"• {pay_line}")
        lines.append("")

    lines.append(t("digest.feishu.pending_approvals", locale, count=pending_approvals))
    if overdue_count > 0:
        lines.append(t("digest.feishu.overdue_approvals", locale, count=overdue_count))
    lines.append(t("digest.feishu.expiring_contracts", locale, count=expiring_count))
    lines.append(t("digest.feishu.price_anomalies", locale, count=sku_anomalies))
    lines.append("")
    lines.append(
        f"[{t('digest.feishu.view_dashboard', locale)}]({base_url}/dashboard) ｜ "
        f"[{t('digest.feishu.view_approvals', locale)}]({base_url}/approvals)"
    )

    body = "\n".join(lines)

    card = {
        "header": {
            "title": {"tag": "plain_text", "content": t("digest.feishu.title", locale)},
            "template": "blue",
        },
        "elements": [{"tag": "markdown", "content": body}],
    }

    client = FeishuClient(db)
    try:
        if user.feishu_union_id:
            await client.send_card("union_id", user.feishu_union_id, card)
        elif user.feishu_open_id:
            await client.send_card("open_id", user.feishu_open_id, card)
    except Exception:
        logger.warning("Failed to send Feishu digest to user %s", user.id, exc_info=True)
