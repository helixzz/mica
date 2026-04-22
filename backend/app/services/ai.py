from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import decrypt
from app.core.litellm_helpers import resolve_litellm_model
from app.models import AICallLog, AIFeatureRouting, AIModel, User

PROMPT_TEMPLATES: dict[str, str] = {
    "pr_description_polish": (
        "你是企业采购系统的写作助手。请把用户草稿改写为更清晰、专业的业务说明，"
        "保留原意、保留关键数字和规格，避免夸大。\n\n"
        "草稿：\n{draft}\n\n"
        "改写后（直接输出正文，不要加前缀或引号）："
    ),
    "sku_suggest": (
        "用户在采购系统里输入了自由文本商品名，请从下面的标准物料清单中挑出最匹配的 3 个，"
        "按相关度从高到低排列，每行一个，格式：{{code}} | {{name}} | {{reason}}\n\n"
        "用户输入：{query}\n\n"
        "可选清单：\n{catalog}\n\n"
        "推荐："
    ),
}


async def _get_routing(
    db: AsyncSession, feature_code: str
) -> tuple[AIFeatureRouting, AIModel | None]:
    routing = (
        await db.execute(
            select(AIFeatureRouting).where(AIFeatureRouting.feature_code == feature_code)
        )
    ).scalar_one_or_none()
    if routing is None:
        raise RuntimeError(f"ai.feature_not_configured:{feature_code}")
    if not routing.enabled:
        raise RuntimeError(f"ai.feature_disabled:{feature_code}")
    model = None
    if routing.primary_model_id:
        model = (
            await db.execute(select(AIModel).where(AIModel.id == routing.primary_model_id))
        ).scalar_one_or_none()
    return routing, model


async def _log_call(
    db: AsyncSession,
    user: User | None,
    feature: str,
    model: AIModel | None,
    status: str,
    latency_ms: int,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    error: str | None = None,
) -> None:
    db.add(
        AICallLog(
            feature_code=feature,
            user_id=user.id if user else None,
            model_name=model.name if model else None,
            provider=model.provider if model else None,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=latency_ms,
            status=status,
            error=error,
        )
    )
    await db.commit()


async def _mock_stream(text: str) -> AsyncGenerator[str, None]:
    for chunk in text.split(" "):
        await asyncio.sleep(0.03)
        yield chunk + " "


async def _call_litellm_stream(
    model: AIModel, prompt: str, temperature: float, max_tokens: int
) -> AsyncGenerator[str, None]:
    try:
        from litellm import acompletion
    except ImportError:
        async for chunk in _mock_stream(
            "[AI unavailable: litellm not installed. Please install litellm.] "
        ):
            yield chunk
        return

    api_key = decrypt(model.api_key_encrypted) if model.api_key_encrypted else None
    kwargs: dict[str, Any] = {
        "model": resolve_litellm_model(model.provider, model.model_string),
        "messages": [{"role": "user", "content": prompt}],
        "stream": True,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if api_key:
        kwargs["api_key"] = api_key
    if model.api_base:
        kwargs["api_base"] = model.api_base

    try:
        response = await acompletion(**kwargs)
        async for chunk in response:
            delta = chunk.choices[0].delta
            if delta and delta.content:
                yield delta.content
    except Exception as e:
        async for chunk in _mock_stream(f"[AI error: {e}] "):
            yield chunk


def render_prompt(template_key: str, **kwargs) -> str:
    tpl = PROMPT_TEMPLATES.get(template_key)
    if tpl is None:
        raise ValueError(f"unknown_template:{template_key}")
    return tpl.format(**kwargs)


async def stream_feature(
    db: AsyncSession,
    user: User,
    feature_code: str,
    prompt: str,
) -> AsyncGenerator[str, None]:
    routing, model = await _get_routing(db, feature_code)
    start = time.monotonic()
    completion = ""
    status = "success"
    error: str | None = None
    try:
        if model is None:
            async for chunk in _mock_stream(
                "[AI 演示模式] 当前没有配置 AI 模型。请在管理后台配置 LLM 模型与场景路由。\n"
                "This is demo mode. Configure LLM models in admin panel to enable real AI. "
            ):
                completion += chunk
                yield chunk
        else:
            async for chunk in _call_litellm_stream(
                model,
                prompt,
                float(routing.temperature),
                int(routing.max_tokens),
            ):
                completion += chunk
                yield chunk
    except Exception as e:
        status = "error"
        error = str(e)
        async for chunk in _mock_stream(f"[AI call failed: {e}] "):
            yield chunk
    finally:
        latency_ms = int((time.monotonic() - start) * 1000)
        try:
            await _log_call(
                db,
                user,
                feature_code,
                model,
                status,
                latency_ms,
                prompt_tokens=len(prompt) // 4,
                completion_tokens=len(completion) // 4,
                error=error,
            )
        except Exception:
            pass
