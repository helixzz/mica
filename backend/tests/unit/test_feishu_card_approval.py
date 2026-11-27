"""Unit tests for rich Feishu approval cards and interactive card callbacks."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.services.feishu import messages as feishu_messages
from app.services.feishu.card_callback import handle_card_action


def _sample_items(count: int = 2) -> list[dict[str, str]]:
    return [
        {
            "name": f"GPU Server #{i + 1}",
            "spec": "8x H200 / 1TB RAM",
            "qty": "2 台",
            "amount": "¥120,000.00",
        }
        for i in range(count)
    ]


def test_pr_submitted_card_renders_rich_content_and_interactive_form() -> None:
    task_id = str(uuid4())
    card = feishu_messages.build_pr_submitted_card(
        pr_number="PR-2026-0042",
        title="研发集群扩容",
        applicant="张三",
        department="基础架构部",
        amount="¥240,000.00",
        line_count=6,
        item_count=12,
        waiting_hours=1.5,
        sla_hours=24,
        task_url="https://mica.example/approvals?task=1",
        pr_url="https://mica.example/purchase-requisitions/1",
        locale="zh-CN",
        task_id=task_id,
        interactive=True,
        cost_center="CC-INFRA 算力预算",
        required_date="2026-12-01",
        business_reason="用于 Q4 训练任务扩容，当前集群利用率已超过 95%。",
        items=_sample_items(6),
        stage_name="部门经理审批",
        stage_order=2,
        total_stages=3,
        prior_approvals=["李四"],
    )

    assert card["schema"] == "2.0"
    assert card["header"]["template"] == "orange"
    elements = card["body"]["elements"]

    # Table capped at 5 rows + "more items" hint
    tables = [el for el in elements if el.get("tag") == "table"]
    assert len(tables) == 1
    assert len(tables[0]["rows"]) == 5

    # Interactive form with comment input and 3 submit buttons + view link
    forms = [el for el in elements if el.get("tag") == "form"]
    assert len(forms) == 1
    form_elements = forms[0]["elements"]
    inputs = [el for el in form_elements if el.get("tag") == "input"]
    assert len(inputs) == 1
    assert inputs[0]["name"] == "comment"

    btn_row = next(el for el in form_elements if el.get("element_id") == "actions")
    buttons = [col["elements"][0] for col in btn_row["columns"]]
    assert len(buttons) == 4
    submit_actions = [
        btn["behaviors"][0]["value"]["action"]
        for btn in buttons
        if btn.get("form_action_type") == "submit"
    ]
    assert submit_actions == ["approve", "return", "reject"]


def test_pr_submitted_card_non_interactive_has_no_form() -> None:
    card = feishu_messages.build_pr_submitted_card(
        pr_number="PR-2026-0043",
        title="办公耗材",
        applicant="Alice",
        department="IT",
        amount="$500.00",
        line_count=1,
        item_count=5,
        waiting_hours=None,
        sla_hours=24,
        task_url="https://mica.example/approvals?task=2",
        pr_url="https://mica.example/purchase-requisitions/2",
        locale="en-US",
        task_id=str(uuid4()),
        interactive=False,
    )
    elements = card["body"]["elements"]
    assert not any(el.get("tag") == "form" for el in elements)


def test_pr_card_decided_replaces_actions_with_outcome() -> None:
    card = feishu_messages.build_pr_card_decided(
        pr_number="PR-2026-0042",
        title="研发集群扩容",
        applicant="张三",
        department="基础架构部",
        amount="¥240,000.00",
        line_count=2,
        item_count=4,
        decider="王五",
        result="rejected",
        comment="请补充两家供应商比价单",
        decided_at="2026-11-25 10:00 UTC",
        pr_url="https://mica.example/purchase-requisitions/1",
        locale="zh-CN",
        items=_sample_items(2),
    )
    assert card["header"]["template"] == "red"
    elements = card["body"]["elements"]
    assert not any(el.get("tag") == "form" for el in elements)
    all_md = "\n".join(el.get("content", "") for el in elements if el.get("tag") == "markdown")
    assert "请补充两家供应商比价单" in all_md


def _mock_db_for_callback(
    *,
    user: object | None,
    task: object | None,
    instance: object | None,
    pr: object | None,
) -> AsyncMock:
    db = AsyncMock()
    user_result = MagicMock()
    user_result.scalars.return_value.first.return_value = user
    pr_result = MagicMock()
    pr_result.scalars.return_value.first.return_value = pr
    db.execute = AsyncMock(side_effect=[user_result, pr_result])

    async def _get(model: type, obj_id: object) -> object | None:
        if model.__name__ == "ApprovalTask":
            return task
        if model.__name__ == "ApprovalInstance":
            return instance
        return None

    db.get = AsyncMock(side_effect=_get)
    return db


@pytest.mark.asyncio
async def test_callback_requires_reason_for_reject_and_return() -> None:
    user = SimpleNamespace(
        id=uuid4(),
        username="bob",
        display_name="Bob",
        preferred_locale="zh-CN",
    )
    db = _mock_db_for_callback(user=user, task=None, instance=None, pr=None)

    for action in ("reject", "return"):
        db.execute = AsyncMock(
            return_value=MagicMock(
                scalars=MagicMock(return_value=MagicMock(first=MagicMock(return_value=user)))
            )
        )
        resp = await handle_card_action(
            db,
            action_value={"action": action, "task_id": str(uuid4())},
            form_value={"comment": "   "},
            operator_open_id="ou_bob",
        )
        assert resp["toast"]["type"] == "warning"
        assert "理由" in resp["toast"]["content"]
        assert "card" not in resp


@pytest.mark.asyncio
async def test_callback_approve_applies_decision_and_returns_decided_card() -> None:
    task_id = uuid4()
    inst_id = uuid4()
    pr_id = uuid4()
    user = SimpleNamespace(
        id=uuid4(),
        username="bob",
        display_name="Bob",
        preferred_locale="zh-CN",
    )
    task = SimpleNamespace(
        id=task_id,
        instance_id=inst_id,
        status="pending",
        comment=None,
        acted_at=None,
    )
    instance = SimpleNamespace(
        id=inst_id,
        biz_type="purchase_requisition",
        biz_id=pr_id,
        biz_number="PR-2026-0099",
        title="测试采购申请",
        amount=Decimal("10000"),
        status="pending",
        completed_at=None,
    )
    pr = SimpleNamespace(
        id=pr_id,
        currency="CNY",
        items=[],
        department=None,
        cost_center=None,
        required_date=None,
        expected_delivery_date=None,
        requester=SimpleNamespace(display_name="Alice"),
        business_reason="测试用途",
    )
    db = _mock_db_for_callback(user=user, task=task, instance=instance, pr=pr)

    with (
        patch(
            "app.services.feishu.card_callback.system_params.get",
            new=AsyncMock(return_value="https://mica.example"),
        ),
        patch(
            "app.services.feishu.card_callback.purchase_svc.decide_pr",
            new=AsyncMock(return_value=pr),
        ) as mock_decide,
    ):
        resp = await handle_card_action(
            db,
            action_value={"action": "approve", "task_id": str(task_id)},
            form_value={},
            operator_open_id="ou_bob",
        )

    assert resp["toast"]["type"] == "success"
    assert resp["card"]["type"] == "raw"
    assert resp["card"]["data"]["header"]["template"] == "green"
    mock_decide.assert_awaited_once()
    call_payload = mock_decide.await_args.args[3]
    assert call_payload.action == "approve"
    assert call_payload.comment


@pytest.mark.asyncio
async def test_callback_already_decided_refreshes_card() -> None:
    task_id = uuid4()
    inst_id = uuid4()
    pr_id = uuid4()
    user = SimpleNamespace(
        id=uuid4(),
        username="bob",
        display_name="Bob",
        preferred_locale="zh-CN",
    )
    task = SimpleNamespace(
        id=task_id,
        instance_id=inst_id,
        status="approved",
        comment="已在 Web 审批",
        acted_at=datetime.now(UTC),
    )
    instance = SimpleNamespace(
        id=inst_id,
        biz_type="purchase_requisition",
        biz_id=pr_id,
        biz_number="PR-2026-0100",
        title="已审批单据",
        amount=Decimal("5000"),
        status="approved",
        completed_at=datetime.now(UTC),
    )
    db = _mock_db_for_callback(user=user, task=task, instance=instance, pr=None)

    with patch(
        "app.services.feishu.card_callback.system_params.get",
        new=AsyncMock(return_value="https://mica.example"),
    ):
        resp = await handle_card_action(
            db,
            action_value={"action": "approve", "task_id": str(task_id)},
            form_value={},
            operator_open_id="ou_bob",
        )

    assert resp["toast"]["type"] == "info"
    assert resp["card"]["type"] == "raw"
    assert resp["card"]["data"]["header"]["template"] == "green"
