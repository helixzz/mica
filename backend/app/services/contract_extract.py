"""AI-powered contract information extraction from scanned documents."""

from __future__ import annotations

import base64
import json
import logging
import time
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import decrypt
from app.core.litellm_helpers import resolve_litellm_model
from app.models import AICallLog, AIModel, User

logger = logging.getLogger("mica.contract_extract")


@dataclass
class ContractExtract:
    contract_number: str | None = None
    title: str | None = None
    supplier_name: str | None = None
    supplier_contact: str | None = None
    supplier_phone: str | None = None
    supplier_id: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    total_amount: str | None = None
    payment_terms: str | None = None
    delivery_terms: str | None = None
    items_text: str | None = None
    description: str | None = None
    language: str | None = None
    error: str | None = None


def _build_prompt(filename: str) -> str:
    return f"""Extract these fields from this contract ({filename}). The document may be in Chinese, English, or bilingual. Extract data in the original language:

1. contract_number - contract reference number or ID
2. title - subject/title of the contract
3. supplier_name - name of the supplier/vendor/contractor
4. supplier_contact - contact person name
5. supplier_phone - contact phone number
6. start_date - contract start date (YYYY-MM-DD)
7. end_date - contract end/expiry date (YYYY-MM-DD)
8. total_amount - total contract value (number only, no currency symbol)
9. payment_terms - payment conditions (e.g. "NET 30", "50% advance, 50% on delivery")
10. delivery_terms - delivery/shipping conditions (e.g. "FOB Shanghai", "DDP")
11. items_text - list of items with name, spec, quantity, unit price. Format as bullet list.
12. description - 1-2 sentence summary in the document's language
13. language - document language: "zh", "en", or "bilingual"

Return ONLY valid JSON. Use null for missing fields.
Example: {{"contract_number":"CT-001","title":"Server Purchase","supplier_name":"Dell","supplier_contact":"Zhang San","supplier_phone":"13800138000","start_date":"2024-01-15","end_date":"2025-01-14","total_amount":"150000","payment_terms":"NET 30","delivery_terms":"FOB Shanghai","items_text":"- Dell R740 Server x 10 @ 12000/unit\\n- 32GB DDR4 RAM x 20 @ 800/unit","description":"Purchase of 10 servers and memory modules","language":"bilingual"}}"""


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def _parse_response(text: str) -> ContractExtract:
    t = text.strip()
    if t.startswith("```"):
        lines = t.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        t = "\n".join(lines)
    try:
        data: dict[str, Any] = json.loads(t)
    except (json.JSONDecodeError, ValueError) as e:
        return ContractExtract(error=f"Failed to parse: {e} (got: {text[:200]})")

    return ContractExtract(
        contract_number=data.get("contract_number") or None,
        title=data.get("title") or None,
        supplier_name=data.get("supplier_name") or None,
        supplier_contact=data.get("supplier_contact") or None,
        supplier_phone=data.get("supplier_phone") or None,
        supplier_id=None,
        start_date=data.get("start_date") or None,
        end_date=data.get("end_date") or None,
        total_amount=str(data.get("total_amount")) if data.get("total_amount") else None,
        payment_terms=data.get("payment_terms") or None,
        delivery_terms=data.get("delivery_terms") or None,
        items_text=data.get("items_text") or None,
        description=data.get("description") or None,
        language=data.get("language") or None,
    )


async def extract_contract(
    db: AsyncSession,
    actor: User | None,
    document_id: UUID,
    content: bytes,
    content_type: str,
    filename: str = "",
) -> ContractExtract:
    start = time.monotonic()
    try:
        result = await _dispatch(db, document_id, content, content_type, filename)
        # Auto-match supplier
        if result.supplier_name and not result.error:
            try:
                from app.models import Supplier

                matched = (
                    (
                        await db.execute(
                            select(Supplier).where(
                                Supplier.name.ilike(f"%{result.supplier_name[:20]}%"),
                                Supplier.is_deleted.is_(False),
                            )
                        )
                    )
                    .scalars()
                    .all()
                )
                if matched:
                    result.supplier_id = str(matched[0].id)
            except Exception:
                pass
    except Exception as e:
        result = ContractExtract(error=str(e))
    finally:
        elapsed = int((time.monotonic() - start) * 1000)
        try:
            db.add(
                AICallLog(
                    feature_code="contract_extract",
                    user_id=actor.id if actor else None,
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
    document_id: UUID,
    content: bytes,
    content_type: str,
    filename: str,
) -> ContractExtract:
    start_ms = time.monotonic()
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

    prompt = _build_prompt(filename)

    # Try stored OCR text first, then pypdf extraction
    text_content = ""
    try:
        from app.models import ContractDocument

        link = (
            await db.execute(
                select(ContractDocument).where(ContractDocument.document_id == document_id)
            )
        ).scalar_one_or_none()
        if link and link.ocr_text:
            text_content = link.ocr_text[:8000]
    except Exception:
        pass

    if not text_content:
        if content_type == "application/pdf" or filename.lower().endswith(".pdf"):
            try:
                import io

                from pypdf import PdfReader

                reader = PdfReader(io.BytesIO(content))
                for i, page in enumerate(reader.pages[:5]):
                    page_text = page.extract_text() or ""
                    if page_text.strip():
                        text_content += f"\n--- Page {i + 1} ---\n{page_text}"
                text_content = text_content[:8000]
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
        try:
            db.add(
                AICallLog(
                    feature_code="contract_extract",
                    model_name=model_row.name if model_row else None,
                    provider=model_row.provider if model_row else None,
                    prompt_tokens=len(prompt) // 4,
                    latency_ms=int((time.monotonic() - start_ms) * 1000),
                    status="error",
                    error=str(e),
                )
            )
            await db.flush()
        except Exception:
            pass
        return ContractExtract(error=f"AI call failed: {e}")

    choice = response.choices[0]
    text = choice.message.content or ""
    if not text:
        text = getattr(choice.message, "reasoning_content", None) or ""
    logger.info("contract_extract: response (%d chars) finish=%s", len(text), choice.finish_reason)

    try:
        db.add(
            AICallLog(
                feature_code="contract_extract",
                model_name=model_row.name,
                provider=model_row.provider,
                prompt_tokens=len(prompt) // 4,
                completion_tokens=len(text) // 4,
                latency_ms=int((time.monotonic() - start_ms) * 1000),
                status="success",
            )
        )
        await db.flush()
    except Exception:
        pass

    return _parse_response(text)
