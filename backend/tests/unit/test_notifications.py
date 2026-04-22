# pyright: reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportPrivateUsage=false, reportUnusedCallResult=false

from typing import cast
from uuid import uuid4

from sqlalchemy import select

from app.models import Company, NotificationCategory, NotificationSubscription, User, UserRole
from app.services import notifications as svc


async def _create_user(db_session, username: str = "alice") -> User:
    company = Company(
        code=f"DEMO-{uuid4().hex[:8]}",
        name_zh="测试公司",
        name_en="Test Company",
        default_locale="zh-CN",
        default_currency="CNY",
    )
    db_session.add(company)
    await db_session.flush()

    user = User(
        username=username,
        email=f"{username}@example.com",
        display_name=username.title(),
        role=UserRole.IT_BUYER.value,
        company_id=company.id,
        preferred_locale="zh-CN",
    )
    db_session.add(user)
    await db_session.flush()
    return user


async def test_create_notification_writes_row(db_session):
    alice = await _create_user(db_session)

    notification = await svc.create_notification(
        db_session,
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


async def test_create_notification_returns_none_when_subscription_disabled(db_session):
    alice = await _create_user(db_session)
    db_session.add(
        NotificationSubscription(
            user_id=alice.id,
            category=NotificationCategory.APPROVAL,
            in_app_enabled=False,
            email_enabled=False,
        )
    )
    await db_session.flush()

    notification = await svc.create_notification(
        db_session,
        user_id=alice.id,
        category=NotificationCategory.APPROVAL,
        title="muted",
    )

    assert notification is None


async def test_create_notification_resolves_callable_title(db_session):
    alice = await _create_user(db_session)

    notification = await svc.create_notification(
        db_session,
        user_id=alice.id,
        category=NotificationCategory.SYSTEM,
        title=lambda user: f"Hi {user.username if user else 'guest'}",
    )

    assert notification is not None
    assert notification.title == "Hi alice"


async def test_recent_notification_exists_false_without_biz_identifiers(db_session):
    alice = await _create_user(db_session)

    result = await svc._recent_notification_exists(
        db_session,
        user_id=alice.id,
        category=NotificationCategory.APPROVAL,
        biz_type=None,
        biz_id=None,
    )

    assert result is False


async def test_create_notification_if_fresh_dedupes_recent_notifications(db_session):
    alice = await _create_user(db_session)
    biz_id = uuid4()

    first = await svc._create_notification_if_fresh(
        db_session,
        user_id=alice.id,
        category=NotificationCategory.APPROVAL,
        title="请审批",
        biz_type="pr",
        biz_id=biz_id,
    )
    second = await svc._create_notification_if_fresh(
        db_session,
        user_id=alice.id,
        category=NotificationCategory.APPROVAL,
        title="重复通知",
        biz_type="pr",
        biz_id=biz_id,
    )

    assert first is not None
    assert second is None


async def test_list_notifications_and_count_unread_reflect_created_rows(db_session):
    alice = await _create_user(db_session)
    await svc.create_notification(
        db_session,
        user_id=alice.id,
        category=NotificationCategory.APPROVAL,
        title="a",
    )
    await svc.create_notification(
        db_session,
        user_id=alice.id,
        category=NotificationCategory.CONTRACT_EXPIRING,
        title="b",
    )

    rows = await svc.list_notifications(db_session, user_id=alice.id, limit=10)
    count = await svc.count_unread(db_session, user_id=alice.id)
    by_category = cast(dict[str, int], count["by_category"])

    assert len(rows) == 2
    assert count["total"] == 2
    assert by_category == {"approval": 1, "contract_expiring": 1}


async def test_mark_read_updates_selected_notifications(db_session):
    alice = await _create_user(db_session)
    n1 = await svc.create_notification(
        db_session,
        user_id=alice.id,
        category=NotificationCategory.APPROVAL,
        title="a",
    )
    n2 = await svc.create_notification(
        db_session,
        user_id=alice.id,
        category=NotificationCategory.APPROVAL,
        title="b",
    )
    assert n1 is not None
    assert n2 is not None

    updated = await svc.mark_read(
        db_session,
        user_id=alice.id,
        notification_ids=[n1.id, n2.id],
    )
    unread = await svc.count_unread(db_session, user_id=alice.id)

    assert updated == 2
    assert unread["total"] == 0


async def test_get_subscriptions_returns_defaults_for_missing_rows(db_session):
    alice = await _create_user(db_session)

    rows = await svc.get_subscriptions(db_session, user_id=alice.id)

    assert len(rows) == len(NotificationCategory)
    approval = next(row for row in rows if row.category == NotificationCategory.APPROVAL)
    assert approval.in_app_enabled is True
    assert approval.email_enabled is False


async def test_upsert_subscription_persists_and_updates_preference(db_session):
    alice = await _create_user(db_session)

    created = await svc.upsert_subscription(
        db_session,
        user_id=alice.id,
        category=NotificationCategory.PAYMENT_PENDING,
        in_app_enabled=False,
        email_enabled=True,
    )
    updated = await svc.upsert_subscription(
        db_session,
        user_id=alice.id,
        category=NotificationCategory.PAYMENT_PENDING,
        in_app_enabled=True,
        email_enabled=False,
    )
    stored = (
        await db_session.execute(
            select(NotificationSubscription).where(
                NotificationSubscription.user_id == alice.id,
                NotificationSubscription.category == NotificationCategory.PAYMENT_PENDING,
            )
        )
    ).scalar_one()

    assert updated.id == created.id
    assert stored.in_app_enabled is True
    assert stored.email_enabled is False
