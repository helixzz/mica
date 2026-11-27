"""Feishu WebSocket long-connection consumer for interactive card callbacks.

Runs inside ``mica-scheduler`` (single instance) and dials out to Feishu via
``lark_oapi.ws.Client``, so Mica requires no inbound public port or webhook URL.
"""

from __future__ import annotations

import asyncio
import logging
import threading
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.services.feishu.card_callback import handle_card_action
from app.services.system_params import system_params

logger = logging.getLogger("mica.feishu.ws")

CALLBACK_TIMEOUT_SECONDS = 2.5


def _build_p2_response(payload: dict[str, Any]) -> Any:
    from lark_oapi.event.callback.model.p2_card_action_trigger import (
        CallBackCard,
        CallBackToast,
        P2CardActionTriggerResponse,
    )

    resp = P2CardActionTriggerResponse()
    toast_data = payload.get("toast")
    if isinstance(toast_data, dict):
        toast = CallBackToast()
        toast.type = str(toast_data.get("type") or "info")
        toast.content = str(toast_data.get("content") or "")
        resp.toast = toast

    card_data = payload.get("card")
    if isinstance(card_data, dict):
        card = CallBackCard()
        card.type = str(card_data.get("type") or "raw")
        card.data = card_data.get("data")
        resp.card = card

    return resp


async def start_feishu_ws_consumer(
    session_factory: async_sessionmaker[AsyncSession],
    loop: asyncio.AbstractEventLoop,
) -> threading.Thread | None:
    """Start the Feishu WS callback consumer in a daemon thread if configured."""
    async with session_factory() as db:
        enabled = await system_params.get_bool_or(db, "feishu.card_callback_enabled", True)
        app_id = str(await system_params.get(db, "auth.feishu.app_id", "") or "").strip()
        app_secret = str(await system_params.get(db, "auth.feishu.app_secret", "") or "").strip()

    if not enabled:
        logger.info("feishu ws: disabled via feishu.card_callback_enabled")
        return None
    if not app_id or not app_secret:
        logger.info("feishu ws: skipped (auth.feishu.app_id / app_secret not configured)")
        return None

    try:
        import lark_oapi as lark
    except ImportError:
        logger.warning("feishu ws: lark-oapi is not installed; interactive card callbacks disabled")
        return None

    def _on_card_action(data: Any) -> Any:
        event = getattr(data, "event", None)
        action = getattr(event, "action", None)
        operator = getattr(event, "operator", None)
        action_value = getattr(action, "value", None) or {}
        form_value = getattr(action, "form_value", None) or {}
        open_id = str(getattr(operator, "open_id", "") or "")
        union_id = str(getattr(operator, "union_id", "") or "")

        async def _run() -> dict[str, Any]:
            async with session_factory() as session:
                return await handle_card_action(
                    session,
                    action_value=dict(action_value),
                    form_value=dict(form_value),
                    operator_open_id=open_id,
                    operator_union_id=union_id,
                )

        future = asyncio.run_coroutine_threadsafe(_run(), loop)
        try:
            result = future.result(timeout=CALLBACK_TIMEOUT_SECONDS)
        except Exception:
            logger.exception("feishu ws: card action timed out or failed")
            result = {"toast": {"type": "error", "content": "处理超时，请在 Mica 中查看结果"}}
        return _build_p2_response(result)

    event_handler = (
        lark.EventDispatcherHandler.builder("", "")
        .register_p2_card_action_trigger(_on_card_action)
        .build()
    )
    ws_client = lark.ws.Client(
        app_id,
        app_secret,
        event_handler=event_handler,
        log_level=lark.LogLevel.WARNING,
    )

    def _run_forever() -> None:
        logger.info("feishu ws: starting long-connection consumer")
        try:
            ws_client.start()
        except Exception:
            logger.exception("feishu ws: consumer exited unexpectedly")

    thread = threading.Thread(target=_run_forever, name="feishu-ws-consumer", daemon=True)
    thread.start()
    return thread
