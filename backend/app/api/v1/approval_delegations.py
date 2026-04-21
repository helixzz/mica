from __future__ import annotations

# pyright: reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownMemberType=false, reportUnknownVariableType=false
from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser, require_roles
from app.db import get_db
from app.models import ApproverDelegation
from app.schemas import ApproverDelegationAdminIn, ApproverDelegationIn, ApproverDelegationOut

router = APIRouter(prefix="/approval-delegations", tags=["approval"])
admin_router = APIRouter(
    prefix="/admin/approval-delegations",
    tags=["admin"],
    dependencies=[Depends(require_roles("admin"))],
)


def _validate_window(starts_at: datetime, ends_at: datetime) -> None:
    if starts_at >= ends_at:
        raise HTTPException(422, "approval.delegation_invalid_window")


def _normalize_dt(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _utcnow() -> datetime:
    return datetime.now(UTC)


@router.get("", response_model=list[ApproverDelegationOut])
async def list_my_delegations(
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    stmt = (
        select(ApproverDelegation)
        .where(ApproverDelegation.from_user_id == user.id)
        .order_by(ApproverDelegation.created_at.desc())
    )
    rows = (await db.execute(stmt)).scalars().all()
    return [ApproverDelegationOut.model_validate(row) for row in rows]


@router.post("", response_model=ApproverDelegationOut, status_code=status.HTTP_201_CREATED)
async def create_my_delegation(
    payload: ApproverDelegationIn,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    starts_at = _normalize_dt(payload.starts_at)
    ends_at = _normalize_dt(payload.ends_at)
    _validate_window(starts_at, ends_at)
    delegation = ApproverDelegation(
        from_user_id=user.id,
        to_user_id=payload.to_user_id,
        starts_at=starts_at,
        ends_at=ends_at,
        reason=payload.reason,
        is_active=True,
    )
    db.add(delegation)
    await db.commit()
    await db.refresh(delegation)
    return ApproverDelegationOut.model_validate(delegation)


@router.post("/{delegation_id}/revoke", response_model=ApproverDelegationOut)
async def revoke_my_delegation(
    delegation_id: UUID,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    delegation = await db.get(ApproverDelegation, delegation_id)
    if delegation is None:
        raise HTTPException(404, "approval.delegation_not_found")
    if delegation.from_user_id != user.id and user.role != "admin":
        raise HTTPException(403, "insufficient_role")
    delegation.revoked_at = _utcnow()
    delegation.is_active = False
    await db.commit()
    await db.refresh(delegation)
    return ApproverDelegationOut.model_validate(delegation)


@admin_router.get("", response_model=list[ApproverDelegationOut])
async def list_all_delegations(
    db: Annotated[AsyncSession, Depends(get_db)],
):
    rows = (
        (
            await db.execute(
                select(ApproverDelegation).order_by(ApproverDelegation.created_at.desc())
            )
        )
        .scalars()
        .all()
    )
    return [ApproverDelegationOut.model_validate(row) for row in rows]


@admin_router.post("", response_model=ApproverDelegationOut, status_code=status.HTTP_201_CREATED)
async def create_delegation_admin(
    payload: ApproverDelegationAdminIn,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    _ = user
    starts_at = _normalize_dt(payload.starts_at)
    ends_at = _normalize_dt(payload.ends_at)
    _validate_window(starts_at, ends_at)
    delegation = ApproverDelegation(
        from_user_id=payload.from_user_id,
        to_user_id=payload.to_user_id,
        starts_at=starts_at,
        ends_at=ends_at,
        reason=payload.reason,
        is_active=payload.is_active,
    )
    db.add(delegation)
    await db.commit()
    await db.refresh(delegation)
    return ApproverDelegationOut.model_validate(delegation)


@admin_router.post("/{delegation_id}/revoke", response_model=ApproverDelegationOut)
async def revoke_delegation_admin(
    delegation_id: UUID,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    _ = user
    delegation = await db.get(ApproverDelegation, delegation_id)
    if delegation is None:
        raise HTTPException(404, "approval.delegation_not_found")
    delegation.revoked_at = _utcnow()
    delegation.is_active = False
    await db.commit()
    await db.refresh(delegation)
    return ApproverDelegationOut.model_validate(delegation)
