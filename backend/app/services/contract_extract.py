"""AI-powered contract information extraction from scanned documents.

Reuses the same AI routing infrastructure as invoice extraction.
Extracts: contract_number, title, supplier_name, start_date, end_date,
total_amount, and description from contract scan PDFs/images.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AICallLog, AIModel, User

logger = logging.getLogger("mica.contract_extract")


@dataclass
class ContractExtract:
    contract_number: str | None = None
    title: str | None = None
    supplier_name: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    total_amount: str | None = None
    description: str | None = None
    error: str | None = None


async def extract_contract(
    db: AsyncSession,
    actor: User,
    content: bytes,
    content_type: str,
    filename: str = "",
) -> ContractExtract:
    start = time.monotonic()
    try:
        result = await _dispatch(db, actor, content, content_type, filename)
    except Exception as e:
        result = ContractExtract(error=str(e))
    finally:
        elapsed = int((time.monotonic() - start) * 1000)
        try:
            db.add(
                AICallLog(
                    feature_code="contract_extract",
                    user_id=actor.id,
                    model_name=None,
                    provider=None,
                    prompt_tokens=0,
                    completion_tokens=0,
                    latency_ms=elapsed,
                    status="success" if not result.error else "error",
                    error=result.error,
                )
            )
        except Exception:
            pass
    return result


async def _dispatch(
    db: AsyncSession,
    actor: User | None,
    content: bytes,
    content_type: str,
    filename: str,
) -> ContractExtract:
    from sqlalchemy import select

    from app.models import AIFeatureRouting

    routing_row = (
        await db.execute(
            select(AIFeatureRouting).where(
                AIFeatureRouting.feature_code == "contract_extract",
                AIFeatureRouting.enabled.is_(True),
            )
        )
    ).scalar_one_or_none()

    if not routing_row or not routing_row.primary_model_id:
        return ContractExtract(error="No AI model configured for contract extraction")

    model_row = await db.get(AIModel, routing_row.primary_model_id)
    if not model_row or not model_row.is_active:
        return ContractExtract(error="AI model not found or inactive")

    import litellm

    from app.core.crypto import decrypt
    from app.core.litellm_helpers import resolve_litellm_model

    prompt = _build_prompt(filename)

    # Extract text from PDF if available; otherwise use base64
    text_content = ""
    if content_type == "application/pdf" or filename.lower().endswith(".pdf"):
        try:
            import io

            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(content))
            for i, page in enumerate(reader.pages[:5]):
                page_text = page.extract_text() or ""
                if page_text.strip():
                    text_content += f"\n--- Page {i+1} ---\n{page_text}"
        except Exception:
            pass

    if text_content:
        prompt = f"{prompt}\n\nExtracted document text:\n{text_content[:8000]}"

    try:
        response = await litellm.acompletion(
            model=resolve_litellm_model(model_row.provider, model_row.model_string),
            messages=[{"role": "user", "content": prompt}],
            api_base=model_row.api_base or None,
            api_key=decrypt(model_row.api_key_encrypted) if model_row.api_key_encrypted else None,
            temperature=0.1,
            max_tokens=4000,
            timeout=120,
            extra_body={"enable_thinking": False},
        )
    except Exception as e:
        return ContractExtract(error=f"AI call failed: {e}")

    choice = response.choices[0]
    text = choice.message.content or ""
    if not text:
        text = getattr(choice.message, "reasoning_content", None) or ""
    if not text:
        text = getattr(choice, "text", None) or ""
logger.info("contract_extract: response (%d chars) finish=%s", len(text), choice.finish_reason)
    return _parse_response(text)


def _parse_response(text: str) -> ContractExtract:
    try:
        # Strip markdown code blocks
        t = text.strip()
        if t.startswith("```"):
            lines = t.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]  # skip opening ```
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]  # skip closing ```
            t = "\n".join(lines)
        data: dict[str, Any] = json.loads(t)
    except (json.JSONDecodeError, ValueError) as e:
        return ContractExtract(error=f"Failed to parse: {e} (got: {text[:200]})")

    return ContractExtract(
        contract_number=data.get("contract_number") or None,
        title=data.get("title") or None,
        supplier_name=data.get("supplier_name") or None,
        start_date=data.get("start_date") or None,
        end_date=data.get("end_date") or None,
        total_amount=str(data.get("total_amount")) if data.get("total_amount") else None,
        description=data.get("description") or None,
    )
