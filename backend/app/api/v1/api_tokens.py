"""Personal access token (PAT) endpoints.

Self-service token management for every signed-in user, plus an admin read/revoke
view. Tokens authenticate as their owner, so these endpoints add *credential*
management — not a second permission system.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser, require_roles
from app.db import get_db
from app.models import ApiToken, User
from app.services import api_tokens as api_token_svc

router = APIRouter()
admin_router = APIRouter()


class ApiTokenOut(BaseModel):
    id: UUID
    name: str
    prefix: str
    scopes: list[str]
    expires_at: datetime | None
    revoked_at: datetime | None
    last_used_at: datetime | None
    last_used_ip: str | None
    created_at: datetime
    is_expired: bool
    is_active: bool


class ApiTokenCreatedOut(ApiTokenOut):
    # Present in this response and nowhere else, ever.
    token: str


class AdminApiTokenOut(ApiTokenOut):
    user_id: UUID
    username: str
    user_display_name: str


class ApiTokenListOut(BaseModel):
    items: list[AdminApiTokenOut]
    total: int


class ApiTokenCreateIn(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    scopes: list[Literal["read", "write"]] | None = None
    expires_in_days: int | None = Field(default=None, ge=1)


def _to_out(row: ApiToken) -> ApiTokenOut:
    return ApiTokenOut(
        id=row.id,
        name=row.name,
        prefix=row.token_prefix,
        scopes=list(row.scopes or []),
        expires_at=row.expires_at,
        revoked_at=row.revoked_at,
        last_used_at=row.last_used_at,
        last_used_ip=row.last_used_ip,
        created_at=row.created_at,
        is_expired=api_token_svc.is_expired(row),
        is_active=api_token_svc.is_active(row),
    )


def _to_created(row: ApiToken, plaintext: str) -> ApiTokenCreatedOut:
    return ApiTokenCreatedOut(**_to_out(row).model_dump(), token=plaintext)


def _caller_scopes(request: Request) -> list[str] | None:
    """Scope ceiling for this request: a PAT cannot mint beyond its own scopes."""
    return getattr(request.state, "api_token_scopes", None)


@router.get("/me/tokens", response_model=list[ApiTokenOut], tags=["api-tokens"])
async def list_my_tokens(
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[ApiTokenOut]:
    rows = await api_token_svc.list_tokens(db, user.id)
    return [_to_out(row) for row in rows]


@router.post(
    "/me/tokens",
    response_model=ApiTokenCreatedOut,
    status_code=201,
    tags=["api-tokens"],
)
async def create_my_token(
    request: Request,
    payload: ApiTokenCreateIn,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiTokenCreatedOut:
    row, plaintext = await api_token_svc.create_token(
        db,
        actor=user,
        name=payload.name,
        scopes=list(payload.scopes) if payload.scopes else None,
        expires_in_days=payload.expires_in_days,
        max_scopes=_caller_scopes(request),
    )
    return _to_created(row, plaintext)


@router.post(
    "/me/tokens/{token_id}/rotate",
    response_model=ApiTokenCreatedOut,
    status_code=201,
    tags=["api-tokens"],
)
async def rotate_my_token(
    request: Request,
    token_id: UUID,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiTokenCreatedOut:
    row = await api_token_svc.get_token_for_actor(db, token_id, actor=user)
    ceiling = _caller_scopes(request)
    if ceiling is not None and any(scope not in ceiling for scope in (row.scopes or [])):
        # A read-only PAT must not be able to re-issue a write token.
        raise HTTPException(403, "api_token.scope_escalation")
    replacement, plaintext = await api_token_svc.rotate_token(db, row, actor=user)
    return _to_created(replacement, plaintext)


@router.delete("/me/tokens/{token_id}", status_code=204, tags=["api-tokens"])
async def revoke_my_token(
    token_id: UUID,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    row = await api_token_svc.get_token_for_actor(db, token_id, actor=user)
    await api_token_svc.revoke_token(db, row, actor=user)


@admin_router.get("/admin/api-tokens", response_model=ApiTokenListOut, tags=["admin"])
async def list_all_tokens(
    _admin: Annotated[User, Depends(require_roles("admin"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[UUID | None, Query()] = None,
    include_revoked: Annotated[bool, Query()] = False,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ApiTokenListOut:
    rows, total = await api_token_svc.list_tokens_for_admin(
        db,
        user_id=user_id,
        include_revoked=include_revoked,
        limit=limit,
        offset=offset,
    )
    return ApiTokenListOut(
        items=[
            AdminApiTokenOut(
                **_to_out(token_row).model_dump(),
                user_id=owner.id,
                username=owner.username,
                user_display_name=owner.display_name,
            )
            for token_row, owner in rows
        ],
        total=total,
    )


@admin_router.delete("/admin/api-tokens/{token_id}", status_code=204, tags=["admin"])
async def revoke_any_token(
    token_id: UUID,
    admin: Annotated[User, Depends(require_roles("admin"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    row = await api_token_svc.get_token_for_actor(db, token_id, actor=admin, allow_others=True)
    await api_token_svc.revoke_token(db, row, actor=admin)
