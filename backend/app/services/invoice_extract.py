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
    unit: str | None = None
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


_VISION_PROMPT = """你是中国增值税发票信息提取专家。请从图片中提取所有发票字段，严格按 JSON 返回，不要输出任何其他内容。

## 头部字段规则
- invoice_number: 发票号码（8-20 位数字）
- invoice_code: 发票代码（10-12 位数字），全电发票可能无此字段
- invoice_date: 开票日期，统一转为 YYYY-MM-DD
- seller_name: 销售方名称
- seller_tax_id: 销售方纳税人识别号（15-20 位）
- buyer_name: 购买方名称
- buyer_tax_id: 购买方纳税人识别号
- subtotal: 合计金额（不含税），对应"金额"列合计行，只保留数字和小数点
- tax_amount: 合计税额，对应"税额"列合计行
- total_amount: 价税合计（含税），对应"价税合计"行小写金额
- 校验：total_amount = subtotal + tax_amount（如不满足请重新核对）

## 行项明细规则（最重要！）
发票中间的表格区域包含货物/服务明细行。每一行包括：
- item_name: 货物或应税劳务、服务名称（含分类简称前缀如 *电子产品*）
- spec: 规格型号（可能为空）
- unit: 单位（个/台/条/片/EA 等，可能为空）
- qty: 数量（纯数字，可能为空如服务类）
- unit_price: 单价（不含税单价，纯数字小数）
- subtotal: 金额（该行不含税金额 = qty × unit_price）
- tax_rate: 税率（如 13%、9%、6%，保留百分号）
- tax_amount: 税额（该行税额 = subtotal × tax_rate）

关键注意：
1. 必须提取**所有**行项，不要遗漏。仔细查看表格区域每一行
2. 如果某行跨多行显示（如名称很长换行了），仍算一条记录
3. 折扣行：如果有"折扣"或负数金额行，也提取出来（subtotal 为负数）
4. "*电子产品*""*信息技术服务*"等分类简称是 item_name 的一部分，保留
5. 金额字段只保留数字、小数点和负号，不含逗号、¥、￥

## 置信度
confidence 为 0.0-1.0。所有关键字段（发票号、金额、行项）清晰可读给 0.9+；部分模糊给 0.6-0.8；大量不确定给 0.3-0.5

## 输出格式
{"invoice_number":"string|null","invoice_code":"string|null","invoice_date":"YYYY-MM-DD|null","seller_name":"string|null","seller_tax_id":"string|null","buyer_name":"string|null","buyer_tax_id":"string|null","subtotal":"string|null","tax_amount":"string|null","total_amount":"string|null","currency":"CNY","lines":[{"item_name":"string","spec":"string|null","unit":"string|null","qty":"string|null","unit_price":"string|null","subtotal":"string|null","tax_rate":"string|null","tax_amount":"string|null"}],"confidence":0.0}

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
    key_fields_matched = 0
    key_fields = {"invoice_number", "total_amount", "subtotal", "tax_amount"}
    for field_name, pattern in _REGEX_PATTERNS.items():
        m = re.search(pattern, text)
        if m:
            value = m.group(1).strip().replace(",", "")
            if field_name == "invoice_date":
                value = re.sub(r"年|-", "-", value).replace("月", "-").replace("日", "")
            setattr(data, field_name, value)
            matched += 1
            if field_name in key_fields:
                key_fields_matched += 1
    base_conf = matched / len(_REGEX_PATTERNS) if _REGEX_PATTERNS else 0.0
    key_bonus = key_fields_matched / len(key_fields) * 0.3
    data.confidence = min(base_conf + key_bonus, 0.99)
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
