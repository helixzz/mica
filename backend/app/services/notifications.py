from __future__ import annotations

import logging
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import new_uuid
from app.i18n import t
from app.models import (
    AuditLog,
    Item,
    JSONValue,
    Notification,
    NotificationCategory,
    NotificationChannel,
    NotificationDelivery,
    NotificationDeliveryStatus,
    NotificationSubscription,
    POContractLink,
    PurchaseOrder,
    SKUPriceAnomaly,
    User,
    UserRole,
)
from app.services import contracts as contract_svc
from app.services.system_params import system_params

logger = logging.getLogger(__name__)

logger = logging.getLogger("mica.notifications")

NotificationText = str | Callable[[User | None], str]


def _locale_for_user(user: User | None) -> str:
    if user and user.preferred_locale:
        return user.preferred_locale
    return "zh-CN"


def _resolve_text(value: NotificationText | None, user: User | None) -> str | None:
    if value is None:
        return None
    return value(user) if callable(value) else value


async def _get_user(session: AsyncSession, user_id: UUID) -> User | None:
    return await session.get(User, user_id)


async def _get_subscription(
    session: AsyncSession,
    *,
    user_id: UUID,
    category: NotificationCategory,
) -> NotificationSubscription | None:
    return (
        await session.execute(
            select(NotificationSubscription).where(
                NotificationSubscription.user_id == user_id,
                NotificationSubscription.category == category,
            )
        )
    ).scalar_one_or_none()


async def _recent_notification_exists(
    session: AsyncSession,
    *,
    user_id: UUID,
    category: NotificationCategory,
    biz_type: str | None,
    biz_id: UUID | None,
    within_hours: int = 24,
) -> bool:
    if biz_type is None or biz_id is None:
        return False
    since = datetime.now(UTC) - timedelta(hours=within_hours)
    return (
        await session.execute(
            select(Notification.id).where(
                Notification.user_id == user_id,
                Notification.category == category,
                Notification.biz_type == biz_type,
                Notification.biz_id == biz_id,
                Notification.created_at >= since,
            )
        )
    ).scalar_one_or_none() is not None


async def _create_notification_if_fresh(
    session: AsyncSession,
    *,
    user_id: UUID,
    category: NotificationCategory,
    title: NotificationText,
    body: NotificationText | None = None,
    link_url: str | None = None,
    biz_type: str | None = None,
    biz_id: UUID | None = None,
    meta: Mapping[str, JSONValue] | None = None,
    dedupe_key: str | None = None,
) -> Notification | None:
    if await _recent_notification_exists(
        session,
        user_id=user_id,
        category=category,
        biz_type=biz_type,
        biz_id=biz_id,
    ):
        return None
    return await create_notification(
        session,
        user_id=user_id,
        category=category,
        title=title,
        body=body,
        link_url=link_url,
        biz_type=biz_type,
        biz_id=biz_id,
        meta=meta,
        dedupe_key=dedupe_key,
    )


async def _dedupe_announced(
    session: AsyncSession,
    *,
    user_id: UUID,
    dedupe_key: str,
) -> bool:
    window_hours = await system_params.get_int_or(session, "notifications.event_dedupe_hours", 24)
    since = datetime.now(UTC) - timedelta(hours=window_hours)
    return (
        await session.execute(
            select(Notification.id)
            .where(
                Notification.user_id == user_id,
                Notification.dedupe_key == dedupe_key,
                Notification.created_at >= since,
            )
            .limit(1)
        )
    ).scalar_one_or_none() is not None


def announcement_key(event: str, biz_type: str, biz_id: object, fingerprint: str) -> str:
    """Stable identity for one announcement: same object, same change, same event."""
    return f"{event}:{biz_type}:{biz_id}:{fingerprint}"


def fingerprint_of(*parts: object) -> str:
    """Short hash of the values that make a change distinct.

    Two saves with no real difference collapse into one announcement; a changed
    amount or status is a new one. Values are joined in caller order, so callers
    should keep the order stable.
    """
    import hashlib

    raw = "|".join(str(part) for part in parts)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]


async def create_notification(
    session: AsyncSession,
    *,
    user_id: UUID,
    category: NotificationCategory,
    title: NotificationText,
    body: NotificationText | None = None,
    link_url: str | None = None,
    biz_type: str | None = None,
    biz_id: UUID | None = None,
    meta: Mapping[str, JSONValue] | None = None,
    dedupe_key: str | None = None,
) -> Notification | None:
    """Respects user's subscription. Returns created notification or None if muted.

    When ``dedupe_key`` is supplied the same announcement for the same user is
    never created twice inside the configured window — the fix for a PR that was
    saved twice announcing itself twice, and for two processes sharing one Feishu
    app pushing the same card.
    """
    subscription = await _get_subscription(session, user_id=user_id, category=category)
    if subscription is not None and not subscription.in_app_enabled:
        return None

    if dedupe_key is not None and await _dedupe_announced(
        session, user_id=user_id, dedupe_key=dedupe_key
    ):
        return None

    user: User | None = None
    if callable(title) or callable(body):
        user = await _get_user(session, user_id)

    notification = Notification(
        user_id=user_id,
        category=category,
        title=_resolve_text(title, user) or "",
        body=_resolve_text(body, user),
        link_url=link_url,
        biz_type=biz_type,
        biz_id=biz_id,
        meta=dict(meta or {}),
        sent_via=[NotificationChannel.IN_APP.value],
        dedupe_key=dedupe_key,
    )
    session.add(notification)
    await session.flush()

    try:
        session.add(
            AuditLog(
                actor_id=None,
                actor_name=None,
                event_type="notification.created",
                resource_type="notification",
                resource_id=str(notification.id),
                metadata_json={
                    "category": notification.category.value,
                    "user_id": str(user_id),
                    "title": notification.title,
                },
                comment="notification.created",
            )
        )
    except Exception:
        pass

    await _maybe_send_feishu_card(session, notification)
    await _maybe_send_email(session, notification)

    try:
        from app.api.v1.websocket import notify_user

        unread = await count_unread(session, user_id=user_id)
        await notify_user(
            str(user_id),
            {
                "type": "new_notification",
                "notification_id": str(notification.id),
                "category": notification.category.value,
                "title": notification.title,
                "unread_count": unread["total"],
            },
        )
    except Exception:
        pass

    return notification


def status_label(status: str, locale: str) -> str:
    """Human status text; unknown values fall back to the raw enum rather than a key."""
    key = f"notification.status.{status}"
    text = t(key, locale)
    return status if text == key else text


def user_locale(user: User | None) -> str:
    return user.preferred_locale if user and user.preferred_locale else "zh-CN"


async def emit_event_notification(
    session: AsyncSession,
    *,
    user_id: UUID,
    event: str,
    title: NotificationText,
    link_url: str,
    biz_type: str,
    biz_id: UUID,
    fields: Sequence[tuple[str, str]] | None = None,
    changes: Sequence[tuple[str, str]] | None = None,
    summary: str = "",
    fingerprint_parts: Sequence[object] = (),
    status: str = "info",
    category: NotificationCategory = NotificationCategory.SYSTEM,
    meta: Mapping[str, JSONValue] | None = None,
) -> Notification | None:
    """Create one event announcement with a structured card payload.

    ``fields`` and ``changes`` are already-translated label/value pairs; the card
    renderer only lays them out. ``fingerprint_parts`` identify the change itself,
    so re-saving an object with the same values does not announce it twice.
    """
    payload_meta: dict[str, JSONValue] = dict(meta or {})
    if fields:
        payload_meta["fields"] = [[label, value] for label, value in fields]
    if changes:
        payload_meta["changes"] = [[label, value] for label, value in changes]
    if summary:
        payload_meta["summary"] = summary
    payload_meta["status"] = status
    payload_meta["event"] = event

    dedupe_key = announcement_key(event, biz_type, biz_id, fingerprint_of(*fingerprint_parts))
    return await create_notification(
        session,
        user_id=user_id,
        category=category,
        title=title,
        body=summary or None,
        link_url=link_url,
        biz_type=biz_type,
        biz_id=biz_id,
        meta=payload_meta,
        dedupe_key=dedupe_key,
    )


#: Admin switch governing each category on the Feishu side. A category that is
#: missing here is never pushed to Feishu, which is what keeps "notify me" honest.
_FEISHU_SWITCH_BY_CATEGORY: dict[NotificationCategory, str] = {
    NotificationCategory.FEISHU_PR_SUBMITTED: "auth.feishu.notify_on_pr",
    NotificationCategory.APPROVAL: "auth.feishu.notify_on_approval",
    NotificationCategory.FEISHU_APPROVAL_DECIDED: "auth.feishu.notify_on_approval",
    NotificationCategory.FEISHU_PO_CREATED: "auth.feishu.notify_on_po",
    NotificationCategory.PO_CREATED: "auth.feishu.notify_on_po",
    NotificationCategory.FEISHU_PAYMENT_PENDING: "auth.feishu.notify_on_payment",
    NotificationCategory.PAYMENT_PENDING: "auth.feishu.notify_on_payment",
    NotificationCategory.FEISHU_CONTRACT_EXPIRING: "auth.feishu.notify_on_contract_expiry",
    NotificationCategory.CONTRACT_EXPIRING: "auth.feishu.notify_on_contract_expiry",
    NotificationCategory.SYSTEM: "auth.feishu.notify_on_system",
    NotificationCategory.PRICE_ANOMALY: "auth.feishu.notify_on_system",
    NotificationCategory.RECEIPT_RECORDED: "auth.feishu.notify_on_system",
}


async def _maybe_send_feishu_card(
    session: AsyncSession,
    notification: Notification,
) -> None:
    """Push one card, honouring the admin switch, the user's own preference and the ledger."""
    switch = _FEISHU_SWITCH_BY_CATEGORY.get(notification.category)
    if switch is None:
        return

    try:
        if not await system_params.get(session, "auth.feishu.enabled", False):
            return
        if not await system_params.get(session, switch, True):
            return

        user = await session.get(User, notification.user_id)
        if not user or not user.email:
            return

        subscription = await _get_subscription(
            session, user_id=user.id, category=notification.category
        )
        if subscription is not None and not subscription.feishu_enabled:
            return

        # Two Mica accounts can share one Feishu identity (the same person holding
        # an admin and a second role). Without this check the same event reaches
        # one chat twice, which is exactly what "the cards arrive in pairs" was.
        if (
            notification.dedupe_key
            and user.feishu_union_id
            and await _delivered_to_shared_account(
                session, union_id=user.feishu_union_id, dedupe_key=notification.dedupe_key
            )
        ):
            logger.info(
                "feishu: skipped duplicate for shared account user=%s key=%s",
                user.email,
                notification.dedupe_key,
            )
            return

        base_url = await _app_base_url(session)
        card = _build_feishu_card(notification, user, base_url=base_url)
        if card is None:
            return

        await _deliver_feishu(session, notification, user, card, base_url=base_url)
    except Exception:
        logger.warning(
            "feishu: card send failed for notification %s",
            notification.id,
            exc_info=True,
        )


async def _app_base_url(session: AsyncSession) -> str:
    value = await system_params.get(session, "app.base_url", "")
    if not value:
        from app.config import get_settings

        value = get_settings().app_base_url
    return str(value).rstrip("/")


async def _delivered_to_shared_account(
    session: AsyncSession,
    *,
    union_id: str,
    dedupe_key: str,
) -> bool:
    """True when this Feishu identity already received the same event."""
    window_hours = await system_params.get_int_or(session, "notifications.event_dedupe_hours", 24)
    since = datetime.now(UTC) - timedelta(hours=window_hours)
    stmt = (
        select(NotificationDelivery.id)
        .join(Notification, Notification.id == NotificationDelivery.notification_id)
        .join(User, User.id == Notification.user_id)
        .where(
            User.feishu_union_id == union_id,
            Notification.dedupe_key == dedupe_key,
            NotificationDelivery.channel == NotificationChannel.FEISHU.value,
            NotificationDelivery.status == NotificationDeliveryStatus.SENT.value,
            NotificationDelivery.created_at >= since,
        )
        .limit(1)
    )
    return (await session.execute(stmt)).scalar_one_or_none() is not None


async def _send_feishu_card(session: AsyncSession, user: User, card: dict) -> dict:
    from app.services.feishu.client import FeishuClient

    client = FeishuClient(session)
    try:
        # Prefer feishu IDs: union_id (tenant-wide) > open_id > email
        if user.feishu_union_id:
            return await client.send_card("union_id", user.feishu_union_id, card)
        if user.feishu_open_id:
            return await client.send_card("open_id", user.feishu_open_id, card)
        return await client.send_card("email", user.email, card)
    finally:
        await client.close()


async def _deliver_feishu(
    session: AsyncSession,
    notification: Notification,
    user: User,
    card: dict,
    *,
    base_url: str = "",
) -> None:
    delivery = NotificationDelivery(
        notification_id=notification.id,
        channel=NotificationChannel.FEISHU.value,
        status=NotificationDeliveryStatus.PENDING.value,
        attempts=0,
    )
    session.add(delivery)
    await session.flush()

    try:
        response = await _send_feishu_card(session, user, card)
        delivery.status = NotificationDeliveryStatus.SENT.value
        delivery.attempts = 1
        delivery.message_id = _message_id_of(response)
        delivery.sent_at = datetime.now(UTC)
        if NotificationChannel.FEISHU.value not in (notification.sent_via or []):
            notification.sent_via = [
                *(notification.sent_via or []),
                NotificationChannel.FEISHU.value,
            ]
        logger.info(
            "feishu: card sent user=%s category=%s message_id=%s",
            user.email,
            notification.category.value,
            delivery.message_id or "-",
        )
        _audit(
            session,
            "notification.feishu_sent",
            notification,
            {"message_id": delivery.message_id, "via": _receive_id_kind(user)},
        )
    except Exception as exc:
        delivery.status = NotificationDeliveryStatus.FAILED.value
        delivery.attempts = 1
        delivery.last_error = str(exc)[:500]
        delivery.next_retry_at = datetime.now(UTC) + timedelta(minutes=10)
        logger.warning(
            "feishu: delivery failed notification=%s user=%s error=%s",
            notification.id,
            user.email,
            exc,
        )
        _audit(session, "notification.feishu_failed", notification, {"error": str(exc)[:200]})


def _receive_id_kind(user: User) -> str:
    if user.feishu_union_id:
        return "union_id"
    if user.feishu_open_id:
        return "open_id"
    return "email"


def _message_id_of(response: dict | None) -> str | None:
    data = (response or {}).get("data")
    if isinstance(data, dict):
        message_id = data.get("message_id")
        if isinstance(message_id, str) and message_id:
            return message_id
    return None


def _audit(
    session: AsyncSession,
    event_type: str,
    notification: Notification,
    extra: dict | None = None,
) -> None:
    try:
        session.add(
            AuditLog(
                actor_id=None,
                actor_name=None,
                event_type=event_type,
                resource_type="notification",
                resource_id=str(notification.id),
                metadata_json={
                    "category": notification.category.value,
                    "user_id": str(notification.user_id),
                    **(extra or {}),
                },
                comment=event_type,
            )
        )
    except Exception:
        pass


async def retry_failed_feishu_deliveries(session: AsyncSession) -> dict[str, int]:
    """Re-send cards whose first attempt failed, up to the configured ceiling.

    The ledger is the only place that knows a card failed, so this job is what
    turns "we probably sent it" into a bounded, inspectable retry.
    """
    from sqlalchemy import or_

    max_attempts = await system_params.get_int_or(session, "notifications.delivery_max_attempts", 3)
    now = datetime.now(UTC)
    deliveries = list(
        (
            await session.execute(
                select(NotificationDelivery)
                .where(
                    NotificationDelivery.channel == NotificationChannel.FEISHU.value,
                    NotificationDelivery.status == NotificationDeliveryStatus.FAILED.value,
                    NotificationDelivery.attempts < max_attempts,
                    or_(
                        NotificationDelivery.next_retry_at.is_(None),
                        NotificationDelivery.next_retry_at <= now,
                    ),
                )
                .order_by(NotificationDelivery.created_at)
                .limit(50)
            )
        )
        .scalars()
        .all()
    )

    retried = 0
    sent = 0
    for delivery in deliveries:
        notification = await session.get(Notification, delivery.notification_id)
        if notification is None:
            delivery.status = NotificationDeliveryStatus.SKIPPED.value
            delivery.last_error = "notification missing"
            continue
        user = await session.get(User, notification.user_id)
        if user is None or not user.email:
            delivery.status = NotificationDeliveryStatus.SKIPPED.value
            delivery.last_error = "user missing"
            continue

        base_url = await _app_base_url(session)
        card = _build_feishu_card(notification, user, base_url=base_url)
        if card is None:
            delivery.status = NotificationDeliveryStatus.SKIPPED.value
            delivery.last_error = "no card template for category"
            continue

        retried += 1
        delivery.attempts += 1
        try:
            response = await _send_feishu_card(session, user, card)
            delivery.status = NotificationDeliveryStatus.SENT.value
            delivery.message_id = _message_id_of(response)
            delivery.sent_at = datetime.now(UTC)
            delivery.last_error = None
            sent += 1
            _audit(
                session,
                "notification.feishu_retried",
                notification,
                {"attempts": delivery.attempts},
            )
        except Exception as exc:
            delivery.last_error = str(exc)[:500]
            if delivery.attempts >= max_attempts:
                delivery.status = NotificationDeliveryStatus.FAILED.value
                delivery.next_retry_at = None
            else:
                delivery.next_retry_at = now + timedelta(minutes=10 * delivery.attempts)

    await session.commit()
    return {"scanned": len(deliveries), "retried": retried, "sent": sent}


async def _maybe_send_email(
    session: AsyncSession,
    notification: Notification,
) -> None:
    """Send an email notification as fallback when feishu is not available."""
    try:
        from app.services.email_service import send_email
        from app.services.system_params import system_params

        enabled = await system_params.get(session, "email.enabled", False)
        if not enabled:
            return

        user = await session.get(User, notification.user_id)
        if not user or not user.email:
            return

        if user.feishu_open_id or user.feishu_union_id:
            return

        subject = f"[Mica] {notification.category.value}: {notification.title}"
        body = f"<p>{notification.body or notification.title}</p>"
        if notification.link_url:
            body += f'<p><a href="{notification.link_url}">View in Mica</a></p>'

        await send_email(session, user.email, subject, body)
        try:
            session.add(
                AuditLog(
                    actor_id=None,
                    actor_name=None,
                    event_type="notification.email_sent",
                    resource_type="notification",
                    resource_id=str(notification.id),
                    metadata_json={
                        "category": notification.category.value,
                        "user_id": str(notification.user_id),
                        "email": user.email,
                    },
                    comment="notification.email_sent",
                )
            )
        except Exception:
            pass
    except Exception:
        logger.warning(
            "email: send failed for notification %s",
            notification.id,
            exc_info=True,
        )
        try:
            session.add(
                AuditLog(
                    actor_id=None,
                    actor_name=None,
                    event_type="notification.email_failed",
                    resource_type="notification",
                    resource_id=str(notification.id),
                    metadata_json={
                        "category": notification.category.value,
                        "user_id": str(notification.user_id),
                    },
                    comment="notification.email_failed",
                )
            )
        except Exception:
            pass


def _absolute_url(path: str | None, base_url: str) -> str:
    if not path:
        return ""
    if path.startswith("http://") or path.startswith("https://"):
        return path
    if path.startswith("/") and base_url:
        return base_url + path
    return path


def _amount_text(meta: Mapping[str, JSONValue]) -> str:
    from app.core.money import fmt_amount

    raw = meta.get("amount")
    if raw is None or raw == "":
        return "—"
    return fmt_amount(raw, str(meta.get("currency") or "CNY"))


def _float_or_none(value: JSONValue | None) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _int_or_none(value: JSONValue | None) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _meta_pairs(value: JSONValue | None) -> list[tuple[str, str]]:
    """Accept ``[[label, value], ...]`` from notification meta, ignoring noise."""
    if not isinstance(value, list):
        return []
    pairs: list[tuple[str, str]] = []
    for entry in value:
        if isinstance(entry, (list, tuple)) and len(entry) == 2:
            pairs.append((str(entry[0]), str(entry[1])))
    return pairs


def _build_feishu_card(
    notification: Notification,
    user: User,
    base_url: str = "",
) -> dict | None:
    """Render the notification as a card 2.0 payload for this user's locale."""
    from app.core.dates import fmt_date
    from app.services.feishu import messages as feishu_messages

    locale = user.preferred_locale or "zh-CN"
    meta = notification.meta or {}
    link = _absolute_url(notification.link_url, base_url)

    if notification.category == NotificationCategory.APPROVAL:
        kind = str(meta.get("kind") or "task")
        if kind == "task":
            task_id = str(meta.get("task_id") or "")
            if meta.get("pr_no") and task_id:
                department = str(
                    (meta.get("department_en") if locale.startswith("en") else None)
                    or meta.get("department")
                    or ""
                )
                return feishu_messages.build_pr_submitted_card(
                    pr_number=str(meta.get("pr_no")),
                    title=str(meta.get("pr_title") or notification.title),
                    applicant=str(meta.get("applicant") or ""),
                    department=department,
                    amount=_amount_text(meta),
                    line_count=_int_or_none(meta.get("line_count")) or 0,
                    item_count=_int_or_none(meta.get("item_count")) or 0,
                    waiting_hours=_float_or_none(meta.get("waiting_hours")),
                    sla_hours=_int_or_none(meta.get("sla_hours")),
                    task_url=_absolute_url(f"/approvals?task={task_id}", base_url),
                    pr_url=_absolute_url(f"/purchase-requisitions/{meta.get('biz_id')}", base_url),
                    locale=locale,
                )
        elif kind == "decision":
            return feishu_messages.build_approval_decided_card(
                pr_number=str(meta.get("pr_no") or ""),
                title=str(meta.get("pr_title") or notification.title),
                decider=str(meta.get("decider") or ""),
                result=str(meta.get("result") or "approved"),
                comment=str(meta.get("comment") or ""),
                amount=_amount_text(meta),
                pr_url=link,
                locale=locale,
            )

    if meta.get("kind") == "invoice":
        return feishu_messages.build_invoice_card(
            invoice_number=str(meta.get("invoice_number") or ""),
            vendor_number=str(meta.get("vendor_number") or ""),
            supplier=str(meta.get("supplier") or ""),
            total_amount=_amount_text(
                {
                    "amount": meta.get("total_amount"),
                    "currency": meta.get("currency"),
                }
            ),
            invoice_date=fmt_date(meta.get("invoice_date"), locale),
            tax_note=str(meta.get("tax_note") or ""),
            matched=bool(meta.get("matched")),
            po_hint=str(meta.get("po_hint") or ""),
            created_by=str(meta.get("created_by") or ""),
            invoice_url=_absolute_url(notification.link_url, base_url),
            locale=locale,
        )

    if meta.get("kind") == "po_receipt":
        return feishu_messages.build_po_receipt_card(
            po_number=str(meta.get("po_number") or ""),
            pr_title=str(meta.get("pr_title") or ""),
            received=str(meta.get("received") or "0"),
            ordered=str(meta.get("ordered") or "0"),
            percent=str(meta.get("percent") or "0%"),
            shipment_number=str(meta.get("shipment_number") or ""),
            carrier=str(meta.get("carrier") or ""),
            tracking=str(meta.get("tracking") or ""),
            fully_received=bool(meta.get("fully_received")),
            po_url=_absolute_url(notification.link_url, base_url),
            locale=locale,
        )

    if notification.category == NotificationCategory.CONTRACT_EXPIRING:
        if meta.get("contract_number") and meta.get("days_remaining") is not None:
            from app.core.money import fmt_amount

            used_amount = meta.get("used_amount")
            if not used_amount and meta.get("used_amount_value") is not None:
                used_amount = fmt_amount(
                    meta.get("used_amount_value"), str(meta.get("currency") or "CNY")
                )
            return feishu_messages.build_contract_expiring_card(
                contract_number=str(meta.get("contract_number")),
                supplier=str(meta.get("supplier") or ""),
                expiry_date=fmt_date(meta.get("expiry_date"), locale),
                days_remaining=_int_or_none(meta.get("days_remaining")) or 0,
                total_amount=_amount_text(meta),
                used_amount=str(used_amount or "—"),
                contract_url=link,
                locale=locale,
            )

    if notification.category == NotificationCategory.PRICE_ANOMALY:
        fields = [
            (
                t("feishu.card.label.observed", locale),
                _amount_text({"amount": meta.get("observed_price")}),
            ),
            (
                t("feishu.card.label.baseline", locale),
                _amount_text({"amount": meta.get("baseline_avg_price")}),
            ),
            (t("feishu.card.label.deviation", locale), f"{meta.get('deviation_pct', '—')}%"),
            (t("feishu.card.label.severity", locale), str(meta.get("severity") or "—")),
        ]
        return feishu_messages.build_event_card(
            title=notification.title,
            summary=notification.body or "",
            fields=fields,
            url=link,
            status="warning",
            locale=locale,
        )

    fields = _meta_pairs(meta.get("fields"))
    changes = _meta_pairs(meta.get("changes"))
    if fields or changes:
        return feishu_messages.build_event_card(
            title=notification.title,
            summary=str(meta.get("summary") or ""),
            fields=fields,
            changes=changes,
            url=link,
            status=str(meta.get("status") or "info"),
            locale=locale,
        )

    return feishu_messages.build_event_card(
        title=notification.title,
        summary=notification.body or "",
        url=link,
        status=str(meta.get("status") or "info"),
        locale=locale,
    )


async def bulk_notify_role(
    session: AsyncSession,
    *,
    role: UserRole,
    company_id: UUID | None = None,
    category: NotificationCategory,
    title: NotificationText,
    body: NotificationText | None = None,
    link_url: str | None = None,
    biz_type: str | None = None,
    biz_id: UUID | None = None,
    meta: Mapping[str, JSONValue] | None = None,
) -> list[Notification]:
    """Send same notification to all users with given role. Useful for approval-pending fanout."""
    stmt = select(User).where(User.role == role.value, User.is_active.is_(True))
    if company_id is not None:
        stmt = stmt.where(User.company_id == company_id)
    users = (await session.execute(stmt.order_by(User.username))).scalars().all()
    notifications: list[Notification] = []
    for user in users:
        if biz_type is not None and biz_id is not None:
            notification = await _create_notification_if_fresh(
                session,
                user_id=user.id,
                category=category,
                title=title,
                body=body,
                link_url=link_url,
                biz_type=biz_type,
                biz_id=biz_id,
                meta=meta,
            )
        else:
            notification = await create_notification(
                session,
                user_id=user.id,
                category=category,
                title=title,
                body=body,
                link_url=link_url,
                biz_type=biz_type,
                biz_id=biz_id,
                meta=meta,
            )
        if notification is not None:
            notifications.append(notification)
    return notifications


async def list_notifications(
    session: AsyncSession,
    *,
    user_id: UUID,
    unread_only: bool = False,
    category: NotificationCategory | None = None,
    limit: int = 20,
    before_created_at: datetime | None = None,
) -> list[Notification]:
    """Paginated listing for user. Cursor-based on created_at for scale."""
    stmt = select(Notification).where(Notification.user_id == user_id)
    if unread_only:
        stmt = stmt.where(Notification.read_at.is_(None))
    if category is not None:
        stmt = stmt.where(Notification.category == category)
    if before_created_at is not None:
        stmt = stmt.where(Notification.created_at < before_created_at)
    stmt = stmt.order_by(Notification.created_at.desc(), Notification.id.desc()).limit(limit)
    return list((await session.execute(stmt)).scalars().all())


async def count_unread(session: AsyncSession, *, user_id: UUID) -> dict[str, int | dict[str, int]]:
    """Returns {total: N, by_category: {approval: 3, ...}} for bell badge + filter UI."""
    rows = (
        await session.execute(
            select(Notification.category, func.count(Notification.id))
            .where(Notification.user_id == user_id, Notification.read_at.is_(None))
            .group_by(Notification.category)
        )
    ).all()
    by_category = {
        category.value if isinstance(category, NotificationCategory) else str(category): int(count)
        for category, count in rows
    }
    return {"total": sum(by_category.values()), "by_category": by_category}


async def mark_read(
    session: AsyncSession,
    *,
    user_id: UUID,
    notification_ids: list[UUID] | None = None,
    all: bool = False,
) -> int:
    """Mark specific notifications or all unread as read. Returns count updated.
    Authorization: only the owner can mark their own notifications.
    """
    if not all and not notification_ids:
        raise HTTPException(422, "notification.ids_or_all_required")

    filters = [
        Notification.user_id == user_id,
        Notification.read_at.is_(None),
    ]
    if not all:
        filters.append(Notification.id.in_(notification_ids or []))
    count_stmt = select(func.count(Notification.id)).where(*filters)
    updated = int((await session.execute(count_stmt)).scalar_one() or 0)
    stmt = update(Notification).where(*filters)
    await session.execute(
        stmt.values(read_at=datetime.now(UTC)).execution_options(synchronize_session=False)
    )
    await session.commit()
    return updated


async def get_subscriptions(
    session: AsyncSession, *, user_id: UUID
) -> list[NotificationSubscription]:
    """Returns all categories with user's current preference (defaults if row absent)."""
    rows = (
        (
            await session.execute(
                select(NotificationSubscription).where(NotificationSubscription.user_id == user_id)
            )
        )
        .scalars()
        .all()
    )
    by_category = {row.category: row for row in rows}
    results: list[NotificationSubscription] = []
    for category in NotificationCategory:
        existing = by_category.get(category)
        if existing is not None:
            results.append(existing)
            continue
        results.append(
            NotificationSubscription(
                id=new_uuid(),
                user_id=user_id,
                category=category,
                in_app_enabled=True,
                email_enabled=False,
                feishu_enabled=True,
            )
        )
    return results


async def upsert_subscription(
    session: AsyncSession,
    *,
    user_id: UUID,
    category: NotificationCategory,
    in_app_enabled: bool,
    email_enabled: bool,
    feishu_enabled: bool = True,
) -> NotificationSubscription:
    """Upsert per (user_id, category)."""
    row = await _get_subscription(session, user_id=user_id, category=category)
    if row is None:
        row = NotificationSubscription(
            user_id=user_id,
            category=category,
            in_app_enabled=in_app_enabled,
            email_enabled=email_enabled,
            feishu_enabled=feishu_enabled,
        )
        session.add(row)
    else:
        row.in_app_enabled = in_app_enabled
        row.email_enabled = email_enabled
        row.feishu_enabled = feishu_enabled
    await session.commit()
    await session.refresh(row)
    return row


async def notify_expiring_contracts(
    session: AsyncSession,
    within_days: int = 30,
) -> dict[str, int]:
    contracts = await contract_svc.expiring_contracts(session, within_days=within_days)
    created = 0
    scanned = len(contracts)
    for contract in contracts:
        linked_po_ids = [str(contract.po_id)]
        link_rows = (
            (
                await session.execute(
                    select(POContractLink.po_id).where(POContractLink.contract_id == contract.id)
                )
            )
            .scalars()
            .all()
        )
        for link_po_id in link_rows:
            linked_po_id = str(link_po_id)
            if linked_po_id not in linked_po_ids:
                linked_po_ids.append(linked_po_id)
        meta = {
            "contract_number": contract.contract_number,
            "expiry_date": contract.expiry_date.isoformat() if contract.expiry_date else None,
            "po_id": str(contract.po_id),
            "linked_po_ids": linked_po_ids,
        }
        purchase_order = await session.get(PurchaseOrder, contract.po_id)
        if purchase_order is not None and purchase_order.created_by_id:
            notification = await _create_notification_if_fresh(
                session,
                user_id=purchase_order.created_by_id,
                category=NotificationCategory.CONTRACT_EXPIRING,
                title=lambda user, contract=contract: t(
                    "notification.contract.expiring",
                    _locale_for_user(user),
                    name=contract.title,
                ),
                body=contract.notes,
                link_url=f"/contracts/{contract.id}",
                biz_type="contract",
                biz_id=contract.id,
                meta=meta,
            )
            if notification is not None:
                created += 1

        manager_notifications = await bulk_notify_role(
            session,
            role=UserRole.PROCUREMENT_MGR,
            company_id=purchase_order.company_id if purchase_order is not None else None,
            category=NotificationCategory.CONTRACT_EXPIRING,
            title=lambda user, contract=contract: t(
                "notification.contract.expiring",
                _locale_for_user(user),
                name=contract.title,
            ),
            body=contract.notes,
            link_url=f"/contracts/{contract.id}",
            biz_type="contract",
            biz_id=contract.id,
            meta=meta,
        )
        created += len(manager_notifications)

    await session.commit()
    return {"scanned": scanned, "created": created}


async def notify_new_price_anomalies(session: AsyncSession) -> dict[str, int]:
    rows = (
        await session.execute(
            select(SKUPriceAnomaly, Item)
            .join(Item, Item.id == SKUPriceAnomaly.item_id)
            .where(SKUPriceAnomaly.status == "new")
            .order_by(SKUPriceAnomaly.created_at.desc())
        )
    ).all()

    created = 0
    scanned = len(rows)
    for anomaly, item in rows:
        meta = {
            "severity": anomaly.severity,
            "observed_price": str(anomaly.observed_price),
            "baseline_avg_price": str(anomaly.baseline_avg_price),
            "deviation_pct": str(anomaly.deviation_pct),
            "item_id": str(item.id),
        }
        created += len(
            await bulk_notify_role(
                session,
                role=UserRole.PROCUREMENT_MGR,
                category=NotificationCategory.PRICE_ANOMALY,
                title=lambda recipient, item=item: t(
                    "notification.price.anomaly",
                    _locale_for_user(recipient),
                    item=item.name,
                ),
                body=item.specification,
                link_url="/sku/anomalies",
                biz_type="sku_price_anomaly",
                biz_id=anomaly.id,
                meta=meta,
            )
        )
        created += len(
            await bulk_notify_role(
                session,
                role=UserRole.IT_BUYER,
                category=NotificationCategory.PRICE_ANOMALY,
                title=lambda recipient, item=item: t(
                    "notification.price.anomaly",
                    _locale_for_user(recipient),
                    item=item.name,
                ),
                body=item.specification,
                link_url="/sku/anomalies",
                biz_type="sku_price_anomaly",
                biz_id=anomaly.id,
                meta=meta,
            )
        )

    await session.commit()
    return {"scanned": scanned, "created": created}
