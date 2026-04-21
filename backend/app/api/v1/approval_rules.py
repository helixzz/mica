from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser, require_roles
from app.db import get_db
from app.models import ApprovalRule
from app.schemas import ApprovalRuleIn, ApprovalRuleOut

router = APIRouter(
    prefix="/approval-rules",
    tags=["approval"],
    dependencies=[Depends(require_roles("admin"))],
)


def _normalize_stages(payload: ApprovalRuleIn) -> list[dict[str, object]]:
    stages = sorted(payload.stages, key=lambda item: (item.order, item.stage_name))
    return [stage.model_dump() for stage in stages]


@router.get("", response_model=list[ApprovalRuleOut])
async def list_approval_rules(
    db: Annotated[AsyncSession, Depends(get_db)],
    biz_type: str | None = None,
    is_active: bool | None = None,
):
    stmt = select(ApprovalRule).order_by(ApprovalRule.priority, ApprovalRule.created_at)
    if biz_type:
        stmt = stmt.where(ApprovalRule.biz_type == biz_type)
    if is_active is not None:
        stmt = stmt.where(ApprovalRule.is_active.is_(is_active))
    rows = (await db.execute(stmt)).scalars().all()
    return [ApprovalRuleOut.model_validate(row) for row in rows]


@router.post("", response_model=ApprovalRuleOut, status_code=status.HTTP_201_CREATED)
async def create_approval_rule(
    payload: ApprovalRuleIn,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    _ = user
    rule = ApprovalRule(
        name=payload.name,
        biz_type=payload.biz_type,
        amount_min=payload.amount_min,
        amount_max=payload.amount_max,
        stages=_normalize_stages(payload),
        is_active=payload.is_active,
        priority=payload.priority,
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return ApprovalRuleOut.model_validate(rule)


@router.get("/{rule_id}", response_model=ApprovalRuleOut)
async def get_approval_rule(
    rule_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    rule = await db.get(ApprovalRule, rule_id)
    if rule is None:
        raise HTTPException(404, "approval.rule_not_found")
    return ApprovalRuleOut.model_validate(rule)


@router.put("/{rule_id}", response_model=ApprovalRuleOut)
async def update_approval_rule(
    rule_id: UUID,
    payload: ApprovalRuleIn,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    _ = user
    rule = await db.get(ApprovalRule, rule_id)
    if rule is None:
        raise HTTPException(404, "approval.rule_not_found")
    rule.name = payload.name
    rule.biz_type = payload.biz_type
    rule.amount_min = payload.amount_min
    rule.amount_max = payload.amount_max
    rule.stages = _normalize_stages(payload)
    rule.is_active = payload.is_active
    rule.priority = payload.priority
    await db.commit()
    await db.refresh(rule)
    return ApprovalRuleOut.model_validate(rule)


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_approval_rule(
    rule_id: UUID,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    _ = user
    rule = await db.get(ApprovalRule, rule_id)
    if rule is None:
        raise HTTPException(404, "approval.rule_not_found")
    await db.delete(rule)
    await db.commit()
