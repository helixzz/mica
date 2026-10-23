"""Event notifications: dedupe, structured payload, and the Feishu ledger."""

from unittest.mock import AsyncMock
from uuid import uuid4

from sqlalchemy import select

from app.models import (
    NotificationCategory,
    NotificationDelivery,
    NotificationDeliveryStatus,
    User,
)
from app.services import notifications as svc


async def _alice(db):
    return (await db.execute(select(User).where(User.username == "alice"))).scalar_one()


async def _emit(db, user, *, fingerprint=("updated", "title-a"), **overrides):
    payload = {
        "user_id": user.id,
        "event": "pr_updated",
        "title": "PR-2026-0001 已更新",
        "link_url": "/purchase-requisitions/1",
        "biz_type": "pr",
        "biz_id": overrides.pop("biz_id", uuid4()),
        "fields": [("金额", "¥1,000.00")],
        "changes": [("标题", "旧 → 新")],
        "summary": "补充说明",
        "fingerprint_parts": fingerprint,
    }
    payload.update(overrides)
    return await svc.emit_event_notification(db, **payload)


async def test_same_fingerprint_is_announced_once(seeded_db_session):
    alice = await _alice(seeded_db_session)
    biz_id = uuid4()

    first = await _emit(seeded_db_session, alice, biz_id=biz_id)
    second = await _emit(seeded_db_session, alice, biz_id=biz_id)

    assert first is not None
    assert second is None


async def test_different_fingerprint_is_a_new_announcement(seeded_db_session):
    alice = await _alice(seeded_db_session)
    biz_id = uuid4()

    first = await _emit(seeded_db_session, alice, biz_id=biz_id, fingerprint=("updated", "a"))
    second = await _emit(seeded_db_session, alice, biz_id=biz_id, fingerprint=("updated", "b"))

    assert first is not None and second is not None


async def test_event_payload_carries_structured_fields(seeded_db_session):
    alice = await _alice(seeded_db_session)

    notification = await _emit(seeded_db_session, alice)

    assert notification is not None
    assert notification.meta["fields"] == [["金额", "¥1,000.00"]]
    assert notification.meta["changes"] == [["标题", "旧 → 新"]]
    assert notification.meta["event"] == "pr_updated"
    assert notification.dedupe_key
    assert notification.body == "补充说明"


def _feishu_params(flag_key: str, flag_value: bool):
    async def fake_get(session, key, default=None):
        if key == "auth.feishu.enabled":
            return True
        if key == flag_key:
            return flag_value
        return default

    return fake_get


async def test_admin_switch_off_suppresses_the_card(seeded_db_session, monkeypatch):
    alice = await _alice(seeded_db_session)
    monkeypatch.setattr(
        svc.system_params, "get", _feishu_params("auth.feishu.notify_on_system", False)
    )
    send = AsyncMock(return_value={"code": 0, "data": {"message_id": "om_x"}})
    monkeypatch.setattr(svc, "_send_feishu_card", send)

    notification = await svc.create_notification(
        seeded_db_session,
        user_id=alice.id,
        category=NotificationCategory.SYSTEM,
        title="PR 已更新",
    )

    assert notification is not None
    send.assert_not_awaited()


async def test_delivery_ledger_records_message_id(seeded_db_session, monkeypatch):
    alice = await _alice(seeded_db_session)
    monkeypatch.setattr(
        svc.system_params, "get", _feishu_params("auth.feishu.notify_on_system", True)
    )
    monkeypatch.setattr(
        svc,
        "_send_feishu_card",
        AsyncMock(return_value={"code": 0, "data": {"message_id": "om_123"}}),
    )

    notification = await svc.create_notification(
        seeded_db_session,
        user_id=alice.id,
        category=NotificationCategory.SYSTEM,
        title="PR 已更新",
        link_url="/purchase-requisitions/1",
    )
    await seeded_db_session.flush()

    delivery = (
        await seeded_db_session.execute(
            select(NotificationDelivery).where(
                NotificationDelivery.notification_id == notification.id
            )
        )
    ).scalar_one()
    assert delivery.status == NotificationDeliveryStatus.SENT.value
    assert delivery.message_id == "om_123"
    assert delivery.sent_at is not None


async def test_failed_delivery_is_recorded_for_retry(seeded_db_session, monkeypatch):
    alice = await _alice(seeded_db_session)
    monkeypatch.setattr(
        svc.system_params, "get", _feishu_params("auth.feishu.notify_on_system", True)
    )
    monkeypatch.setattr(
        svc, "_send_feishu_card", AsyncMock(side_effect=RuntimeError("feishu down"))
    )

    notification = await svc.create_notification(
        seeded_db_session,
        user_id=alice.id,
        category=NotificationCategory.SYSTEM,
        title="PR 已更新",
    )
    await seeded_db_session.flush()

    delivery = (
        await seeded_db_session.execute(
            select(NotificationDelivery).where(
                NotificationDelivery.notification_id == notification.id
            )
        )
    ).scalar_one()
    assert delivery.status == NotificationDeliveryStatus.FAILED.value
    assert delivery.next_retry_at is not None
    assert "feishu down" in (delivery.last_error or "")


async def test_two_accounts_sharing_one_feishu_identity_get_one_card(seeded_db_session, monkeypatch):
    """zijing-guo and admin shared a union_id in production; the event arrived twice."""
    alice = (await seeded_db_session.execute(select(User).where(User.username == "alice"))).scalar_one()
    bob = (await seeded_db_session.execute(select(User).where(User.username == "bob"))).scalar_one()
    alice.feishu_union_id = "on_shared"
    bob.feishu_union_id = "on_shared"
    await seeded_db_session.flush()

    monkeypatch.setattr(
        svc.system_params, "get", _feishu_params("auth.feishu.notify_on_system", True)
    )
    send = AsyncMock(return_value={"code": 0, "data": {"message_id": "om_one"}})
    monkeypatch.setattr(svc, "_send_feishu_card", send)

    first = await svc.create_notification(
        seeded_db_session,
        user_id=alice.id,
        category=NotificationCategory.SYSTEM,
        title="同一事件",
        dedupe_key="shared:event:1",
    )
    second = await svc.create_notification(
        seeded_db_session,
        user_id=bob.id,
        category=NotificationCategory.SYSTEM,
        title="同一事件",
        dedupe_key="shared:event:1",
    )
    await seeded_db_session.flush()

    assert first is not None and second is not None
    assert send.await_count == 1
