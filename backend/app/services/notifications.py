from __future__ import annotations

import logging
from collections.abc import Callable, Mapping
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import new_uuid
from app.i18n import t
from app.models import (
    Item,
    JSONValue,
    Notification,
    NotificationCategory,
    NotificationChannel,
    NotificationSubscription,
    POContractLink,
    PurchaseOrder,
    SKUPriceAnomaly,
    User,
    UserRole,
)
from app.services import contracts as contract_svc

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
    )


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
) -> Notification | None:
    """Respects user's subscription. Returns created notification or None if muted."""
    subscription = await _get_subscription(session, user_id=user_id, category=category)
    if subscription is not None and not subscription.in_app_enabled:
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
    )
    session.add(notification)
    await session.flush()

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


async def _maybe_send_feishu_card(
    session: AsyncSession,
    notification: Notification,
) -> None:
    """Send a Feishu card notification if feishu is enabled and category matches."""
    feishu_categories = {
        NotificationCategory.FEISHU_PR_SUBMITTED,
        NotificationCategory.FEISHU_APPROVAL_DECIDED,
        NotificationCategory.FEISHU_PO_CREATED,
        NotificationCategory.FEISHU_PAYMENT_PENDING,
        NotificationCategory.FEISHU_CONTRACT_EXPIRING,
    }
    if notification.category not in feishu_categories:
        return

    try:
        from app.services.feishu.client import FeishuClient
        from app.services.system_params import system_params

        enabled = await system_params.get(session, "auth.feishu.enabled", False)
        if not enabled:
            return

        user = await session.get(User, notification.user_id)
        if not user or not user.email:
            return

        client = FeishuClient(session)
        try:
            card = _build_feishu_card(notification, user)
            if card is None:
                return

            # Prefer feishu IDs: union_id (tenant-wide) > open_id > email
            if user.feishu_union_id:
                await client.send_card("union_id", user.feishu_union_id, card)
            elif user.feishu_open_id:
                await client.send_card("open_id", user.feishu_open_id, card)
            else:
                await client.send_card("email", user.email, card)
            logger.info(
                "feishu: card sent to user=%s category=%s via=%s",
                user.email,
                notification.category.value,
                "open_id" if user.feishu_open_id else "email",
            )
        finally:
            await client.close()
    except Exception:
        logger.warning(
            "feishu: card send failed for notification %s",
            notification.id,
            exc_info=True,
        )


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
    except Exception:
        logger.warning(
            "email: send failed for notification %s",
            notification.id,
            exc_info=True,
        )


def _build_feishu_card(
    notification: Notification,
    user: User,
) -> dict | None:
    """Build a Feishu card dict from notification data."""
    from app.services.feishu import messages as feishu_messages

    meta = notification.meta or {}

    if notification.category == NotificationCategory.FEISHU_PR_SUBMITTED:
        return feishu_messages.build_pr_submitted_card(
            pr_title=notification.title,
            applicant=user.display_name,
            department=meta.get("department", ""),
            amount=meta.get("amount", "—"),
            line_count=int(meta.get("line_count", 0)),
            pr_url=meta.get("pr_url", ""),
        )

    if notification.category == NotificationCategory.FEISHU_APPROVAL_DECIDED:
        return feishu_messages.build_approval_decided_card(
            pr_title=notification.title,
            decider=meta.get("decider", ""),
            result=meta.get("result", "approved"),
            comment=meta.get("comment", ""),
            pr_url=meta.get("pr_url", ""),
        )

    if notification.category == NotificationCategory.FEISHU_PO_CREATED:
        return feishu_messages.build_po_created_card(
            po_number=meta.get("po_number", ""),
            supplier=meta.get("supplier", ""),
            amount=meta.get("amount", "—"),
            pr_title=meta.get("pr_title", ""),
            po_url=meta.get("po_url", ""),
        )

    if notification.category == NotificationCategory.FEISHU_PAYMENT_PENDING:
        return feishu_messages.build_payment_pending_card(
            payment_id=meta.get("payment_id", ""),
            po_number=meta.get("po_number", ""),
            supplier=meta.get("supplier", ""),
            amount=meta.get("amount", "—"),
            payment_url=meta.get("payment_url", ""),
        )

    if notification.category == NotificationCategory.FEISHU_CONTRACT_EXPIRING:
        return feishu_messages.build_contract_expiring_card(
            contract_number=meta.get("contract_number", ""),
            supplier=meta.get("supplier", ""),
            expiry_date=meta.get("expiry_date", ""),
            days_remaining=int(meta.get("days_remaining", 0)),
            total_amount=meta.get("total_amount", "—"),
            used_amount=meta.get("used_amount", "—"),
            contract_url=meta.get("contract_url", ""),
        )

    return None


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
) -> NotificationSubscription:
    """Upsert per (user_id, category)."""
    row = await _get_subscription(session, user_id=user_id, category=category)
    if row is None:
        row = NotificationSubscription(
            user_id=user_id,
            category=category,
            in_app_enabled=in_app_enabled,
            email_enabled=email_enabled,
        )
        session.add(row)
    else:
        row.in_app_enabled = in_app_enabled
        row.email_enabled = email_enabled
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
