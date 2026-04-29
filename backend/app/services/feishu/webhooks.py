from __future__ import annotations

import hashlib
import hmac
import logging
from typing import Any

logger = logging.getLogger("mica.feishu.webhooks")


def verify_signature(
    timestamp: str,
    nonce: str,
    body: bytes,
    signature: str,
    app_secret: str,
) -> bool:
    raw = f"{timestamp}{nonce}{app_secret}{body.decode('utf-8')}"
    expected = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return hmac.compare_digest(expected, signature)


def parse_approval_callback(body: dict[str, Any]) -> dict[str, Any] | None:
    event = body.get("event", {})
    event_type = event.get("type", "")
    if event_type != "approval_instance":
        return None

    instance_code = event.get("approval_code", "")
    instance_id = event.get("instance_code", "")
    status = event.get("status", "")
    return {
        "approval_code": instance_code,
        "instance_id": instance_id,
        "status": status,
        "raw": event,
    }


def parse_url_verification(body: dict[str, Any]) -> str | None:
    if body.get("type") == "url_verification":
        return body.get("challenge", "")
    return None
