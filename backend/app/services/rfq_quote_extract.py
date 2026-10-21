"""Read a supplier's scanned quotation into line items — without writing anything.

Deliberately a preview: recognising price off a stamped scan is unreliable enough
that the numbers must be looked at by a person before they reach the price history,
where an error is hard to unwind. Nothing here touches RFQQuote or SKUPriceRecord;
the caller shows the result and a human decides.

Unlike the invoice path this rasterises every page. A quotation is often "prices on
page one, terms and stamp on page two", and reading only the first page loses rows
silently.
"""

from __future__ import annotations

import base64
import json
import logging
import re
import time
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AICallLog, User
from app.services.ai import _call_litellm_vision, _get_routing
from app.services.system_params import system_params

logger = logging.getLogger(__name__)

FEATURE_CODE = "rfq_quote_extract"
DEFAULT_DPI = 250
DEFAULT_MAX_PAGES = 5

_QUOTE_PROMPT = """你在读一张供应商填写好的报价单扫描件。请只输出 JSON，不要解释。

要求：
1. 逐行读出价格表的每一行，字段固定为：
   line_no(行号，整数)、item_name(物料名称)、specification(规格/型号)、
   qty(数量)、unit_price(未税单价,数字)、tax_rate(税率,小数或百分数都按原文)、
   delivery_days(交期天数,整数或null)
2. 金额一律输出数字，不要带货币符号或千分位逗号；读不出就输出 null。
3. 表头若有供应商名称、币种、报价有效期，分别填 supplier_name / currency / valid_until。
4. 不要编造，看不清的字段填 null。
5. 每行给一个 confidence(0-1)，表示你对这一行数字的把握。

输出格式：
{"supplier_name": null, "currency": null, "valid_until": null,
 "lines": [{"line_no": 1, "item_name": "", "specification": "", "qty": 1,
            "unit_price": 0, "tax_rate": 0.13, "delivery_days": 7,
            "confidence": 0.8}],
 "confidence": 0.8}
"""


def _to_decimal(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value).replace(",", "").strip())
    except (InvalidOperation, ValueError):
        return None


def _pages(pdf_bytes: bytes, dpi: int, max_pages: int) -> tuple[list[bytes], int]:
    """Rasterise every page, up to a limit. Returns the images and the page count."""
    import fitz

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    total = doc.page_count
    images: list[bytes] = []
    for index in range(min(total, max_pages)):
        pix = doc.load_page(index).get_pixmap(dpi=dpi)
        images.append(pix.tobytes("jpeg"))
    return images, total


async def _read_page(db: AsyncSession, actor: User, image: bytes, content_type: str) -> dict:
    routing, model = await _get_routing(db, FEATURE_CODE)
    if model is None:
        raise RuntimeError("no_vision_model_configured")

    data_url = f"data:{content_type};base64,{base64.b64encode(image).decode()}"
    raw = ""
    async for chunk in _call_litellm_vision(
        model, _QUOTE_PROMPT, data_url, float(routing.temperature), int(routing.max_tokens)
    ):
        raw += chunk
    return _parse_json(raw)


def _parse_json(raw: str) -> dict:
    cleaned = raw.strip()
    cleaned = re.sub(r"^```(?:json)?|```$", "", cleaned, flags=re.MULTILINE).strip()
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start == -1 or end == -1:
        raise RuntimeError("vision_returned_non_json")
    return json.loads(cleaned[start : end + 1])


def _reconcile(lines: list[dict]) -> list[str]:
    """Arithmetic the form itself already promises: qty × price = line total."""
    warnings: list[str] = []
    for line in lines:
        qty, price = line.get("qty"), line.get("unit_price")
        total = line.get("line_total")
        if None in (qty, price) or total is None:
            continue
        try:
            expected = Decimal(str(qty)) * Decimal(str(price))
        except (InvalidOperation, ValueError):
            continue
        if abs(Decimal(str(total)) - expected) > Decimal("0.05"):
            warnings.append(
                f"line {line.get('line_no')}: total {total} != qty {qty} × price {price}"
            )
    return warnings


async def extract_rfq_quote(
    db: AsyncSession,
    actor: User,
    content: bytes,
    content_type: str,
    filename: str = "",
) -> dict:
    started = time.monotonic()
    error: str | None = None
    # Seed every field the response declares: a failure should still produce the
    # same shape, not a payload the schema has to paper over.
    payload: dict = {
        "supplier_name": None,
        "currency": None,
        "valid_until": None,
        "lines": [],
        "confidence": 0.0,
        "warnings": [],
        "pages_read": 0,
        "pages_total": 0,
    }

    try:
        is_pdf = content_type == "application/pdf" or content[:4] == b"%PDF"
        dpi = await system_params.get_int_or(db, "ai.rfq_quote_dpi", DEFAULT_DPI)
        max_pages = await system_params.get_int_or(db, "ai.rfq_quote_max_pages", DEFAULT_MAX_PAGES)

        if is_pdf:
            images, total_pages = _pages(content, dpi, max_pages)
            types = ["image/jpeg"] * len(images)
        elif content_type.startswith("image/"):
            images, total_pages, types = [content], 1, [content_type]
        else:
            raise RuntimeError(f"unsupported_content_type:{content_type}")

        if not images:
            raise RuntimeError("no_pages_rendered")

        merged: list[dict] = []
        supplier = currency = valid_until = None
        seen: set[Any] = set()
        confidences: list[float] = []

        for image, kind in zip(images, types, strict=True):
            page = await _read_page(db, actor, image, kind)
            supplier = supplier or page.get("supplier_name")
            currency = currency or page.get("currency")
            valid_until = valid_until or page.get("valid_until")
            if isinstance(page.get("confidence"), (int, float)):
                confidences.append(float(page["confidence"]))
            for raw_line in page.get("lines") or []:
                key = (raw_line.get("line_no"), (raw_line.get("item_name") or "").strip())
                if key in seen:
                    continue
                seen.add(key)
                merged.append(
                    {
                        "line_no": raw_line.get("line_no"),
                        "item_name": (raw_line.get("item_name") or "").strip() or None,
                        "specification": (raw_line.get("specification") or "").strip() or None,
                        "qty": _to_decimal(raw_line.get("qty")),
                        "unit_price": _to_decimal(raw_line.get("unit_price")),
                        "tax_rate": _to_decimal(raw_line.get("tax_rate")),
                        "delivery_days": raw_line.get("delivery_days"),
                        "confidence": float(
                            raw_line.get("confidence") or page.get("confidence") or 0.0
                        ),
                    }
                )

        warnings = _reconcile(page.get("lines") or []) if images else []
        if total_pages > len(images):
            warnings.append(f"only the first {len(images)} of {total_pages} pages were read")

        payload = {
            "supplier_name": supplier,
            "currency": currency,
            "valid_until": valid_until,
            "lines": merged,
            "confidence": min(confidences) if confidences else 0.0,
            "warnings": warnings,
            "pages_read": len(images),
            "pages_total": total_pages,
        }
    except Exception as exc:  # the caller renders `error`; never 500 on a bad scan
        error = str(exc)
        logger.warning("rfq quote extract failed: %s", exc)
    finally:
        try:
            db.add(
                AICallLog(
                    feature_code=FEATURE_CODE,
                    user_id=actor.id,
                    model_name=None,
                    provider=None,
                    prompt_tokens=0,
                    completion_tokens=0,
                    latency_ms=int((time.monotonic() - started) * 1000),
                    status="success" if error is None else "error",
                    error=error,
                )
            )
            await db.commit()
        except Exception:
            logger.debug("rfq quote extract: could not record the AI call", exc_info=True)

    payload["error"] = error
    return payload
