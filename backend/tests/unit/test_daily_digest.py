# pyright: reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportUnusedCallResult=false

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import select

from app.models import (
    Contract,
    Item,
    SKUPriceAnomaly,
    User,
    UserRole,
)
from app.services import daily_digest


def test_build_email_body_zh():
    from datetime import date as date_t

    body = daily_digest._build_email_body(
        pending_approvals=3,
        expiring_count=1,
        expiry_rows_html="<tr><td>C-001</td></tr>",
        sku_anomalies=2,
        anomaly_detail_html="<tr><td>Item A</td></tr>",
        today_po_count=5,
        today_po_amount=15000.0,
        upcoming_pay_count=2,
        upcoming_pay_amount=8000.0,
        overdue_count=4,
        today=date_t(2026, 5, 20),
        locale="zh-CN",
    )
    assert "今日概览" in body
    assert "<table" in body or "C-001" in body
    assert "5" in body
    assert "2026-05-20" in body
    assert "待审批" in body or "approval" in body.lower()


def test_build_email_body_en():
    from datetime import date as date_t

    body = daily_digest._build_email_body(
        pending_approvals=0,
        expiring_count=0,
        expiry_rows_html="<p><em>none</em></p>",
        sku_anomalies=0,
        anomaly_detail_html="<p><em>none</em></p>",
        today_po_count=0,
        today_po_amount=0.0,
        upcoming_pay_count=0,
        upcoming_pay_amount=0.0,
        overdue_count=0,
        today=date_t(2026, 5, 20),
        locale="en-US",
    )
    assert "<h2" in body
    assert "2026-05-20" in body
    assert "<body" in body


def test_build_expiry_rows_empty():
    result = daily_digest._build_expiry_rows([], "zh-CN")
    assert "<em>" in result


def test_build_expiry_rows_with_contracts():
    from datetime import date as date_t

    c = MagicMock(spec=Contract)
    c.contract_number = "C-001"
    c.title = "Server Maintenance"
    c.expiry_date = date_t(2026, 12, 31)
    c.total_amount = Decimal("50000.00")
    c.currency = "CNY"
    result = daily_digest._build_expiry_rows([c], "zh-CN")
    assert "C-001" in result
    assert "Server Maintenance" in result
    assert "2026-12-31" in result


def test_build_expiry_rows_without_currency():

    c = MagicMock(spec=Contract)
    c.contract_number = "C-002"
    c.title = "Office Supplies"
    c.expiry_date = None
    c.total_amount = Decimal("5000.00")
    del c.currency
    result = daily_digest._build_expiry_rows([c], "en-US")
    assert "C-002" in result
    assert "N/A" in result


def test_build_anomaly_detail_html_empty():
    result = daily_digest._build_anomaly_detail_html([], "zh-CN")
    assert "<em>" in result


def test_build_anomaly_detail_html_with_anomalies():

    anomaly = MagicMock(spec=SKUPriceAnomaly)
    anomaly.observed_price = Decimal("150.00")
    anomaly.baseline_avg_price = Decimal("100.00")
    anomaly.deviation_pct = Decimal("50.00")
    anomaly.severity = "warning"

    item = MagicMock(spec=Item)
    item.name = "Test SKU"

    result = daily_digest._build_anomaly_detail_html([(anomaly, item)], "zh-CN")
    assert "Test SKU" in result
    assert "<table" in result


@pytest.mark.asyncio
async def test_get_digest_recipients(seeded_db_session):
    recipients = await daily_digest._get_digest_recipients(seeded_db_session)
    assert isinstance(recipients, list)
    roles = {r.role for r in recipients}
    assert roles.issubset({UserRole.ADMIN.value, UserRole.PROCUREMENT_MGR.value})


@pytest.mark.asyncio
async def test_count_pending_approvals_empty(db_session):
    result = await daily_digest._count_pending_approvals(db_session)
    assert result == 0


@pytest.mark.asyncio
async def test_count_recent_anomalies_empty(db_session):
    result = await daily_digest._count_recent_anomalies(db_session)
    assert result == 0


@pytest.mark.asyncio
async def test_count_today_pos_empty(db_session):
    count, amount = await daily_digest._count_today_pos(db_session)
    assert count >= 0
    assert amount >= 0.0


@pytest.mark.asyncio
async def test_count_overdue_approvals_empty(db_session):
    result = await daily_digest._count_overdue_approvals(db_session)
    assert result == 0


@pytest.mark.asyncio
async def test_fetch_anomaly_rows_empty(db_session):
    result = await daily_digest._fetch_anomaly_rows(db_session)
    assert isinstance(result, list)
    assert len(result) == 0


@pytest.mark.asyncio
async def test_send_daily_digest_no_recipients(db_session, monkeypatch):
    monkeypatch.setattr(daily_digest, "_get_digest_recipients", AsyncMock(return_value=[]))
    result = await daily_digest.send_daily_digest(db_session)
    assert result["recipients_total"] == 0
    assert result["sent_successfully"] == 0


@pytest.mark.asyncio
async def test_send_daily_digest_with_recipients(seeded_db_session, monkeypatch):
    admin = (
        (await seeded_db_session.execute(select(User).where(User.role == UserRole.ADMIN.value)))
        .scalars()
        .first()
    )

    monkeypatch.setattr(daily_digest, "_get_digest_recipients", AsyncMock(return_value=[admin]))
    monkeypatch.setattr(daily_digest, "send_email", AsyncMock(return_value=True))

    async def _skip_feishu(*args, **kwargs):
        return None

    monkeypatch.setattr(daily_digest, "_send_feishu_digest", AsyncMock(side_effect=_skip_feishu))

    result = await daily_digest.send_daily_digest(seeded_db_session)
    assert result["recipients_total"] == 1
    assert result["sent_successfully"] == 1
    assert "pending_approvals" in result
    assert "expiring_contracts" in result


@pytest.mark.asyncio
async def test_send_daily_digest_email_fails(seeded_db_session, monkeypatch):
    admin = (
        (await seeded_db_session.execute(select(User).where(User.role == UserRole.ADMIN.value)))
        .scalars()
        .first()
    )

    monkeypatch.setattr(daily_digest, "_get_digest_recipients", AsyncMock(return_value=[admin]))
    monkeypatch.setattr(daily_digest, "send_email", AsyncMock(return_value=False))

    async def _skip_feishu(*args, **kwargs):
        return None

    monkeypatch.setattr(daily_digest, "_send_feishu_digest", AsyncMock(side_effect=_skip_feishu))

    result = await daily_digest.send_daily_digest(seeded_db_session)
    assert result["recipients_total"] == 1
    assert result["sent_successfully"] == 0
    assert len(result["failed_recipients"]) == 1


@pytest.mark.asyncio
async def test_send_daily_digest_email_exception(seeded_db_session, monkeypatch):
    admin = (
        (await seeded_db_session.execute(select(User).where(User.role == UserRole.ADMIN.value)))
        .scalars()
        .first()
    )

    monkeypatch.setattr(daily_digest, "_get_digest_recipients", AsyncMock(return_value=[admin]))

    async def _send_raise(*args, **kwargs):
        raise RuntimeError("SMTP down")

    monkeypatch.setattr(daily_digest, "send_email", _send_raise)

    async def _skip_feishu(*args, **kwargs):
        return None

    monkeypatch.setattr(daily_digest, "_send_feishu_digest", AsyncMock(side_effect=_skip_feishu))

    result = await daily_digest.send_daily_digest(seeded_db_session)
    assert result["sent_successfully"] == 0
    assert len(result["failed_recipients"]) == 1


@pytest.mark.asyncio
async def test_send_feishu_digest_disabled(db_session):
    from unittest.mock import MagicMock

    user = MagicMock(spec=User)
    user.preferred_locale = "zh-CN"
    user.feishu_union_id = "test-union-id"

    async def disabled_get(self, session, key, default=None):
        return False if key == "auth.feishu.enabled" else default

    import app.services.daily_digest as daily_digest_mod
    from app.services.daily_digest import _send_feishu_digest

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(daily_digest_mod.system_params, "get", disabled_get)
    try:
        await _send_feishu_digest(db_session, user, 3, 1, 2, 5, 15000.0, 2, 8000.0, 4)
    finally:
        monkeypatch.undo()


@pytest.mark.asyncio
async def test_send_feishu_digest_no_feishu_id(db_session):
    from unittest.mock import MagicMock

    user = MagicMock(spec=User)
    user.preferred_locale = "zh-CN"
    user.feishu_union_id = None
    user.feishu_open_id = None

    async def enabled_get(self, session, key, default=None):
        return True if key == "auth.feishu.enabled" else default

    import app.services.daily_digest as daily_digest_mod
    from app.services.daily_digest import _send_feishu_digest

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(daily_digest_mod.system_params, "get", enabled_get)
    try:
        await _send_feishu_digest(db_session, user, 0, 0, 0, 0, 0.0, 0, 0.0, 0)
    finally:
        monkeypatch.undo()


async def test_count_recent_anomalies_returns_int(seeded_db_session):
    from app.services.daily_digest import _count_recent_anomalies
    result = await _count_recent_anomalies(seeded_db_session)
    assert isinstance(result, int)


async def test_fetch_anomaly_rows_returns_list(seeded_db_session):
    from app.services.daily_digest import _fetch_anomaly_rows
    result = await _fetch_anomaly_rows(seeded_db_session)
    assert isinstance(result, list)


def test_build_anomaly_detail_html_zh():
    from app.services.daily_digest import _build_anomaly_detail_html
    html = _build_anomaly_detail_html([], locale="zh-CN")
    assert isinstance(html, str)
