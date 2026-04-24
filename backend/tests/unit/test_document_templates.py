from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.services import document_templates as svc


def test_extract_placeholders_from_filename_only():
    placeholders = svc.extract_placeholders(
        None, "财务付款表_[PO编号]_[付款期次]_[付款日期YYYYMMDD]"
    )
    assert placeholders == ["PO编号", "付款期次", "付款日期YYYYMMDD"]


def test_extract_placeholders_preserves_order_and_deduplicates():
    placeholders = svc.extract_placeholders(
        None,
        "[A]-[B]-[A]-[C]",
    )
    assert placeholders == ["A", "B", "C"]


def test_extract_placeholders_ignores_multiline_square_brackets():
    placeholders = svc.extract_placeholders(None, "[line1\nline2]")
    assert placeholders == []


def test_render_filename_substitutes_known_placeholders():
    result = svc.render_filename(
        "财务付款表_[PO编号]_[付款期次]",
        {"PO编号": "JQ-001", "付款期次": "第1期"},
    )
    assert result == "财务付款表_JQ-001_第1期"


def test_render_filename_sanitizes_illegal_chars():
    result = svc.render_filename(
        "[A]/[B]",
        {"A": "foo<bar", "B": "baz?qux"},
    )
    assert "/" not in result
    assert "<" not in result
    assert "?" not in result


def test_cn_amount_upper_zero_cents():
    assert svc.cn_amount_upper("4500000") == "肆佰伍拾万元整"


def test_cn_amount_upper_with_cents():
    assert svc.cn_amount_upper("12.34") == "壹拾贰元叁角肆分"


def test_cn_amount_upper_handles_decimal():
    assert svc.cn_amount_upper(Decimal("100.50")) == "壹佰元伍角整"


def test_cn_amount_upper_empty_input():
    assert svc.cn_amount_upper(None) == ""
    assert svc.cn_amount_upper("") == ""


def _sample_context():
    return {
        "po": {
            "po_number": "PO-2026-0001",
            "currency": "CNY",
            "total_amount": "10500000",
            "status": "confirmed",
        },
        "contract": {
            "contract_number": "JQPA20260425001",
            "title": "Annual Hardware",
            "total_amount": "10500000",
            "currency": "CNY",
            "signed_date": "2026-03-01",
            "effective_date": "2026-03-01",
            "expiry_date": "2027-03-01",
            "status": "active",
        },
        "supplier": {
            "name": "Foo Corp",
            "code": "SUP-FOO",
            "tax_number": "91310000TAX",
            "contact_name": "",
            "contact_phone": "",
            "contact_email": "",
            "payee_name": "Foo Payee",
            "payee_name_effective": "Foo Payee",
            "payee_bank": "ICBC Shanghai",
            "payee_bank_account": "6222 0800 1234 5678",
        },
        "schedule": {
            "installment_no": 2,
            "label": "balance",
            "label_with_installment": "第 2 期 · balance",
            "planned_amount": "5000000",
            "planned_date": "2026-05-01",
            "actual_amount": "5000000",
            "actual_date": "2026-04-25",
            "status": "paid",
            "effective_amount": "5000000",
            "effective_date": "2026-04-25",
            "trigger_type": "fixed_date",
            "trigger_description": "",
        },
    }


def test_resolve_deterministic_po_number():
    context = _sample_context()
    assert svc.resolve_placeholder_deterministic("PO编号", context) == "PO-2026-0001"
    assert svc.resolve_placeholder_deterministic("采购订单号", context) == "PO-2026-0001"


def test_resolve_deterministic_contract_number():
    context = _sample_context()
    assert svc.resolve_placeholder_deterministic("合同编号", context) == "JQPA20260425001"


def test_resolve_deterministic_payee_info():
    context = _sample_context()
    assert svc.resolve_placeholder_deterministic("收款单位名称", context) == "Foo Payee"
    assert svc.resolve_placeholder_deterministic("收款单位开户行", context) == "ICBC Shanghai"
    assert svc.resolve_placeholder_deterministic("银行账号", context) == "6222 0800 1234 5678"


def test_resolve_deterministic_returns_none_for_unknown():
    context = _sample_context()
    assert svc.resolve_placeholder_deterministic("随便什么字段", context) is None


def test_enrich_computed_handles_date_pattern():
    context = _sample_context()
    result = svc._enrich_with_computed("付款日期 YYYY年MM月DD日", context, None)
    assert result == "2026年04月25日"


def test_enrich_computed_handles_yyyymmdd():
    context = _sample_context()
    result = svc._enrich_with_computed("YYYYMMDD", context, None)
    assert result == "20260425"


def test_enrich_computed_handles_cn_upper_amount():
    context = _sample_context()
    result = svc._enrich_with_computed("本期付款金额(大写)", context, None)
    assert result == "伍佰万元整"


def test_enrich_computed_passes_through_existing_value():
    context = _sample_context()
    result = svc._enrich_with_computed("付款日期 YYYY年MM月DD日", context, "already-set")
    assert result == "already-set"


@pytest.mark.asyncio
async def test_resolve_all_falls_back_gracefully_without_llm(monkeypatch):
    async def _no_llm(*_args, **_kwargs):
        return {}

    monkeypatch.setattr(svc, "resolve_placeholders_with_llm", _no_llm)

    context = _sample_context()
    mapping = await svc.resolve_all_placeholders(
        db=SimpleNamespace(),
        placeholders=[
            "PO编号",
            "合同编号",
            "本期付款金额(大写)",
            "付款日期YYYYMMDD",
            "unknown_field",
        ],
        context=context,
    )
    assert mapping["PO编号"] == "PO-2026-0001"
    assert mapping["合同编号"] == "JQPA20260425001"
    assert mapping["本期付款金额(大写)"] == "伍佰万元整"
    assert mapping["付款日期YYYYMMDD"] == "20260425"
    assert mapping["unknown_field"] == ""
