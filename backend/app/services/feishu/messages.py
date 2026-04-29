from __future__ import annotations

from typing import Any


def _card_header(title: str, color: str = "blue") -> dict[str, Any]:
    return {
        "title": {"tag": "plain_text", "content": title},
        "template": color,
    }


def _markdown_element(content: str) -> dict[str, Any]:
    return {"tag": "markdown", "content": content}


def _action_element(actions: list[dict[str, Any]]) -> dict[str, Any]:
    return {"tag": "action", "actions": actions}


def _button(text: str, url: str, button_type: str = "primary") -> dict[str, Any]:
    return {
        "tag": "button",
        "text": {"tag": "plain_text", "content": text},
        "type": button_type,
        "url": url,
    }


def _hr_element() -> dict[str, Any]:
    return {"tag": "hr"}


def _note_element(content: str) -> dict[str, Any]:
    return {"tag": "note", "elements": [{"tag": "plain_text", "content": content}]}


def build_pr_submitted_card(
    pr_title: str,
    applicant: str,
    department: str,
    amount: str,
    line_count: int,
    pr_url: str,
) -> dict[str, Any]:
    return {
        "config": {"wide_screen_mode": True},
        "header": _card_header("📋 新的采购申请已提交", "blue"),
        "elements": [
            _markdown_element(f"**申请标题：**{pr_title}"),
            _markdown_element(f"**申请人：**{applicant}"),
            _markdown_element(f"**申请部门：**{department}"),
            _markdown_element(f"**金额：**{amount}"),
            _markdown_element(f"**明细行数：**{line_count} 行"),
            _hr_element(),
            _action_element([_button("查看详情", pr_url)]),
            _note_element("Mica 采购管理系统"),
        ],
    }


def build_approval_decided_card(
    pr_title: str,
    decider: str,
    result: str,
    comment: str,
    pr_url: str,
) -> dict[str, Any]:
    result_label = "✅ 已通过" if result == "approved" else "❌ 已驳回"
    color = "green" if result == "approved" else "red"
    return {
        "config": {"wide_screen_mode": True},
        "header": _card_header(f"审批决定: {result_label}", color),
        "elements": [
            _markdown_element(f"**采购申请：**{pr_title}"),
            _markdown_element(f"**审批人：**{decider}"),
            _markdown_element(f"**决定：**{result_label}"),
            *([_markdown_element(f"**备注：**{comment}")] if comment else []),
            _hr_element(),
            _action_element([_button("查看详情", pr_url)]),
            _note_element("Mica 采购管理系统"),
        ],
    }


def build_po_created_card(
    po_number: str,
    supplier: str,
    amount: str,
    pr_title: str,
    po_url: str,
) -> dict[str, Any]:
    return {
        "config": {"wide_screen_mode": True},
        "header": _card_header("📦 采购订单已创建", "turquoise"),
        "elements": [
            _markdown_element(f"**订单编号：**{po_number}"),
            _markdown_element(f"**供应商：**{supplier}"),
            _markdown_element(f"**金额：**{amount}"),
            _markdown_element(f"**关联申请：**{pr_title}"),
            _hr_element(),
            _action_element([_button("查看订单", po_url)]),
            _note_element("Mica 采购管理系统"),
        ],
    }


def build_payment_pending_card(
    payment_id: str,
    po_number: str,
    supplier: str,
    amount: str,
    payment_url: str,
) -> dict[str, Any]:
    return {
        "config": {"wide_screen_mode": True},
        "header": _card_header("💰 付款待审核", "orange"),
        "elements": [
            _markdown_element(f"**付款编号：**{payment_id}"),
            _markdown_element(f"**关联订单：**{po_number}"),
            _markdown_element(f"**供应商：**{supplier}"),
            _markdown_element(f"**金额：**{amount}"),
            _hr_element(),
            _action_element([_button("查看付款", payment_url)]),
            _note_element("Mica 采购管理系统"),
        ],
    }


def build_contract_expiring_card(
    contract_number: str,
    supplier: str,
    expiry_date: str,
    days_remaining: int,
    total_amount: str,
    used_amount: str,
    contract_url: str,
) -> dict[str, Any]:
    urgency_color = "red" if days_remaining <= 7 else "orange"
    return {
        "config": {"wide_screen_mode": True},
        "header": _card_header("⚠️ 合同即将到期", urgency_color),
        "elements": [
            _markdown_element(f"**合同编号：**{contract_number}"),
            _markdown_element(f"**供应商：**{supplier}"),
            _markdown_element(f"**到期日期：**{expiry_date}"),
            _markdown_element(f"**剩余天数：**{days_remaining} 天"),
            _markdown_element(f"**合同总额：**{total_amount}"),
            _markdown_element(f"**已使用金额：**{used_amount}"),
            _hr_element(),
            _action_element([_button("查看合同", contract_url)]),
            _note_element("Mica 采购管理系统"),
        ],
    }
