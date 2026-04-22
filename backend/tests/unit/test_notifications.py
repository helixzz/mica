from typing import cast
from uuid import uuid4

from sqlalchemy import select

from app.models import NotificationCategory, NotificationSubscription, User
from app.services import notifications as svc


async def _alice(db):
    return (await db.execute(select(User).where(User.username == "alice"))).scalar_one()


async def test_create_notification_writes_row(seeded_db_session):
    alice = await _alice(seeded_db_session)

    notification = await svc.create_notification(
        seeded_db_session,
        user_id=alice.id,
        category=NotificationCategory.APPROVAL,
        title="审批任务",
        body="请审批 PR-2026-0001",
        link_url="/approvals",
    )

    assert notification is not None
    assert notification.user_id == alice.id
    assert notification.title == "审批任务"
    assert notification.read_at is None


async def test_create_notification_returns_none_when_subscription_disabled(seeded_db_session):
    alice = await _alice(seeded_db_session)
    seeded_db_session.add(
        NotificationSubscription(
            user_id=alice.id,
            category=NotificationCategory.APPROVAL,
            in_app_enabled=False,
            email_enabled=False,
        )
    )
    await seeded_db_session.flush()

    notification = await svc.create_notification(
        seeded_db_session,
        user_id=alice.id,
        category=NotificationCategory.APPROVAL,
        title="muted",
    )

    assert notification is None


async def test_create_notification_resolves_callable_title(seeded_db_session):
    alice = await _alice(seeded_db_session)

    notification = await svc.create_notification(
        seeded_db_session,
        user_id=alice.id,
        category=NotificationCategory.SYSTEM,
        title=lambda user: f"Hi {user.username if user else 'guest'}",
    )

    assert notification is not None
    assert notification.title == "Hi alice"


async def test_recent_notification_exists_false_without_biz_identifiers(seeded_db_session):
    alice = await _alice(seeded_db_session)

    result = await svc._recent_notification_exists(
        seeded_db_session,
        user_id=alice.id,
        category=NotificationCategory.APPROVAL,
        biz_type=None,
        biz_id=None,
    )

    assert result is False


async def test_create_notification_if_fresh_dedupes_recent_notifications(seeded_db_session):
    alice = await _alice(seeded_db_session)
    biz_id = uuid4()

    first = await svc._create_notification_if_fresh(
        seeded_db_session,
        user_id=alice.id,
        category=NotificationCategory.APPROVAL,
        title="请审批",
        biz_type="pr",
        biz_id=biz_id,
    )
    second = await svc._create_notification_if_fresh(
        seeded_db_session,
        user_id=alice.id,
        category=NotificationCategory.APPROVAL,
        title="重复通知",
        biz_type="pr",
        biz_id=biz_id,
    )

    assert first is not None
    assert second is None


async def test_list_notifications_and_count_unread_reflect_created_rows(seeded_db_session):
    alice = await _alice(seeded_db_session)
    await svc.create_notification(
        seeded_db_session,
        user_id=alice.id,
        category=NotificationCategory.APPROVAL,
        title="a",
    )
    await svc.create_notification(
        seeded_db_session,
        user_id=alice.id,
        category=NotificationCategory.CONTRACT_EXPIRING,
        title="b",
    )

    rows = await svc.list_notifications(seeded_db_session, user_id=alice.id, limit=10)
    count = await svc.count_unread(seeded_db_session, user_id=alice.id)

    assert len(rows) >= 2
    assert count["total"] >= 2


async def test_mark_read_updates_selected_notifications(seeded_db_session):
    alice = await _alice(seeded_db_session)
    n1 = await svc.create_notification(
        seeded_db_session,
        user_id=alice.id,
        category=NotificationCategory.APPROVAL,
        title="mark-a",
    )
    n2 = await svc.create_notification(
        seeded_db_session,
        user_id=alice.id,
        category=NotificationCategory.APPROVAL,
        title="mark-b",
    )
    assert n1 is not None
    assert n2 is not None

    updated = await svc.mark_read(
        seeded_db_session,
        user_id=alice.id,
        notification_ids=[n1.id, n2.id],
    )

    assert updated == 2


async def test_get_subscriptions_returns_defaults_for_missing_rows(seeded_db_session):
    alice = await _alice(seeded_db_session)

    rows = await svc.get_subscriptions(seeded_db_session, user_id=alice.id)

    assert len(rows) == len(NotificationCategory)
    approval = next(row for row in rows if row.category == NotificationCategory.APPROVAL)
    assert approval.in_app_enabled is True
    assert approval.email_enabled is False


async def test_upsert_subscription_persists_and_updates_preference(seeded_db_session):
    alice = await _alice(seeded_db_session)

    created = await svc.upsert_subscription(
        seeded_db_session,
        user_id=alice.id,
        category=NotificationCategory.PAYMENT_PENDING,
        in_app_enabled=False,
        email_enabled=True,
    )
    updated = await svc.upsert_subscription(
        seeded_db_session,
        user_id=alice.id,
        category=NotificationCategory.PAYMENT_PENDING,
        in_app_enabled=True,
        email_enabled=False,
    )
    stored = (
        await seeded_db_session.execute(
            select(NotificationSubscription).where(
                NotificationSubscription.user_id == alice.id,
                NotificationSubscription.category == NotificationCategory.PAYMENT_PENDING,
            )
        )
    ).scalar_one()

    assert updated.id == created.id
    assert stored.in_app_enabled is True
    assert stored.email_enabled is False
