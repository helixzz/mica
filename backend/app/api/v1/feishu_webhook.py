from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.feishu.webhooks import (
    parse_approval_callback,
    parse_url_verification,
    verify_signature,
)
from app.services.system_params import system_params

logger = logging.getLogger("mica.feishu.webhook")

router = APIRouter(prefix="/feishu", tags=["feishu"])


@router.post("/webhook")
async def feishu_webhook(request: Request) -> dict[str, Any]:
    body_bytes = await request.body()
    try:
        body: dict[str, Any] = json.loads(body_bytes)
    except json.JSONDecodeError as err:
        raise HTTPException(400, "feishu.invalid_body") from err

    challenge = parse_url_verification(body)
    if challenge:
        return {"challenge": challenge}

    async with AsyncSession() as db:  # type: ignore[var-annotated]
        try:
            app_secret_raw = await system_params.get(db, "auth.feishu.app_secret", "")
            app_secret = str(app_secret_raw) if app_secret_raw else ""
            if app_secret:
                timestamp = request.headers.get("x-lark-request-timestamp", "")
                nonce = request.headers.get("x-lark-request-nonce", "")
                signature = request.headers.get("x-lark-signature", "")
                if timestamp and nonce and signature:
                    if not verify_signature(timestamp, nonce, body_bytes, signature, app_secret):
                        logger.warning("feishu: webhook signature verification failed")
                        raise HTTPException(401, "feishu.invalid_signature")

            parsed = parse_approval_callback(body)
            if parsed:
                await _handle_approval_callback(db, parsed)
        finally:
            await db.close()

    return {"code": 0}


async def _handle_approval_callback(
    db: AsyncSession,
    parsed: dict[str, Any],
) -> None:
    status = parsed.get("status", "")
    instance_id = parsed.get("instance_id", "")

    if status not in ("APPROVED", "REJECTED", "CANCELED"):
        return

    logger.info(
        "feishu: approval callback instance=%s status=%s",
        instance_id,
        status,
    )

    try:
        from sqlalchemy import select, update

        from app.models import PaymentRecord, PaymentStatus

        payment_status = (
            PaymentStatus.CONFIRMED.value if status == "APPROVED" else PaymentStatus.CANCELLED.value
        )

        result = await db.execute(
            select(PaymentRecord).where(
                PaymentRecord.transaction_ref == instance_id,
            )
        )
        payment = result.scalar_one_or_none()
        if payment:
            await db.execute(
                update(PaymentRecord)
                .where(PaymentRecord.id == payment.id)
                .values(status=payment_status)
            )
            await db.commit()
            logger.info(
                "feishu: payment %s status updated to %s via approval callback",
                payment.payment_number,
                payment_status,
            )
    except Exception:
        logger.exception("feishu: failed to handle approval callback")
        await db.rollback()
