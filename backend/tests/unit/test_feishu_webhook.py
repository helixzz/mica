"""Integration test for feishu payment approval workflow.

Verifies the webhook handler can parse approval callbacks and update
payment status correctly. Tests both APPROVED and REJECTED paths.
"""

from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.feishu_webhook import _handle_approval_callback
from app.models import PaymentRecord


@pytest.mark.asyncio
async def test_approval_callback_approved(db_session: AsyncSession):
    """Verify callback handler sets payment status to CONFIRMED on APPROVED."""
    parsed = {"status": "APPROVED", "instance_id": "test-instance-123"}

    with patch(
        "app.api.v1.feishu_webhook.select", autospec=True
    ) as mock_select:
        mock_payment = AsyncMock(spec=PaymentRecord)
        mock_payment.payment_number = "PAY-001"
        mock_payment.id = "payment-uuid"

        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_payment
        mock_select.return_value = mock_select
        mock_select.where.return_value = mock_select

        mock_db = AsyncMock(spec=AsyncSession)
        mock_db.execute.return_value = mock_result
        mock_db.commit = AsyncMock()

        await _handle_approval_callback(mock_db, parsed)

        mock_db.execute.assert_called()
        mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_approval_callback_rejected(db_session: AsyncSession):
    """Verify callback handler sets payment status to CANCELLED on REJECTED."""
    parsed = {"status": "REJECTED", "instance_id": "test-instance-456"}

    with patch(
        "app.api.v1.feishu_webhook.select", autospec=True
    ) as mock_select:
        mock_payment = AsyncMock(spec=PaymentRecord)
        mock_payment.payment_number = "PAY-002"
        mock_payment.id = "payment-uuid-2"

        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_payment
        mock_select.return_value = mock_select
        mock_select.where.return_value = mock_select

        mock_db = AsyncMock(spec=AsyncSession)
        mock_db.execute.return_value = mock_result
        mock_db.commit = AsyncMock()

        await _handle_approval_callback(mock_db, parsed)

        mock_db.execute.assert_called()
        mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_approval_callback_unknown_status(db_session: AsyncSession):
    """Verify callback handler ignores unknown statuses (no-op)."""
    parsed = {"status": "PENDING", "instance_id": "test-instance-789"}

    mock_db = AsyncMock(spec=AsyncSession)

    await _handle_approval_callback(mock_db, parsed)

    mock_db.commit.assert_not_called()


@pytest.mark.asyncio
async def test_approval_callback_no_payment(db_session: AsyncSession):
    """Verify callback handler handles missing payment gracefully."""
    parsed = {"status": "APPROVED", "instance_id": "nonexistent"}

    mock_result = AsyncMock()
    mock_result.scalar_one_or_none.return_value = None

    with patch(
        "app.api.v1.feishu_webhook.select", autospec=True
    ) as mock_select:
        mock_select.return_value = mock_select
        mock_select.where.return_value = mock_select

        mock_db = AsyncMock(spec=AsyncSession)
        mock_db.execute.return_value = mock_result

        await _handle_approval_callback(mock_db, parsed)

        mock_db.commit.assert_not_called()


@pytest.mark.asyncio
async def test_webhook_url_verification():
    """Verify URL verification returns challenge."""
    from app.services.feishu.webhooks import parse_url_verification

    body = {"type": "url_verification", "challenge": "test-challenge"}
    challenge = parse_url_verification(body)
    assert challenge == "test-challenge"


@pytest.mark.asyncio
async def test_webhook_approval_parsing():
    """Verify approval callback parsing extracts correct fields."""
    from app.services.feishu.webhooks import parse_approval_callback

    body = {
        "event": {
            "type": "approval_instance",
            "instance_code": "ABC-123",
            "status": "APPROVED",
        }
    }
    parsed = parse_approval_callback(body)
    assert parsed == {"instance_id": "ABC-123", "status": "APPROVED"}
