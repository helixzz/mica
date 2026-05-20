# pyright: reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportUnusedCallResult=false

from unittest.mock import MagicMock

import pytest
from sqlalchemy import select

from app.models import User, UserRole
from app.services import approval_reminder, sla_escalation


@pytest.mark.asyncio
async def test_approval_reminder_disabled(db_session, monkeypatch):
    async def disabled_get(self, session, key, default=None):
        return False

    monkeypatch.setattr(approval_reminder.system_params, "get", disabled_get)

    result = await approval_reminder.send_reminders(db_session)
    assert result["scanned"] == 0
    assert result["reminded"] == 0
    assert result["notifications"] == 0
    assert result["reminder_disabled"] is True


@pytest.mark.asyncio
async def test_approval_reminder_no_pending_instances(db_session):
    result = await approval_reminder.send_reminders(db_session)
    assert result["scanned"] == 0
    assert result["reminded"] == 0
    assert result["notifications"] == 0


def test_approval_reminder_locale_none():
    assert approval_reminder._locale(None) == "zh-CN"


def test_approval_reminder_locale_with_user():
    user = MagicMock()
    user.preferred_locale = "en-US"
    assert approval_reminder._locale(user) == "en-US"


@pytest.mark.asyncio
async def test_sla_escalation_disabled(db_session, monkeypatch):
    async def disabled_get(self, session, key, default=None):
        return False

    monkeypatch.setattr(sla_escalation.system_params, "get", disabled_get)

    result = await sla_escalation.check_overdue_approvals(db_session)
    assert result["scanned"] == 0
    assert result["escalated"] == 0
    assert result["notifications"] == 0
    assert result["sla_disabled"] is True


@pytest.mark.asyncio
async def test_sla_escalation_no_pending_instances(db_session):
    result = await sla_escalation.check_overdue_approvals(db_session)
    assert result["scanned"] == 0
    assert result["escalated"] == 0
    assert result["notifications"] == 0


@pytest.mark.asyncio
async def test_sla_escalation_with_pending_instance_mocked_notifications(
    seeded_db_session, monkeypatch
):
    from datetime import UTC, datetime, timedelta
    from uuid import uuid4

    from app.models import ApprovalInstance, ApprovalTask

    admin = (
        (await seeded_db_session.execute(select(User).where(User.role == UserRole.ADMIN.value)))
        .scalars()
        .first()
    )

    instance = ApprovalInstance(
        biz_type="pr",
        biz_id=uuid4(),
        biz_number="PR-SLA-001",
        title="SLA Test PR",
        status="pending",
        submitter_id=admin.id,
        company_id=admin.company_id,
        submitted_at=datetime.now(UTC) - timedelta(hours=48),
    )
    seeded_db_session.add(instance)
    await seeded_db_session.flush()
    seeded_db_session.add(
        ApprovalTask(
            instance_id=instance.id,
            stage_order=1,
            stage_name="manager",
            assignee_id=admin.id,
            status="pending",
            assigned_at=datetime.now(UTC) - timedelta(hours=47),
        )
    )
    await seeded_db_session.commit()

    async def _mock_create(db, *args, **kwargs):
        return MagicMock()

    async def _mock_bulk_notify(db, *args, **kwargs):
        return [MagicMock(), MagicMock()]

    monkeypatch.setattr(sla_escalation, "create_notification", _mock_create)
    monkeypatch.setattr(sla_escalation, "bulk_notify_role", _mock_bulk_notify)

    result = await sla_escalation.check_overdue_approvals(seeded_db_session)
    assert result["scanned"] >= 1
    assert result["escalated"] >= 1
    assert result["notifications"] >= 1


@pytest.mark.asyncio
async def test_approval_reminder_with_pending_instance(seeded_db_session, monkeypatch):
    from datetime import UTC, datetime, timedelta
    from uuid import uuid4

    from app.models import ApprovalInstance, ApprovalTask

    admin = (
        (await seeded_db_session.execute(select(User).where(User.role == UserRole.ADMIN.value)))
        .scalars()
        .first()
    )

    instance = ApprovalInstance(
        biz_type="pr",
        biz_id=uuid4(),
        biz_number="PR-REMIND-001",
        title="Reminder Test PR",
        status="pending",
        submitter_id=admin.id,
        company_id=admin.company_id,
        submitted_at=datetime.now(UTC) - timedelta(hours=12),
    )
    seeded_db_session.add(instance)
    await seeded_db_session.flush()
    seeded_db_session.add(
        ApprovalTask(
            instance_id=instance.id,
            stage_order=1,
            stage_name="manager",
            assignee_id=admin.id,
            status="pending",
            assigned_at=datetime.now(UTC) - timedelta(hours=11),
        )
    )
    await seeded_db_session.commit()

    async def _mock_create(db, *args, **kwargs):
        return MagicMock()

    monkeypatch.setattr(approval_reminder, "create_notification", _mock_create)

    result = await approval_reminder.send_reminders(seeded_db_session)
    assert result["scanned"] >= 1
    assert result["reminded"] >= 1
    assert result["notifications"] >= 1
