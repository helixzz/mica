"""Feishu interactive card callback handler for Mica approvals.

Processes ``card.action.trigger`` callbacks from Feishu Card 2.0 approval cards,
validating the operator's Mica identity and delegating the decision to the exact
same service path used by the Web UI (:func:`app.services.purchase.decide_pr`
or :func:`app.services.approval.act_on_task`).
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.dates import fmt_date
from app.core.money import fmt_amount
from app.i18n import t
from app.models import ApprovalInstance, ApprovalTask, PurchaseRequisition, User
from app.schemas import PRDecisionIn
from app.services import approval as approval_svc
from app.services import purchase as purchase_svc
from app.services.feishu import messages as feishu_messages
from app.services.system_params import system_params

logger = logging.getLogger("mica.feishu.card_callback")

_VALID_ACTIONS = {"approve", "return", "reject"}
_REASON_REQUIRED_ACTIONS = {"return", "reject"}


def _toast(kind: str, content: str) -> dict[str, Any]:
    return {"toast": {"type": kind, "content": content}}


def _user_locale(user: User | None) -> str:
    if user is not None and user.preferred_locale:
        return user.preferred_locale
    return "zh-CN"


async def _resolve_user(
    db: AsyncSession,
    *,
    open_id: str,
    union_id: str,
) -> User | None:
    if open_id:
        user = (
            (await db.execute(select(User).where(User.feishu_open_id == open_id))).scalars().first()
        )
        if user is not None:
            return user
    if union_id:
        user = (
            (await db.execute(select(User).where(User.feishu_union_id == union_id)))
            .scalars()
            .first()
        )
        if user is not None:
            return user
    return None


async def _load_pr_context(db: AsyncSession, pr_id: UUID) -> PurchaseRequisition | None:
    stmt = (
        select(PurchaseRequisition)
        .where(PurchaseRequisition.id == pr_id)
        .options(
            selectinload(PurchaseRequisition.items),
            selectinload(PurchaseRequisition.department),
            selectinload(PurchaseRequisition.cost_center),
            selectinload(PurchaseRequisition.requester),
        )
    )
    return (await db.execute(stmt)).scalars().first()


def _build_decided_card_payload(
    *,
    instance: ApprovalInstance,
    pr: PurchaseRequisition | None,
    decider_name: str,
    result: str,
    comment: str,
    decided_at: datetime | None,
    base_url: str,
    locale: str,
) -> dict[str, Any]:
    currency = getattr(pr, "currency", None) or "CNY"
    amount = fmt_amount(instance.amount, currency)
    items = list(pr.items) if pr is not None and pr.items else []
    item_summaries: list[dict[str, str]] = []
    for item in items[:5]:
        qty_val = float(item.qty or 0)
        qty_str = str(int(qty_val)) if qty_val.is_integer() else f"{qty_val:g}"
        item_summaries.append(
            {
                "name": str(item.item_name or ""),
                "spec": str(item.specification or ""),
                "qty": f"{qty_str} {item.uom or 'EA'}".strip(),
                "amount": fmt_amount(item.amount, currency),
            }
        )

    dept = getattr(pr, "department", None) if pr is not None else None
    department_name = ""
    if dept is not None:
        department_name = (dept.name_en if locale.startswith("en") else None) or dept.name_zh or ""

    cc = getattr(pr, "cost_center", None) if pr is not None else None
    cost_center_name = ""
    if cc is not None:
        code = getattr(cc, "code", "") or ""
        name = getattr(cc, "name", "") or ""
        cost_center_name = f"{code} {name}".strip() if code and name else (name or code)

    req_date = (
        getattr(pr, "required_date", None) or getattr(pr, "expected_delivery_date", None)
        if pr is not None
        else None
    )
    requester_name = (
        getattr(getattr(pr, "requester", None), "display_name", "") if pr is not None else ""
    )

    pr_url = f"{base_url.rstrip('/')}/purchase-requisitions/{instance.biz_id}" if base_url else ""
    decided_str = (
        decided_at.astimezone(UTC).strftime("%Y-%m-%d %H:%M UTC") if decided_at is not None else ""
    )

    card_data = feishu_messages.build_pr_card_decided(
        pr_number=str(instance.biz_number or ""),
        title=str(instance.title or ""),
        applicant=requester_name,
        department=department_name,
        amount=amount,
        line_count=len(items),
        item_count=int(sum(float(item.qty or 0) for item in items)) if items else 0,
        decider=decider_name,
        result=result,
        comment=comment,
        decided_at=decided_str,
        pr_url=pr_url,
        locale=locale,
        cost_center=cost_center_name,
        required_date=fmt_date(req_date, locale) if req_date is not None else "",
        business_reason=str(getattr(pr, "business_reason", "") or ""),
        items=item_summaries,
    )
    return {"type": "raw", "data": card_data}


async def handle_card_action(
    db: AsyncSession,
    *,
    action_value: dict[str, Any],
    form_value: dict[str, Any] | None = None,
    operator_open_id: str = "",
    operator_union_id: str = "",
) -> dict[str, Any]:
    """Process one Feishu card button click and return a Card 2.0 callback response."""
    action = str(action_value.get("action") or "").strip().lower()
    raw_task_id = str(action_value.get("task_id") or "").strip()
    if action not in _VALID_ACTIONS or not raw_task_id:
        return _toast("error", t("feishu.card.callback.invalid_payload", "zh-CN"))

    try:
        task_id = UUID(raw_task_id)
    except ValueError:
        return _toast("error", t("feishu.card.callback.invalid_payload", "zh-CN"))

    user = await _resolve_user(
        db,
        open_id=operator_open_id.strip(),
        union_id=operator_union_id.strip(),
    )
    if user is None:
        logger.warning("feishu card callback: unbound operator open_id=%s", operator_open_id)
        return _toast("error", t("feishu.card.callback.user_not_bound", "zh-CN"))

    locale = _user_locale(user)
    raw_comment = ""
    if isinstance(form_value, dict):
        raw_comment = str(form_value.get("comment") or "").strip()

    if action in _REASON_REQUIRED_ACTIONS and not raw_comment:
        return _toast("warning", t("feishu.card.callback.reason_required", locale))

    comment = raw_comment or t("feishu.card.callback.default_approve_comment", locale)

    task = await db.get(ApprovalTask, task_id)
    if task is None:
        return _toast("error", t("feishu.card.callback.no_pending_task", locale))

    instance = await db.get(ApprovalInstance, task.instance_id)
    if instance is None:
        return _toast("error", t("feishu.card.callback.no_pending_task", locale))

    base_url = str(await system_params.get(db, "app.base_url", "") or "")
    is_pr = instance.biz_type in ("pr", "purchase_requisition")
    pr = await _load_pr_context(db, instance.biz_id) if is_pr else None

    if task.status != "pending":
        result_status = (
            task.status
            if task.status in ("approved", "rejected", "returned")
            else (
                instance.status
                if instance.status in ("approved", "rejected", "returned")
                else "approved"
            )
        )
        resp = _toast("info", t("feishu.card.callback.already_decided", locale))
        resp["card"] = _build_decided_card_payload(
            instance=instance,
            pr=pr,
            decider_name=user.display_name or user.username,
            result=result_status,
            comment=task.comment or "",
            decided_at=task.acted_at or instance.completed_at,
            base_url=base_url,
            locale=locale,
        )
        return resp

    try:
        if is_pr:
            await purchase_svc.decide_pr(
                db,
                user,
                instance.biz_id,
                PRDecisionIn(action=action, comment=comment),
            )
        else:
            await approval_svc.act_on_task(db, user, instance.id, action, comment)
            await db.commit()
    except HTTPException as exc:
        await db.rollback()
        logger.warning(
            "feishu card callback rejected: task=%s user=%s status=%s detail=%s",
            task_id,
            user.username,
            exc.status_code,
            exc.detail,
        )
        if exc.status_code in (403, 404, 409):
            return _toast("warning", t("feishu.card.callback.no_pending_task", locale))
        return _toast("error", t("feishu.card.callback.failed", locale))
    except Exception:
        await db.rollback()
        logger.exception("feishu card callback failed: task=%s", task_id)
        return _toast("error", t("feishu.card.callback.failed", locale))

    result_key = {
        "approve": "approved",
        "return": "returned",
        "reject": "rejected",
    }[action]

    logger.info(
        "feishu card decision applied: task=%s action=%s actor=%s",
        task_id,
        action,
        user.username,
    )

    resp = _toast("success", t(f"feishu.card.callback.{result_key}", locale))
    resp["card"] = _build_decided_card_payload(
        instance=instance,
        pr=pr,
        decider_name=user.display_name or user.username,
        result=result_key,
        comment=comment,
        decided_at=datetime.now(UTC),
        base_url=base_url,
        locale=locale,
    )
    return resp
