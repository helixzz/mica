from uuid import uuid4

import pytest
from sqlalchemy import select

from app.models import (
    Notification,
    NotificationCategory,
    NotificationSubscription,
    User,
)
from app.services import notifications as svc


async def _get_alice(seeded_db_session) -> User:
    return (await seeded_db_session.execute(select(User).where(User.username == "alice"))).scalar_one()


async def test_create_notification_writes_row(seeded_db_session):
    alice = await _get_alice(seeded_db_session)
    n = await svc.create_notification(
        seeded_db_session,
        user_id=alice.id,
        category=NotificationCategory.APPROVAL,
        title="审批任务",
        body="请审批 PR-2026-0001",
        link_url="/approvals",
    )
    assert n is not None
    assert n.user_id == alice.id
    assert n.title == "审批任务"
    assert n.body == "请审批 PR-2026-0001"
    assert n.category == NotificationCategory.APPROVAL
    assert n.read_at is None


async def test_create_notification_muted_when_subscription_disabled(seeded_db_session):
    alice = await _get_alice(seeded_db_session)
    sub = NotificationSubscription(
        user_id=alice.id,
        category=NotificationCategory.APPROVAL,
        in_app_enabled=False,
        email_enabled=False,
    )
    seeded_db_session.add(sub)
    await seeded_db_session.flush()

    n = await svc.create_notification(
        seeded_db_session,
        user_id=alice.id,
        category=NotificationCategory.APPROVAL,
        title="muted",
    )
    assert n is None


async def test_create_notification_delivered_when_subscription_enabled(seeded_db_session):
    alice = await _get_alice(seeded_db_session)
    sub = NotificationSubscription(
        user_id=alice.id,
        category=NotificationCategory.PO_CREATED,
        in_app_enabled=True,
        email_enabled=False,
    )
    seeded_db_session.add(sub)
    await seeded_db_session.flush()

    n = await svc.create_notification(
        seeded_db_session,
        user_id=alice.id,
        category=NotificationCategory.PO_CREATED,
        title="PO 已生成",
    )
    assert n is not None
    assert n.title == "PO 已生成"


async def test_create_notification_with_callable_title_resolves(seeded_db_session):
    alice = await _get_alice(seeded_db_session)
    n = await svc.create_notification(
        seeded_db_session,
        user_id=alice.id,
        category=NotificationCategory.SYSTEM,
        title=lambda user: f"Hi {user.username}",
    )
    assert n is not None
    assert n.title == "Hi alice"


async def test_recent_notification_exists_false_for_missing_biz(seeded_db_session):
    alice = await _get_alice(seeded_db_session)
    result = await svc._recent_notification_exists(
        seeded_db_session,
        user_id=alice.id,
        category=NotificationCategory.APPROVAL,
        biz_type=None,
        biz_id=None,
    )
    assert result is False


async def test_create_notification_if_fresh_dedupes_within_window(seeded_db_session):
    alice = await _get_alice(seeded_db_session)
    biz_id = uuid4()
    first = await svc._create_notification_if_fresh(
        seeded_db_session,
        user_id=alice.id,
        category=NotificationCategory.APPROVAL,
        title="请审批",
        biz_type="pr",
        biz_id=biz_id,
    )
    assert first is not None

    second = await svc._create_notification_if_fresh(
        seeded_db_session,
        user_id=alice.id,
        category=NotificationCategory.APPROVAL,
        title="请审批(dup)",
        biz_type="pr",
        biz_id=biz_id,
    )
    assert second is None


async def test_list_notifications_returns_user_rows(seeded_db_session):
    alice = await _get_alice(seeded_db_session)
    for i in range(3):
        await svc.create_notification(
            seeded_db_session,
            user_id=alice.id,
            category=NotificationCategory.SYSTEM,
            title=f"msg {i}",
        )

    rows = await svc.list_notifications(seeded_db_session, user_id=alice.id, limit=10)
    assert len(rows) == 3


async def test_count_unread_returns_zero_when_none(seeded_db_session):
    alice = await _get_alice(seeded_db_session)
    result = await svc.count_unread(seeded_db_session, user_id=alice.id)
    assert result["total"] == 0
    assert result["by_category"] == {}


async def test_count_unread_tallies_by_category(seeded_db_session):
    alice = await _get_alice(seeded_db_session)
    await svc.create_notification(
        seeded_db_session, user_id=alice.id,
        category=NotificationCategory.APPROVAL, title="a",
    )
    await svc.create_notification(
        seeded_db_session, user_id=alice.id,
        category=NotificationCategory.APPROVAL, title="b",
    )
    await svc.create_notification(
        seeded_db_session, user_id=alice.id,
        category=NotificationCategory.CONTRACT_EXPIRING, title="c",
    )

    result = await svc.count_unread(seeded_db_session, user_id=alice.id)
    assert result["total"] == 3
    by_cat = result["by_category"]
    assert by_cat["approval"] == 2
    assert by_cat["contract_expiring"] == 1


async def test_mark_read_by_ids_zeroes_count(seeded_db_session):
    alice = await _get_alice(seeded_db_session)
    n1 = await svc.create_notification(
        seeded_db_session, user_id=alice.id,
        category=NotificationCategory.APPROVAL, title="a",
    )
    n2 = await svc.create_notification(
        seeded_db_session, user_id=alice.id,
        category=NotificationCategory.APPROVAL, title="b",
    )

    updated = await svc.mark_read(
        seeded_db_session, user_id=alice.id, notification_ids=[n1.id, n2.id]
    )
    assert updated == 2

    count = await svc.count_unread(seeded_db_session, user_id=alice.id)
    assert count["total"] == 0


async def test_mark_read_all_zeroes_all(seeded_db_session):
    alice = await _get_alice(seeded_db_session)
    for _ in range(3):
        await svc.create_notification(
            seeded_db_session, user_id=alice.id,
            category=NotificationCategory.SYSTEM, title="x",
        )

    updated = await svc.mark_read(seeded_db_session, user_id=alice.id, all=True)
    assert updated == 3

    count = await svc.count_unread(seeded_db_session, user_id=alice.id)
    assert count["total"] == 0


async def test_mark_read_all_zeroes_all(seeded_db_session):
    alice = await _get_alice(seeded_db_session)
    for _ in range(3):
        await svc.create_notification(
            seeded_db_session,
            user_id=alice.id,
            category=NotificationCategory.SYSTEM,
            title="x",
        )

    result = await svc.mark_read(seeded_db_session, user_id=alice.id, all=True)
    assert result == 3

    count = await svc.count_unread(seeded_db_session, user_id=alice.id)
    assert count["total"] == 0
