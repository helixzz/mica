from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
from typing import Any

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.system_params import system_params

logger = logging.getLogger("mica.feishu")

FEISHU_BASE_URL = "https://open.feishu.cn"
TOKEN_BUFFER_SECONDS = 300


class FeishuClient:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._token: str | None = None
        self._token_expires_at: float = 0
        self._client = httpx.AsyncClient(base_url=FEISHU_BASE_URL, timeout=15.0)

    async def _ensure_token(self) -> str:
        now = time.time()
        if self._token and now < self._token_expires_at - TOKEN_BUFFER_SECONDS:
            return self._token

        app_id = await system_params.get(self._db, "auth.feishu.app_id", "")
        app_secret = await system_params.get(self._db, "auth.feishu.app_secret", "")
        if not app_id or not app_secret:
            raise FeishuError("feishu.not_configured")

        resp = await self._client.post(
            "/open-apis/auth/v3/tenant_access_token/internal",
            json={"app_id": str(app_id), "app_secret": str(app_secret)},
        )
        data = resp.json()
        if data.get("code") != 0:
            raise FeishuError(f"feishu.token_failed: {data.get('msg', 'unknown')}")

        self._token = data["tenant_access_token"]
        self._token_expires_at = now + data.get("expire", 7200)
        return self._token

    async def _request(
        self, method: str, path: str, json_body: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        token = await self._ensure_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
        }
        resp = await self._client.request(method, path, json=json_body, headers=headers)
        data = resp.json()
        if data.get("code") != 0:
            raise FeishuError(f"feishu.api_error: {data.get('code')} {data.get('msg', '')}")
        return data

    async def send_card(
        self,
        receive_id_type: str,
        receive_id: str,
        card: dict[str, Any],
    ) -> dict[str, Any]:
        return await self._request(
            "POST",
            "/open-apis/im/v1/messages",
            json_body={
                "receive_id_type": receive_id_type,
                "receive_id": receive_id,
                "msg_type": "interactive",
                "content": json.dumps(card, ensure_ascii=False),
            },
        )

    async def create_approval_instance(
        self,
        approval_code: str,
        user_id: str,
        form_values: list[dict[str, Any]],
        title: str = "",
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "approval_code": approval_code,
            "user_id": user_id,
            "form": json.dumps(form_values, ensure_ascii=False),
        }
        if title:
            payload["title"] = title
        return await self._request(
            "POST",
            "/open-apis/approval/v4/instances",
            json_body=payload,
        )

    async def get_approval_instance(self, instance_id: str) -> dict[str, Any]:
        return await self._request(
            "GET",
            f"/open-apis/approval/v4/instances/{instance_id}",
        )

    async def get_user_by_email(self, email: str) -> dict[str, Any] | None:
        try:
            data = await self._request(
                "GET",
                f"/open-apis/user/v4/batch_get?emails={email}",
            )
            users = data.get("data", {}).get("email_users", {})
            user_list = users.get(email, [])
            return user_list[0] if user_list else None
        except FeishuError:
            return None

    async def close(self) -> None:
        await self._client.aclose()

    @staticmethod
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


class FeishuError(Exception):
    pass
