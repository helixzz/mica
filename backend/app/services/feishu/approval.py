from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.feishu.client import FeishuClient, FeishuError
from app.services.system_params import system_params

logger = logging.getLogger("mica.feishu.approval")


async def create_payment_approval(
    db: AsyncSession,
    *,
    payment_id: str,
    po_number: str,
    supplier: str,
    amount: str,
    submitter_email: str,
    title: str = "",
) -> dict[str, Any] | None:
    enabled = await system_params.get(db, "auth.feishu.enabled", False)
    workflow_enabled = await system_params.get(db, "auth.feishu.payment_workflow", False)
    if not enabled or not workflow_enabled:
        return None

    approval_code = await system_params.get(db, "auth.feishu.approval_code", "")
    if not approval_code:
        logger.warning("feishu.payment_workflow enabled but approval_code not configured")
        return None

    client = FeishuClient(db)
    try:
        user_info = await client.get_user_by_email(submitter_email)
        if not user_info:
            logger.warning("feishu: user not found for email %s", submitter_email)
            return None

        user_id = user_info.get("user_id", "")
        if not user_id:
            return None

        form_values = [
            {"id": "payment_id", "value": payment_id},
            {"id": "po_number", "value": po_number},
            {"id": "supplier", "value": supplier},
            {"id": "amount", "value": amount},
        ]

        instance_title = title or f"付款审批 - {po_number} - {amount}"
        result = await client.create_approval_instance(
            approval_code=str(approval_code),
            user_id=user_id,
            form_values=form_values,
            title=instance_title,
        )
        return result
    except FeishuError as e:
        logger.warning("feishu: create_approval_instance failed: %s", e)
        return None
    finally:
        await client.close()


async def get_approval_status(
    db: AsyncSession,
    instance_id: str,
) -> dict[str, Any] | None:
    enabled = await system_params.get(db, "auth.feishu.enabled", False)
    if not enabled:
        return None

    client = FeishuClient(db)
    try:
        return await client.get_approval_instance(instance_id)
    except FeishuError as e:
        logger.warning("feishu: get_approval_instance failed: %s", e)
        return None
    finally:
        await client.close()
