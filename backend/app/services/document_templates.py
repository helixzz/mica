from __future__ import annotations

import io
import json
import logging
import re
import zipfile
from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.crypto import decrypt
from app.core.litellm_helpers import resolve_litellm_model
from app.core.money import fmt_amount
from app.models import (
    AIFeatureRouting,
    AIModel,
    Company,
    Contract,
    Document,
    DocumentTemplate,
    PaymentSchedule,
    POContractLink,
    PurchaseOrder,
    Supplier,
    User,
)

logger = logging.getLogger(__name__)

PLACEHOLDER_RE = re.compile(r"\[([^\]\n\r]{1,200})\]")

DETERMINISTIC_RESOLVERS: dict[re.Pattern[str], str] = {
    re.compile(r"^PO[_\-\s]?(编号|号|number)$", re.IGNORECASE): "po.po_number",
    re.compile(r"^采购订单[_\-\s]?(编号|号)$"): "po.po_number",
    re.compile(r"^合同[_\-\s]?(编号|号|number)$", re.IGNORECASE): "contract.contract_number",
    re.compile(r"^供应商(名称|名字|name)?$", re.IGNORECASE): "supplier.name",
    re.compile(
        r"^(收款(方|单位)?|payee)[_\-\s]?(公司)?(全(称|名)?|名称|name)?$",
        re.IGNORECASE,
    ): "supplier.payee_name_effective",
    re.compile(
        r"^((收款(方|单位)?|payee)[_\-\s]?)?(银行[_\-\s]?)?开户行$",
        re.IGNORECASE,
    ): "supplier.payee_bank",
    re.compile(
        r"^((收款(方|单位)?)[_\-\s]?)?银行[_\-\s]?(账号|账户|account)$",
        re.IGNORECASE,
    ): "supplier.payee_bank_account",
    re.compile(r"^银行账号$"): "supplier.payee_bank_account",
    re.compile(r"^(税号|tax[_\-\s]?number)$", re.IGNORECASE): "supplier.tax_number",
    re.compile(r"^付款期次(说明)?$"): "schedule.label_with_installment",
    re.compile(r"^分期[_\-\s]?(编号|号|no)$", re.IGNORECASE): "schedule.installment_no",
    re.compile(r"^付款金额$"): "schedule.effective_amount",
    re.compile(r"^(付款方|采购方|采购)[_\-\s]?(公司)?(全(称|名)?|名称)?$"): "company.name",
    # ``company.short_name`` is an explicitly maintained column; when it is empty the
    # context falls back to the full legal name (see build_context).
    re.compile(
        r"^(付款方|采购方|采购)[_\-\s]?(公司)?(简称|short[_\-\s]?name)$"
    ): "company.short_name",
    re.compile(r"^采购公司名的四字简称$"): "company.short_name",
    re.compile(r"^(本单据|付款单据)?[_\-\s]?生成日期$"): "today.iso",
    re.compile(r"^生成日期(YYYY)?[-/\.年]?MM?[-/\.月]?DD?[日]?$"): "today.iso",
    re.compile(r"^(生成付款单据的|当前|制单)?用户[_\-\s]?(全名|姓名|name)$"): "actor.display_name",
    re.compile(r"(付款的?)?(极简)?概括"): "payment.narrative_short",
    re.compile(r"付款(的?)性质"): "payment.narrative_short",
    re.compile(r"采购付款的?性质"): "payment.narrative_short",
}


def detect_ooxml_kind(content_bytes: bytes) -> str | None:
    """Return ``"docx"``, ``"xlsx"`` or ``None`` by inspecting the package members.

    Trying ``python-docx`` first and catching its failure works, but for an .xlsx
    template it raises on every single generation and logs a full ERROR traceback,
    which buries real problems in the log. Deciding up front is both quieter and
    cheaper (the wrong parser is never started).
    """
    try:
        with zipfile.ZipFile(io.BytesIO(content_bytes)) as archive:
            names = set(archive.namelist())
    except (zipfile.BadZipFile, OSError):
        return None
    if "word/document.xml" in names:
        return "docx"
    if any(name.startswith("xl/") for name in names):
        return "xlsx"
    return None


def extract_placeholders(content_bytes: bytes | None, filename_template: str) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()

    def _add(text: str) -> None:
        for match in PLACEHOLDER_RE.finditer(text):
            description = match.group(1).strip()
            if description and description not in seen:
                seen.add(description)
                found.append(description)

    _add(filename_template)

    if content_bytes:
        kind = detect_ooxml_kind(content_bytes)

        if kind == "docx":
            try:
                from docx import Document as DocxDocument

                doc = DocxDocument(io.BytesIO(content_bytes))
                for para in doc.paragraphs:
                    _add(para.text)
                for table in doc.tables:
                    for row in table.rows:
                        for cell in row.cells:
                            _add(cell.text)
            except Exception:
                logger.exception("template: failed to parse docx for placeholder extraction")

        elif kind == "xlsx":
            try:
                from openpyxl import load_workbook

                workbook = load_workbook(io.BytesIO(content_bytes))
                for sheet in workbook.worksheets:
                    for row in sheet.iter_rows():
                        for cell in row:
                            if isinstance(cell.value, str):
                                _add(cell.value)
            except Exception:
                logger.exception("template: failed to parse xlsx for placeholder extraction")

        else:
            logger.debug(
                "template: content is neither a docx nor an xlsx package; "
                "only filename placeholders are available"
            )

    return found


def _as_date_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def build_context(
    po: PurchaseOrder,
    contract: Contract,
    supplier: Supplier,
    schedule: PaymentSchedule,
    *,
    actor: User | None = None,
    company: Company | None = None,
    payment_narrative: str | None = None,
) -> dict[str, Any]:
    payee_name = supplier.payee_name or supplier.name
    amount = (
        schedule.actual_amount if schedule.actual_amount is not None else schedule.planned_amount
    )
    date_value = schedule.actual_date or schedule.planned_date
    today = datetime.now(UTC).date()

    company_name = ""
    company_short = ""
    if company is not None:
        company_name = company.name_zh or company.name_en or ""
        # Never derive the abbreviation by slicing the name. Distinct payers share a
        # prefix ("上海佳期私募基金管理有限公司" / "上海佳期数据科技有限公司" both
        # truncated to "上海佳期", producing indistinguishable payment-form filenames)
        # and English names degrade to gibberish ("JQ Investments (HK) Limited" ->
        # "JQ I"). Fall back to the full name so an unset abbreviation is verbose
        # rather than ambiguous.
        company_short = company.short_name or company_name

    actor_name = ""
    if actor is not None:
        actor_name = actor.display_name or actor.username or ""

    return {
        "po": {
            "po_number": po.po_number,
            "currency": po.currency,
            "total_amount": fmt_amount(po.total_amount, po.currency),
            "status": po.status,
        },
        "contract": {
            "contract_number": contract.contract_number,
            "title": contract.title,
            "total_amount": fmt_amount(contract.total_amount, contract.currency),
            "currency": contract.currency,
            "signed_date": _as_date_str(contract.signed_date),
            "effective_date": _as_date_str(contract.effective_date),
            "expiry_date": _as_date_str(contract.expiry_date),
            "status": contract.status,
        },
        "supplier": {
            "name": supplier.name,
            "code": supplier.code,
            "tax_number": supplier.tax_number or "",
            "contact_name": supplier.contact_name or "",
            "contact_phone": supplier.contact_phone or "",
            "contact_email": supplier.contact_email or "",
            "payee_name": supplier.payee_name or "",
            "payee_name_effective": payee_name,
            "payee_bank": supplier.payee_bank or "",
            "payee_bank_account": supplier.payee_bank_account or "",
        },
        "schedule": {
            "installment_no": schedule.installment_no,
            "label": schedule.label,
            "label_with_installment": f"第 {schedule.installment_no} 期 · {schedule.label}",
            "planned_amount": fmt_amount(schedule.planned_amount, po.currency),
            "planned_date": _as_date_str(schedule.planned_date),
            "actual_amount": fmt_amount(schedule.actual_amount, po.currency)
            if schedule.actual_amount
            else "",
            "actual_date": _as_date_str(schedule.actual_date),
            "status": schedule.status,
            "effective_amount": fmt_amount(amount, po.currency),
            "effective_amount_raw": str(amount),
            "effective_date": _as_date_str(date_value),
            "trigger_type": schedule.trigger_type,
            "trigger_description": schedule.trigger_description or "",
        },
        "company": {
            "name": company_name,
            "short_name": company_short,
        },
        "actor": {
            "display_name": actor_name,
        },
        "today": {
            "iso": today.isoformat(),
            "yyyymmdd": today.strftime("%Y%m%d"),
            "yyyy_mm_dd_cn": today.strftime("%Y年%m月%d日"),
        },
        "payment": {
            "narrative_short": (payment_narrative or schedule.label or "").strip(),
        },
    }


def _lookup_context(context: dict[str, Any], path: str) -> str | None:
    cur: Any = context
    for key in path.split("."):
        if not isinstance(cur, dict) or key not in cur:
            return None
        cur = cur[key]
    return None if cur is None else str(cur)


def resolve_placeholder_deterministic(description: str, context: dict[str, Any]) -> str | None:
    for pattern, path in DETERMINISTIC_RESOLVERS.items():
        if pattern.search(description):
            value = _lookup_context(context, path)
            if value is not None:
                return value
    return None


async def _resolve_document_generation_model(db: AsyncSession) -> AIModel | None:
    routing = (
        await db.execute(
            select(AIFeatureRouting).where(AIFeatureRouting.feature_code == "document_generation")
        )
    ).scalar_one_or_none()
    if routing is None or not routing.enabled or not routing.primary_model_id:
        return None
    return (
        await db.execute(select(AIModel).where(AIModel.id == routing.primary_model_id))
    ).scalar_one_or_none()


async def resolve_placeholders_with_llm(
    db: AsyncSession,
    placeholders: list[str],
    context: dict[str, Any],
) -> dict[str, str]:
    if not placeholders:
        return {}

    model = await _resolve_document_generation_model(db)
    if model is None:
        return {}

    try:
        from litellm import acompletion
    except ImportError:
        return {}

    prompt = _build_llm_prompt(placeholders, context)
    kwargs: dict[str, Any] = {
        "model": resolve_litellm_model(model.provider, model.model_string),
        "messages": [
            {
                "role": "system",
                "content": "You are a precise data-extraction assistant. "
                "Given structured business data and a list of placeholder descriptions, "
                "return ONLY a valid JSON object mapping each exact placeholder text to "
                "its extracted value. No prose, no markdown fences.",
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.0,
        "max_tokens": 1200,
    }
    api_key = decrypt(model.api_key_encrypted) if model.api_key_encrypted else None
    if api_key:
        kwargs["api_key"] = api_key
    if model.api_base:
        kwargs["api_base"] = model.api_base

    try:
        resp = await acompletion(**kwargs)
        raw = resp.choices[0].message.content or "{}"
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.strip("`").lstrip("json").strip()
        data = json.loads(raw)
        if not isinstance(data, dict):
            return {}
        return {str(k): str(v) if v is not None else "" for k, v in data.items()}
    except Exception:
        logger.exception("template: LLM placeholder resolution failed")
        return {}


def _build_llm_prompt(placeholders: list[str], context: dict[str, Any]) -> str:
    return (
        "Here is structured business data about a purchase order, a contract, "
        "a supplier, and a single payment schedule installment:\n\n"
        f"{json.dumps(context, ensure_ascii=False, indent=2, default=str)}\n\n"
        "For each of the following placeholders, produce the best-fitting extracted "
        "or formatted string value. If a placeholder description implies a date format "
        '(e.g. "YYYY-MM-DD" or "YYYY年MM月DD日"), format accordingly. '
        'If it implies an amount in words (大写), convert the number to Chinese "大写金额" '
        '(e.g. "肆佰伍拾万元整"). If you cannot find a value, return an empty string.\n\n'
        "Return ONLY a single JSON object, where keys are the EXACT placeholder texts "
        "as given, and values are the resolved strings.\n\n"
        "Placeholders:\n" + "\n".join(f"- {p}" for p in placeholders)
    )


_DIGIT_CN = "零壹贰叁肆伍陆柒捌玖"
_UNIT_CN = ["", "拾", "佰", "仟"]
_BIG_UNIT_CN = ["", "万", "亿", "兆"]


def cn_amount_upper(amount: Decimal | float | int | str | None) -> str:
    if amount is None or amount == "":
        return ""
    try:
        d = Decimal(str(amount)).quantize(Decimal("0.01"))
    except Exception:
        return str(amount)
    yuan_part = int(d)
    cents = int((d - Decimal(yuan_part)) * 100)

    def _convert_int(n: int) -> str:
        if n == 0:
            return "零"
        parts: list[str] = []
        big = 0
        while n > 0:
            section = n % 10000
            n //= 10000
            if section == 0:
                parts.insert(0, "")
                big += 1
                continue
            section_str = ""
            prev_zero = False
            for i in range(4):
                digit = section % 10
                section //= 10
                if digit == 0:
                    if not prev_zero and section_str:
                        section_str = "零" + section_str
                    prev_zero = True
                else:
                    section_str = _DIGIT_CN[digit] + _UNIT_CN[i] + section_str
                    prev_zero = False
            section_str = section_str.rstrip("零")
            parts.insert(0, section_str + _BIG_UNIT_CN[big])
            big += 1
        return "".join(p for p in parts if p).lstrip("零") or "零"

    yuan_str = _convert_int(yuan_part) + "元"
    if cents == 0:
        return yuan_str + "整"
    jiao = cents // 10
    fen = cents % 10
    tail = ""
    if jiao:
        tail += _DIGIT_CN[jiao] + "角"
    if fen:
        tail += _DIGIT_CN[fen] + "分"
    else:
        tail += "整" if jiao else "零"
    return yuan_str + tail


DATE_FORMAT_RE = re.compile(
    r"(YYYY|YY)[-/\.\s年]*MM[-/\.\s月]*DD[日]?|(YYYY|YY)MM?DD?",
    re.IGNORECASE,
)


def _format_schedule_date(fmt: str, y: str, m: str, d: str) -> str:
    out = fmt
    out = out.replace("YYYY", y).replace("yyyy", y)
    out = out.replace("YY", y[-2:]).replace("yy", y[-2:])
    out = out.replace("MM", m).replace("mm", m)
    out = out.replace("DD", d).replace("dd", d)
    return out


def _enrich_with_computed(
    description: str, context: dict[str, Any], current: str | None
) -> str | None:
    if current:
        return current
    if "大写" in description or "upper" in description.lower():
        amount = context["schedule"]["effective_amount_raw"]
        return cn_amount_upper(amount)
    if "数字" in description and ("金额" in description or "amount" in description.lower()):
        return context["schedule"]["effective_amount"]
    date_match = DATE_FORMAT_RE.search(description)
    if date_match:
        today_markers = ("生成", "今天", "当前", "本单据", "today", "now")
        if any(marker in description for marker in today_markers):
            raw_date = context.get("today", {}).get("iso", "")
        else:
            raw_date = context["schedule"]["effective_date"]
        if not raw_date or raw_date == "None":
            return ""
        try:
            y, m, d = raw_date.split("-")
        except ValueError:
            return raw_date
        return _format_schedule_date(date_match.group(0), y, m, d)
    return None


_NL_HINT_SUBSTRINGS = ("请", "根据", "基于", "写成", "改写", "改成", "描述", "说明", "生成", "总结")
_NL_PUNCT_CHARS = "，。；：？！（）、 "
_NL_MIN_LENGTH = 12


def _looks_like_natural_language(description: str) -> bool:
    """Return True if the placeholder is an instruction/description, not a short canonical key."""
    text = description.strip()
    if len(text) >= _NL_MIN_LENGTH:
        return True
    for token in _NL_HINT_SUBSTRINGS:
        if token in text:
            return True
    for ch in _NL_PUNCT_CHARS:
        if ch in text:
            return True
    return False


_SENSITIVE_KEYWORDS = ("银行账号", "账号", "开户行", "税号", "tax", "bank", "account")


def _is_sensitive_description(description: str) -> bool:
    """Sensitive placeholders (bank account / tax id) must never be filled by the LLM."""
    lower = description.lower()
    return any(tok.lower() in lower for tok in _SENSITIVE_KEYWORDS)


async def resolve_all_placeholders(
    db: AsyncSession,
    placeholders: list[str],
    context: dict[str, Any],
    *,
    filename_placeholders: set[str] | None = None,
) -> dict[str, str]:
    """Resolve placeholders by routing class.

    Routing contract (tests enforce this):
    - sensitive placeholders (bank / tax) → deterministic only
    - short canonical placeholders → deterministic; LLM as fallback if no hit
    - natural-language placeholders → LLM is primary; deterministic is fallback
    - filename placeholders pass through the same routing but their final value
      is sanitized for filesystem safety by render_filename()
    - computed enrichment (dates / 大写金额) runs last and overrides everything
    """

    _ = filename_placeholders  # accepted for API compatibility; sanitization is in render_filename
    resolved: dict[str, str] = {}
    deterministic_hits: dict[str, str] = {}
    llm_candidates: list[str] = []

    for p in placeholders:
        value = resolve_placeholder_deterministic(p, context)
        if value is not None:
            deterministic_hits[p] = value

        if _is_sensitive_description(p):
            resolved[p] = value if value is not None else ""
            continue

        if _looks_like_natural_language(p):
            llm_candidates.append(p)
            continue

        if value is not None:
            resolved[p] = value
        else:
            llm_candidates.append(p)

    if llm_candidates:
        llm_results = await resolve_placeholders_with_llm(db, llm_candidates, context)
        for p in llm_candidates:
            llm_value = llm_results.get(p, "")
            if llm_value:
                resolved[p] = llm_value
            else:
                resolved[p] = deterministic_hits.get(p, "")

    for p in placeholders:
        enriched = _enrich_with_computed(p, context, None)
        if enriched is not None:
            resolved[p] = enriched

    return resolved


def render_filename(filename_template: str, mapping: dict[str, str]) -> str:
    def _sub(match: re.Match[str]) -> str:
        return mapping.get(match.group(1).strip(), "")

    filename = PLACEHOLDER_RE.sub(_sub, filename_template)
    sanitized = re.sub(r"[<>:\"/\\|?*\x00-\x1f]+", "_", filename)
    return sanitized.strip()


def substitute_docx(content_bytes: bytes, mapping: dict[str, str]) -> bytes:
    from docx import Document as DocxDocument

    doc = DocxDocument(io.BytesIO(content_bytes))

    def _replace_in_paragraph(para) -> None:
        full_text = "".join(run.text for run in para.runs)
        if not PLACEHOLDER_RE.search(full_text):
            return
        new_text = PLACEHOLDER_RE.sub(lambda m: mapping.get(m.group(1).strip(), ""), full_text)
        if para.runs:
            para.runs[0].text = new_text
            for run in para.runs[1:]:
                run.text = ""
        else:
            para.text = new_text

    for para in doc.paragraphs:
        _replace_in_paragraph(para)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for para in cell.paragraphs:
                    _replace_in_paragraph(para)

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


# A row that carries this placeholder is treated as the repeating template row for
# a line-item table; everything in it is copied once per entry.
_XLSX_REPEAT_ANCHOR = "line_no"


def _offset_formula(formula: str, from_row: int, to_row: int) -> str:
    """Shift the row numbers inside a formula, keeping columns as they are."""
    if from_row == to_row:
        return formula
    return re.sub(
        rf"([A-Z]{{1,3}})\$?{from_row}(?![0-9])",
        lambda m: m.group(0).replace(str(from_row), str(to_row)),
        formula,
    )


def _resize_block_keeping_merges(sheet, at_row: int, delta: int) -> None:
    """Insert or delete rows without losing the merged ranges below them.

    openpyxl moves cell values on insert/delete but leaves merged ranges where they
    were, which silently corrupted the totals row of the quotation sheet.
    """
    from openpyxl.worksheet.cell_range import CellRange

    ranges = [CellRange(str(item)) for item in sheet.merged_cells.ranges]
    for item in ranges:
        sheet.unmerge_cells(str(item))

    if delta > 0:
        sheet.insert_rows(at_row, amount=delta)
    elif delta < 0:
        sheet.delete_rows(at_row, amount=-delta)

    for item in ranges:
        if item.min_row >= at_row:
            item.shift(row_shift=delta)
        sheet.merge_cells(str(item))


def _detail_rows(sheet, template_row: int) -> list[int]:
    """Rows of the line-item block: the template row plus consecutive numbered rows."""
    rows = [template_row]
    row = template_row + 1
    while row <= sheet.max_row:
        value = sheet.cell(row=row, column=1).value
        numbered = isinstance(value, (int, float)) or (
            isinstance(value, str) and value.strip().isdigit()
        )
        if not numbered:
            break
        rows.append(row)
        row += 1
    return rows


def _repeat_rows_by_anchor(sheet, provider: Callable[[str], list[dict[str, Any]] | None]) -> None:
    """Expand the line-item block to one row per data entry.

    The row containing ``[line_no]`` is the template. The block is sized to the
    entry count (inserting or removing rows, keeping merged ranges intact), then
    each row is filled from its own entry; columns the supplier must write (price,
    tax rate, lead time) are left blank.
    """
    from copy import copy

    template_row: int | None = None
    for row in sheet.iter_rows():
        for cell in row:
            if isinstance(cell.value, str) and PLACEHOLDER_RE.search(cell.value):
                if _XLSX_REPEAT_ANCHOR in cell.value:
                    template_row = cell.row
                    break
        if template_row:
            break
    if template_row is None:
        return

    entries = provider(_XLSX_REPEAT_ANCHOR)
    if not entries:
        return

    block = _detail_rows(sheet, template_row)
    original_last = block[-1]
    # Only grow. A supplier may quote extra items, so leftover blank rows are better
    # than a table that leaves them no room; shrinking also fought the merged totals
    # row for no real benefit.
    if len(entries) > len(block):
        _resize_block_keeping_merges(sheet, original_last + 1, len(entries) - len(block))
    # Totals cover the rows we used and any blank rows left for the supplier.
    new_last = max(template_row + len(entries) - 1, original_last)

    template_values: dict[int, Any] = {}
    styles: dict[int, Any] = {}
    for col in range(1, sheet.max_column + 1):
        source = sheet.cell(row=template_row, column=col)
        template_values[col] = source.value
        styles[col] = copy(source._style)

    for index, entry in enumerate(entries):
        target_row = template_row + index
        sheet.row_dimensions[target_row].height = sheet.row_dimensions[template_row].height
        for col, style in styles.items():
            cell = sheet.cell(row=target_row, column=col)
            cell._style = copy(style)
            value = template_values[col]
            if isinstance(value, str):
                if value.startswith("="):
                    cell.value = _offset_formula(value, template_row, target_row)
                else:
                    cell.value = PLACEHOLDER_RE.sub(
                        lambda match, row=entry: str(row.get(match.group(1).strip(), "")),
                        value,
                    )
            else:
                cell.value = value

    # Totals formulas were written for the template's five rows; stretch them over
    # the rows that actually exist now.
    if new_last != original_last:
        for row in sheet.iter_rows():
            for cell in row:
                if not (isinstance(cell.value, str) and cell.value.startswith("=SUM(")):
                    continue
                cell.value = cell.value.replace(f"{original_last})", f"{new_last})")


def substitute_xlsx(
    content_bytes: bytes,
    mapping: dict[str, str],
    *,
    repeat_provider: Callable[[str], list[dict[str, Any]] | None] | None = None,
) -> bytes:
    from openpyxl import load_workbook
    from openpyxl.cell.cell import MergedCell

    workbook = load_workbook(io.BytesIO(content_bytes))
    if repeat_provider is not None:
        for sheet in workbook.worksheets:
            _repeat_rows_by_anchor(sheet, repeat_provider)
    for sheet in workbook.worksheets:
        for row in sheet.iter_rows():
            for cell in row:
                if isinstance(cell, MergedCell):
                    continue
                if not isinstance(cell.value, str):
                    continue
                if not PLACEHOLDER_RE.search(cell.value):
                    continue
                cell.value = PLACEHOLDER_RE.sub(
                    lambda match: mapping.get(match.group(1).strip(), ""),
                    cell.value,
                )

    buf = io.BytesIO()
    workbook.save(buf)
    return buf.getvalue()


async def generate_payment_document(
    db: AsyncSession,
    template_code: str,
    schedule_item_id: UUID,
    *,
    actor: User | None = None,
) -> tuple[bytes, str]:
    template = (
        await db.execute(
            select(DocumentTemplate)
            .where(DocumentTemplate.code == template_code)
            .options(selectinload(DocumentTemplate.template_document))
        )
    ).scalar_one_or_none()
    if template is None:
        raise HTTPException(404, "template.not_found")
    if not template.is_enabled:
        raise HTTPException(409, "template.disabled")
    if template.template_document is None:
        raise HTTPException(409, "template.no_file")

    schedule = (
        await db.execute(
            select(PaymentSchedule)
            .where(PaymentSchedule.id == schedule_item_id)
            .options(
                selectinload(PaymentSchedule.contract).selectinload(Contract.po),
                selectinload(PaymentSchedule.contract).selectinload(Contract.supplier),
                selectinload(PaymentSchedule.po).selectinload(PurchaseOrder.supplier),
            )
        )
    ).scalar_one_or_none()
    if schedule is None:
        raise HTTPException(404, "schedule_item.not_found")

    if schedule.contract is not None:
        contract = schedule.contract
        po = contract.po
        supplier = contract.supplier
    elif schedule.po is not None:
        po = schedule.po
        linked_contract_ids = (
            (
                await db.execute(
                    select(POContractLink.contract_id).where(POContractLink.po_id == po.id)
                )
            )
            .scalars()
            .all()
        )
        contract_ids = list(linked_contract_ids)
        if not contract_ids:
            contract = (
                await db.execute(select(Contract).where(Contract.po_id == po.id).limit(1))
            ).scalar_one_or_none()
        elif len(contract_ids) == 1:
            contract = (
                await db.execute(select(Contract).where(Contract.id == contract_ids[0]).limit(1))
            ).scalar_one_or_none()
        else:
            contract = None
        if contract is None:
            raise HTTPException(
                409,
                "template.contract_required_for_generation",
            )
        supplier = (
            await db.execute(select(Supplier).where(Supplier.id == po.supplier_id))
        ).scalar_one_or_none()
    else:
        raise HTTPException(409, "schedule_item.orphan")

    if supplier is None:
        raise HTTPException(409, "template.supplier_missing")

    company = None
    company_id = getattr(po, "company_id", None)
    if company_id is not None:
        company = (
            await db.execute(select(Company).where(Company.id == company_id))
        ).scalar_one_or_none()

    file_bytes = _read_document_bytes(template.template_document)
    original_filename = template.template_document.original_filename.lower()

    context = build_context(po, contract, supplier, schedule, actor=actor, company=company)
    filename_only = extract_placeholders(None, template.filename_template)
    placeholders = extract_placeholders(file_bytes, template.filename_template)
    mapping = await resolve_all_placeholders(
        db,
        placeholders,
        context,
        filename_placeholders=set(filename_only),
    )

    if original_filename.endswith(".xlsx"):
        generated_bytes = substitute_xlsx(file_bytes, mapping)
        output_ext = ".xlsx"
    else:
        generated_bytes = substitute_docx(file_bytes, mapping)
        output_ext = ".docx"
    filename_base = render_filename(template.filename_template, mapping)
    if not filename_base:
        filename_base = f"{template.code}_{schedule.installment_no}"
    filename = f"{filename_base}{output_ext}"

    return generated_bytes, filename


def _read_document_bytes(document: Document) -> bytes:

    from app.config import get_settings

    settings = get_settings()
    media_root = Path(getattr(settings, "media_root", "/app/media"))
    path = media_root / document.storage_key
    if not path.exists():
        raise HTTPException(500, "template.file_missing_on_disk")
    return path.read_bytes()


# ── RFQ quotation ────────────────────────────────────────────────────────────


def build_rfq_context(rfq: Any, company: Any, pr: Any) -> dict[str, Any]:
    """Header values for the quotation sheet handed to suppliers.

    Only what we know: the supplier fills prices, tax rate, lead time and
    warranty themselves, so those columns stay blank in the template.
    """
    created = getattr(rfq, "created_at", None)
    return {
        "rfq.number": rfq.rfq_number,
        "rfq.date": created.date().isoformat() if created else "",
        "rfq.deadline": _as_date_str(rfq.deadline),
        "rfq.currency": getattr(pr, "currency", None) or "CNY",
        "rfq.pr_number": getattr(pr, "pr_number", None) or "",
        "rfq.delivery_location": getattr(pr, "delivery_address", None) or "",
        "rfq.payment_terms": "",
        "buyer.name": getattr(company, "name_zh", None) or getattr(company, "name_en", None) or "",
    }


def rfq_line_entries(rfq: Any) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for index, item in enumerate(getattr(rfq, "items", []) or [], start=1):
        entries.append(
            {
                "line_no": str(index),
                "item_name": item.item_name or "",
                "brand_model": "",
                "specification": (item.specification or "").strip(),
                "qty": _as_date_str(item.qty),
                "uom": item.uom or "",
            }
        )
    return entries


async def generate_rfq_quotation(db: AsyncSession, rfq_id: UUID) -> tuple[bytes, str]:
    """Render the quotation sheet for one RFQ from the bundled template."""
    from app.models import RFQ, Company, PurchaseRequisition

    rfq = (
        await db.execute(select(RFQ).where(RFQ.id == rfq_id).options(selectinload(RFQ.items)))
    ).scalar_one_or_none()
    if rfq is None:
        raise HTTPException(404, "rfq.not_found")

    pr = (
        (
            await db.execute(select(PurchaseRequisition).where(PurchaseRequisition.id == rfq.pr_id))
        ).scalar_one_or_none()
        if rfq.pr_id
        else None
    )
    company = (
        (await db.execute(select(Company).where(Company.id == rfq.company_id))).scalar_one_or_none()
        if rfq.company_id
        else None
    )

    template_path = Path(__file__).resolve().parent.parent / "templates" / "rfq_quotation.xlsx"
    context = build_rfq_context(rfq, company, pr)
    lines = rfq_line_entries(rfq)

    content = substitute_xlsx(
        template_path.read_bytes(),
        context,
        repeat_provider=lambda anchor: lines if anchor == "line_no" else None,
    )
    filename = render_filename("[number]-询价单.xlsx", {"number": rfq.rfq_number})
    return content, filename
