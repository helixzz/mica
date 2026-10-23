# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
"""Card 2.0 builders: layout, semantics and locale."""

from app.services.feishu import cards
from app.services.feishu.messages import (
    build_approval_decided_card,
    build_contract_expiring_card,
    build_event_card,
    build_payment_pending_card,
    build_po_created_card,
    build_pr_submitted_card,
)


def _find(card: dict, tag: str) -> list[dict]:
    return [element for element in card["body"]["elements"] if element["tag"] == tag]


def _actions(card: dict) -> list[dict]:
    rows = _find(card, "action")
    assert rows, "card has no action row"
    return rows[0]["actions"]


def _texts(card: dict) -> str:
    return str(card)


def test_card_is_schema_2_with_semantic_template():
    payload = cards.card(title="Test", status="action", footer="foot")
    assert payload["schema"] == "2.0"
    assert payload["config"]["wide_screen_mode"] is True
    assert payload["header"]["template"] == "orange"
    assert payload["body"]["elements"][-1]["tag"] == "note"
    assert _texts(payload).count("foot") == 1


def test_unknown_status_falls_back_to_blue():
    payload = cards.card(title="Test", status="nope")
    assert payload["header"]["template"] == "blue"


def test_field_rows_use_two_columns():
    rows = cards.field_rows([("金额", "¥1.00"), ("部门", "IT"), ("申请人", "Alice")])
    assert len(rows) == 2
    assert rows[0]["tag"] == "column_set"
    assert len(rows[0]["columns"]) == 2
    # the trailing cell is padded so the grid keeps its shape
    assert len(rows[1]["columns"]) == 2


def test_button_carries_both_navigation_forms():
    button = cards.button("查看", "https://mica.example/approvals?task=1", primary=True)
    assert button["type"] == "primary"
    assert button["behaviors"][0]["type"] == "open_url"
    assert button["behaviors"][0]["default_url"].endswith("task=1")
    assert button["url"].endswith("task=1")


def test_table_columns_and_rows():
    table = cards.table(
        [("pr", "PR"), ("amount", "金额")],
        [{"pr": "PR-1", "amount": "¥1.00"}],
    )
    assert table["tag"] == "table"
    assert [column["name"] for column in table["columns"]] == ["pr", "amount"]
    assert table["rows"][0]["pr"] == "PR-1"


def test_pr_submitted_zh_leads_with_action():
    card = build_pr_submitted_card(
        pr_number="PR-2026-0095",
        title="prod耗材补货",
        applicant="Chris Wang",
        department="研发部",
        amount="¥29,750.00",
        line_count=3,
        item_count=4,
        waiting_hours=3.2,
        sla_hours=24,
        task_url="https://mica.example/approvals?task=t1",
        pr_url="https://mica.example/purchase-requisitions/1",
        locale="zh-CN",
    )
    assert card["header"]["template"] == "orange"
    assert "Chris Wang" in card["header"]["title"]["content"]
    assert "已等待 3.2 小时" in card["header"]["subtitle"]["content"]
    actions = _actions(card)
    assert actions[0]["behaviors"][0]["default_url"].endswith("task=t1")
    assert "¥29,750.00" in _texts(card)


def test_pr_submitted_en_uses_english_labels():
    card = build_pr_submitted_card(
        pr_number="PR-1",
        title="Servers",
        applicant="Alice",
        department="IT",
        amount="$1,000.00",
        line_count=1,
        item_count=1,
        waiting_hours=1.0,
        sla_hours=24,
        task_url="",
        pr_url="",
        locale="en-US",
    )
    assert "waiting 1.0h" in card["header"]["subtitle"]["content"]
    assert "Amount" in _texts(card)
    assert not _find(card, "action")


def test_approval_decided_is_green_when_approved():
    card = build_approval_decided_card(
        pr_number="PR-1",
        title="Servers",
        decider="Bob",
        result="approved",
        comment="ok",
        amount="¥1.00",
        pr_url="https://mica.example/pr/1",
        locale="zh-CN",
    )
    assert card["header"]["template"] == "green"
    assert "ok" in _texts(card)


def test_approval_rejected_is_red():
    card = build_approval_decided_card(
        pr_number="PR-1",
        title="Servers",
        decider="Bob",
        result="rejected",
        comment="",
        amount="¥1.00",
        pr_url="",
        locale="zh-CN",
    )
    assert card["header"]["template"] == "red"


def test_po_created_card_lists_supplier_and_amount():
    card = build_po_created_card(
        po_number="PO-1",
        supplier="ACME",
        amount="¥9,000.00",
        pr_title="Servers",
        po_url="https://mica.example/po/1",
        locale="zh-CN",
    )
    text = _texts(card)
    assert "PO-1" in text and "ACME" in text and "¥9,000.00" in text
    assert card["header"]["template"] == "blue"


def test_payment_pending_is_action():
    card = build_payment_pending_card(
        payment_number="PAY-1",
        po_number="PO-1",
        supplier="ACME",
        amount="¥1.00",
        due_date="2026年10月30日",
        payment_url="https://mica.example/pay/1",
        locale="zh-CN",
    )
    assert card["header"]["template"] == "orange"
    assert "2026年10月30日" in _texts(card)


def test_contract_expiring_escalates_within_a_week():
    card = build_contract_expiring_card(
        contract_number="C-1",
        supplier="ACME",
        expiry_date="2026年10月30日",
        days_remaining=5,
        total_amount="¥1,000.00",
        used_amount="¥400.00",
        contract_url="",
        locale="zh-CN",
    )
    assert card["header"]["template"] == "red"


def test_contract_expiring_outside_a_week_is_action():
    card = build_contract_expiring_card(
        contract_number="C-1",
        supplier="ACME",
        expiry_date="2026年11月30日",
        days_remaining=20,
        total_amount="¥1,000.00",
        used_amount="—",
        contract_url="",
        locale="zh-CN",
    )
    assert card["header"]["template"] == "orange"


def test_event_card_renders_changes_with_arrows():
    card = build_event_card(
        title="合同 C-1 已更新",
        summary="",
        fields=[("合同", "C-1")],
        changes=[("金额", "¥100.00 → ¥200.00")],
        url="https://mica.example/contracts/1",
        status="info",
        locale="zh-CN",
    )
    text = _texts(card)
    assert "¥100.00 → ¥200.00" in text
    assert _actions(card)[0]["url"].endswith("/contracts/1")
