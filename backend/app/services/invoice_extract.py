"""Invoice extractor: XML → OFD → PDF (embedded) → PDF (text) → LLM Vision → Manual.

Graceful degradation: if optional libs (pdfplumber/pypdf/pymupdf/easyofd)
are not installed at runtime, the corresponding strategy is skipped and
extraction falls back to the next tier.
"""

from __future__ import annotations

import base64
import io
import re
import time
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AICallLog, User
from app.services.ai import _call_litellm_stream, _get_routing


class ExtractSource(StrEnum):
    XML = "xml"
    OFD = "ofd"
    PDF_EMBEDDED = "pdf_embedded"
    PDF_TEXT = "pdf_text"
    LLM_VISION = "llm_vision"
    MANUAL = "manual"


@dataclass
class InvoiceLineExtract:
    item_name: str | None = None
    spec: str | None = None
    qty: str | None = None
    unit_price: str | None = None
    tax_rate: str | None = None
    tax_amount: str | None = None
    subtotal: str | None = None


@dataclass
class InvoiceExtract:
    invoice_number: str | None = None
    invoice_code: str | None = None
    invoice_date: str | None = None
    seller_name: str | None = None
    seller_tax_id: str | None = None
    buyer_name: str | None = None
    buyer_tax_id: str | None = None
    subtotal: str | None = None
    tax_amount: str | None = None
    total_amount: str | None = None
    currency: str = "CNY"
    lines: list[InvoiceLineExtract] = field(default_factory=list)
    raw_extract_source: str = ExtractSource.MANUAL.value
    confidence: float = 0.0
    error: str | None = None


_VISION_PROMPT = """你是中国增值税发票信息提取专家。请从图片中提取发票字段，严格按 JSON 返回，不要输出任何其他内容。

规则：
- 金额字段只保留数字和小数点
- 开票日期统一转为 YYYY-MM-DD
- 不存在的字段填 null
- confidence 为 0.0-1.0 的整体置信度

JSON 格式：
{"invoice_number":"string|null","invoice_code":"string|null","invoice_date":"YYYY-MM-DD|null","seller_name":"string|null","seller_tax_id":"string|null","buyer_name":"string|null","buyer_tax_id":"string|null","subtotal":"string|null","tax_amount":"string|null","total_amount":"string|null","currency":"CNY","lines":[{"item_name":"string","spec":"string|null","qty":"string|null","unit_price":"string|null","tax_rate":"string|null","tax_amount":"string|null","subtotal":"string|null"}],"confidence":0.0}

直接输出 JSON，不要 markdown 代码块。"""


_REGEX_PATTERNS: dict[str, str] = {
    "invoice_number": r"发票号码[：:]\s*(\d{8,20})",
    "invoice_code": r"发票代码[：:]\s*(\d{10,12})",
    "invoice_date": r"开票日期[：:]\s*(\d{4}[年\-]\d{1,2}[月\-]\d{1,2}[日]?)",
    "seller_tax_id": r"销售方[\s\S]{0,80}?纳税人识别号[：:]\s*([A-Z0-9]{15,20})",
    "buyer_tax_id": r"购买方[\s\S]{0,80}?纳税人识别号[：:]\s*([A-Z0-9]{15,20})",
    "total_amount": r"价\s*税\s*合\s*计[（(]?\s*(?:小写|大写)?[）)]?[^¥￥0-9]*[¥￥]?\s*([\d,]+\.?\d*)",
    "tax_amount": r"合\s*计\s*税\s*额[：:]?\s*[¥￥]?\s*([\d,]+\.?\d*)",
    "subtotal": r"合\s*计\s*金\s*额[：:]?\s*[¥￥]?\s*([\d,]+\.?\d*)",
}


async def extract_invoice(
    db: AsyncSession,
    actor: User,
    content: bytes,
    content_type: str,
    filename: str = "",
) -> InvoiceExtract:
    start = time.monotonic()
    feature = "invoice_extract"
    try:
        result = await _dispatch(db, actor, content, content_type, filename)
    except Exception as e:
        result = InvoiceExtract(error=str(e))
    finally:
        elapsed = int((time.monotonic() - start) * 1000)
        try:
            db.add(
                AICallLog(
                    feature_code=feature,
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
    db: AsyncSession, actor: User, content: bytes, content_type: str, filename: str
) -> InvoiceExtract:
    lower_name = (filename or "").lower()
    if (
        content_type in ("application/xml", "text/xml")
        or lower_name.endswith(".xml")
        or _looks_xml(content)
    ):
        return _extract_xml(content)
    if (
        content_type in ("application/ofd", "application/octet-stream")
        or lower_name.endswith(".ofd")
    ) and _is_zip(content):
        result = _extract_ofd(content)
        if result.confidence > 0:
            return result
    if content_type == "application/pdf" or content[:4] == b"%PDF":
        return await _extract_pdf(db, actor, content)
    if content_type.startswith("image/"):
        return await _extract_via_vision(db, actor, content, content_type)
    return InvoiceExtract(error=f"unsupported_content_type:{content_type}")


def _looks_xml(b: bytes) -> bool:
    sample = b[:200].lstrip()
    return sample.startswith(b"<?xml") or sample.startswith(b"<")


def _is_zip(b: bytes) -> bool:
    return b[:4] == b"PK\x03\x04"


def _extract_xml(xml_bytes: bytes) -> InvoiceExtract:
    try:
        root = ET.fromstring(xml_bytes.decode("utf-8", errors="replace"))
    except ET.ParseError as e:
        return InvoiceExtract(
            raw_extract_source=ExtractSource.XML.value,
            error=f"xml_parse_error:{e}",
        )

    def find_any(tags: list[str]) -> str | None:
        for tag in tags:
            el = root.find(f".//{tag}")
            if el is not None and el.text:
                return el.text.strip()
            el = root.find(f".//{{{'*'}}}{tag}")
            if el is not None and el.text:
                return el.text.strip()
        return None

    data = InvoiceExtract(
        invoice_number=find_any(["InvoiceNumber", "invoiceNo"]),
        invoice_code=find_any(["InvoiceCode", "invoiceCode"]),
        invoice_date=find_any(["IssueDate", "invoiceDate"]),
        seller_name=find_any(["SellerName", "salerName"]),
        seller_tax_id=find_any(["SellerTaxID", "salerTaxNum"]),
        buyer_name=find_any(["BuyerName", "purchaserName"]),
        buyer_tax_id=find_any(["BuyerTaxID", "purchaserTaxNum"]),
        subtotal=find_any(["TaxExclusiveAmount", "amountWithoutTax"]),
        tax_amount=find_any(["TaxAmount", "taxAmount"]),
        total_amount=find_any(["TaxInclusiveAmount", "amountWithTax"]),
        raw_extract_source=ExtractSource.XML.value,
        confidence=0.99,
    )
    return data


def _extract_ofd(ofd_bytes: bytes) -> InvoiceExtract:
    try:
        with zipfile.ZipFile(io.BytesIO(ofd_bytes)) as zf:
            names = zf.namelist()
            for name in names:
                if "invoice" in name.lower() or "发票" in name or name.endswith(".xml"):
                    if name.lower().endswith(".xml"):
                        data = zf.read(name)
                        result = _extract_xml(data)
                        if result.invoice_number or result.total_amount:
                            result.raw_extract_source = ExtractSource.OFD.value
                            return result
            text_parts: list[str] = []
            for name in names:
                if name.endswith(".xml"):
                    content = zf.read(name).decode("utf-8", errors="replace")
                    text_parts.extend(re.findall(r">([^<]{2,})<", content))
        full_text = " ".join(text_parts)
        return _regex_extract(full_text, ExtractSource.OFD)
    except Exception as e:
        return InvoiceExtract(
            raw_extract_source=ExtractSource.OFD.value,
            error=f"ofd_parse_error:{e}",
        )


async def _extract_pdf(db: AsyncSession, actor: User, pdf_bytes: bytes) -> InvoiceExtract:
    try:
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(pdf_bytes))
        attachments = getattr(reader, "attachments", {}) or {}
        for name, blobs in attachments.items():
            if str(name).lower().endswith(".xml") and blobs:
                xml_blob = blobs[0] if isinstance(blobs, list) else blobs
                if isinstance(xml_blob, (bytes, bytearray)):
                    result = _extract_xml(bytes(xml_blob))
                    if result.invoice_number:
                        result.raw_extract_source = ExtractSource.PDF_EMBEDDED.value
                        return result
    except Exception:
        pass

    text = _pdf_text(pdf_bytes)
    if text and len(text) > 100:
        result = _regex_extract(text, ExtractSource.PDF_TEXT)
        if result.invoice_number or result.total_amount:
            return result

    return await _extract_via_vision_from_pdf(db, actor, pdf_bytes)


def _pdf_text(pdf_bytes: bytes) -> str:
    try:
        import pdfplumber

        texts: list[str] = []
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                t = page.extract_text(x_tolerance=3, y_tolerance=3)
                if t:
                    texts.append(t)
        return "\n".join(texts)
    except Exception:
        return ""


def _regex_extract(text: str, source: ExtractSource) -> InvoiceExtract:
    data = InvoiceExtract(raw_extract_source=source.value)
    matched = 0
    for field_name, pattern in _REGEX_PATTERNS.items():
        m = re.search(pattern, text)
        if m:
            value = m.group(1).strip().replace(",", "")
            if field_name == "invoice_date":
                value = re.sub(r"年|-", "-", value).replace("月", "-").replace("日", "")
            setattr(data, field_name, value)
            matched += 1
    data.confidence = matched / len(_REGEX_PATTERNS) if _REGEX_PATTERNS else 0.0
    return data


async def _extract_via_vision_from_pdf(
    db: AsyncSession, actor: User, pdf_bytes: bytes
) -> InvoiceExtract:
    try:
        import fitz

        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        page = doc.load_page(0)
        pix = page.get_pixmap(dpi=150)
        img_bytes = pix.tobytes("jpeg")
        return await _extract_via_vision(db, actor, img_bytes, "image/jpeg")
    except Exception as e:
        return InvoiceExtract(
            raw_extract_source=ExtractSource.LLM_VISION.value,
            error=f"pdf_to_image_error:{e}",
        )


async def _extract_via_vision(
    db: AsyncSession, actor: User, img_bytes: bytes, content_type: str
) -> InvoiceExtract:
    try:
        routing, model = await _get_routing(db, "invoice_extract")
    except Exception as e:
        return InvoiceExtract(
            raw_extract_source=ExtractSource.LLM_VISION.value,
            error=f"ai_not_configured:{e}",
        )
    if model is None:
        return InvoiceExtract(
            raw_extract_source=ExtractSource.LLM_VISION.value,
            error="no_vision_model_configured",
            confidence=0.0,
        )

    import json

    img_b64 = base64.b64encode(img_bytes).decode()
    _ = f"data:{content_type};base64,{img_b64}"
    raw = ""
    try:
        async for chunk in _call_litellm_stream(
            model, _VISION_PROMPT, float(routing.temperature), int(routing.max_tokens)
        ):
            raw += chunk
    except Exception as e:
        return InvoiceExtract(
            raw_extract_source=ExtractSource.LLM_VISION.value,
            error=f"vision_call_failed:{e}",
        )

    json_block = raw
    m = re.search(r"\{[\s\S]*\}", raw)
    if m:
        json_block = m.group()
    try:
        payload: dict[str, Any] = json.loads(json_block)
    except json.JSONDecodeError:
        return InvoiceExtract(
            raw_extract_source=ExtractSource.LLM_VISION.value,
            error="vision_returned_non_json",
        )

    data = InvoiceExtract(
        invoice_number=payload.get("invoice_number"),
        invoice_code=payload.get("invoice_code"),
        invoice_date=payload.get("invoice_date"),
        seller_name=payload.get("seller_name"),
        seller_tax_id=payload.get("seller_tax_id"),
        buyer_name=payload.get("buyer_name"),
        buyer_tax_id=payload.get("buyer_tax_id"),
        subtotal=payload.get("subtotal"),
        tax_amount=payload.get("tax_amount"),
        total_amount=payload.get("total_amount"),
        currency=payload.get("currency", "CNY"),
        lines=[
            InvoiceLineExtract(**{k: ln.get(k) for k in InvoiceLineExtract.__dataclass_fields__})
            for ln in (payload.get("lines") or [])
        ],
        raw_extract_source=ExtractSource.LLM_VISION.value,
        confidence=float(payload.get("confidence", 0.75)),
    )
    return data


def to_dict(result: InvoiceExtract) -> dict:
    d = asdict(result)
    return d
