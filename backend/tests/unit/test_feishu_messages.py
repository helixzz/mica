# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
from unittest.mock import patch

from app.services.feishu.messages import (
    _button,
    _card_header,
    _hr_element,
    _make_generic_card,
    _markdown_element,
    _note_element,
    build_approval_decided_card,
    build_contract_expiring_card,
    build_payment_pending_card,
    build_po_created_card,
    build_pr_submitted_card,
)


def test_card_header_default_color():
    h = _card_header("Test")
    assert h["title"]["content"] == "Test"
    assert h["template"] == "blue"


def test_card_header_custom_color():
    h = _card_header("Warn", "red")
    assert h["template"] == "red"


def test_markdown_element():
    e = _markdown_element("**bold**")
    assert e == {"tag": "markdown", "content": "**bold**"}


def test_hr_element():
    assert _hr_element() == {"tag": "hr"}


def test_note_element():
    n = _note_element("footer")
    assert n["tag"] == "note"
    assert n["elements"][0]["content"] == "footer"


def test_button_absolute_url_unchanged():
    b = _button("Click", "https://example.com/path")
    assert b["url"] == "https://example.com/path"
    assert b["text"]["content"] == "Click"
    assert b["type"] == "primary"


@patch("app.config.get_settings")
def test_button_relative_url_prepends_base(mock_settings):
    mock_settings.return_value.app_base_url = "https://mica.example.com"
    b = _button("View", "/purchase-requisitions/123")
    assert b["url"] == "https://mica.example.com/purchase-requisitions/123"


@patch("app.config.get_settings")
def test_button_relative_url_strips_trailing_slash(mock_settings):
    mock_settings.return_value.app_base_url = "https://mica.example.com/"
    b = _button("View", "/orders/1")
    assert b["url"] == "https://mica.example.com/orders/1"


def test_button_empty_url():
    b = _button("Noop", "")
    assert b["url"] == ""


def test_build_pr_submitted_card_structure():
    card = build_pr_submitted_card(
        pr_title="Buy Servers",
        applicant="Alice",
        department="IT",
        amount="¥100,000",
        line_count=3,
        pr_url="https://mica.example.com/pr/1",
    )
    assert card["config"]["wide_screen_mode"] is True
    assert "采购申请" in card["header"]["title"]["content"]
    md_texts = [e["content"] for e in card["elements"] if e.get("tag") == "markdown"]
    assert any("Buy Servers" in t for t in md_texts)
    assert any("Alice" in t for t in md_texts)
    assert any("IT" in t for t in md_texts)
    assert any("¥100,000" in t for t in md_texts)
    assert any("3" in t for t in md_texts)


def test_build_approval_decided_card_approved():
    card = build_approval_decided_card(
        pr_title="PR-001",
        decider="Bob",
        result="approved",
        comment="LGTM",
        pr_url="https://mica.example.com/pr/1",
    )
    assert "通过" in card["header"]["title"]["content"]


def test_build_approval_decided_card_rejected():
    card = build_approval_decided_card(
        pr_title="PR-002",
        decider="Bob",
        result="rejected",
        comment="Too expensive",
        pr_url="https://mica.example.com/pr/2",
    )
    assert "拒绝" in card["header"]["title"]["content"]


def test_build_approval_decided_card_returned():
    card = build_approval_decided_card(
        pr_title="PR-003",
        decider="Bob",
        result="returned",
        comment="",
        pr_url="",
    )
    assert "退回" in card["header"]["title"]["content"]


def test_build_po_created_card():
    card = build_po_created_card(
        po_number="PO-2026-001",
        supplier="Acme Corp",
        amount="¥50,000",
        pr_title="Buy Cables",
        po_url="https://mica.example.com/po/1",
    )
    md_texts = [e["content"] for e in card["elements"] if e.get("tag") == "markdown"]
    assert any("PO-2026-001" in t for t in md_texts)
    assert any("Acme Corp" in t for t in md_texts)


def test_build_payment_pending_card():
    card = build_payment_pending_card(
        payment_id="PAY-001",
        po_number="PO-001",
        supplier="Vendor",
        amount="¥10,000",
        payment_url="https://mica.example.com/pay/1",
    )
    assert "付款" in card["header"]["title"]["content"]
    md_texts = [e["content"] for e in card["elements"] if e.get("tag") == "markdown"]
    assert any("PAY-001" in t for t in md_texts)


def test_build_contract_expiring_card_urgent():
    card = build_contract_expiring_card(
        contract_number="C-001",
        supplier="Vendor",
        expiry_date="2026-06-01",
        days_remaining=5,
        total_amount="¥1,000,000",
        used_amount="¥800,000",
        contract_url="https://mica.example.com/c/1",
    )
    assert card["header"]["template"] == "red"


def test_build_contract_expiring_card_not_urgent():
    card = build_contract_expiring_card(
        contract_number="C-002",
        supplier="Vendor",
        expiry_date="2026-07-01",
        days_remaining=30,
        total_amount="¥500,000",
        used_amount="¥100,000",
        contract_url="",
    )
    assert card["header"]["template"] == "orange"


def test_make_generic_card_with_body_and_link():
    card = _make_generic_card(
        title="Notification",
        body="Something happened",
        link_url="https://mica.example.com/details",
    )
    assert card["header"]["title"]["content"] == "Notification"
    has_md = any(e.get("content") == "Something happened" for e in card["elements"])
    assert has_md
    has_button = any(e.get("tag") == "action" for e in card["elements"])
    assert has_button


def test_make_generic_card_no_link():
    card = _make_generic_card(title="Info", body="Just FYI", link_url="")
    action_elements = [e for e in card["elements"] if e.get("tag") == "action"]
    assert len(action_elements) == 0


def test_make_generic_card_no_body():
    card = _make_generic_card(title="Empty", body="", link_url="")
    md_elements = [e for e in card["elements"] if e.get("tag") == "markdown"]
    assert len(md_elements) == 0
