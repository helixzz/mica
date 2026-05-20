# pyright: reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportUnusedCallResult=false

from unittest.mock import MagicMock

import pytest

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
