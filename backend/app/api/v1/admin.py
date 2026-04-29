"""Admin console backend: system params, AI model CRUD, feature routing CRUD,
audit log, AI call log, user management. Restricted to admin role.
"""

from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Annotated, Any, Literal, cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.core.crypto import decrypt, encrypt
from app.core.litellm_helpers import resolve_litellm_model
from app.core.security import CurrentUser, hash_password, require_roles
from app.db import get_db
from app.models import (
    AICallLog,
    AIFeatureRouting,
    AIModel,
    AuditLog,
    JSONValue,
    User,
    UserRole,
)
from app.services import notifications as notification_svc
from app.services.system_params import system_params

router = APIRouter(prefix="/admin", dependencies=[Depends(require_roles("admin"))])
settings = get_settings()


@router.get("/system", tags=["admin"])
async def system_info(user: CurrentUser):
    return {
        "app_name": settings.app_name,
        "app_env": settings.app_env,
        "app_version": settings.app_version,
        "default_locale": settings.default_locale,
        "supported_locales": settings.supported_locales,
        "download_token_ttl_seconds": settings.download_token_ttl_seconds,
        "media_root_set": bool(settings.media_root),
    }


class AIModelIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    provider: str = Field(..., max_length=32)
    model_string: str = Field(..., max_length=128)
    modality: Literal["text", "vision", "ocr", "embedding"] = "text"
    api_base: str | None = None
    api_key: str | None = None
    timeout_s: int = 60
    is_active: bool = True
    priority: int = 100
    capabilities: dict[str, JSONValue] | None = None


class AIModelOutDetailed(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    provider: str
    model_string: str
    modality: str
    api_base: str | None
    api_key_masked: str | None = None
    timeout_s: int
    is_active: bool
    priority: int
    capabilities: dict[str, JSONValue] | None
    created_at: datetime
    updated_at: datetime


def _mask_key(encrypted_key: str | None) -> str | None:
    if not encrypted_key:
        return None
    try:
        raw = decrypt(encrypted_key)
    except Exception:
        return "********"
    if not raw:
        return "********"
    if len(raw) < 10:
        return "****"
    return f"{raw[:4]}****{raw[-4:]}"


def _serialize_model(m: AIModel) -> AIModelOutDetailed:
    data = AIModelOutDetailed.model_validate(m)
    data.api_key_masked = _mask_key(m.api_key_encrypted)
    return data


@router.get("/ai-models", tags=["admin"])
async def list_ai_models(
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    rows = (
        (await db.execute(select(AIModel).order_by(AIModel.priority, AIModel.name))).scalars().all()
    )
    return [_serialize_model(m) for m in rows]


@router.post("/ai-models", status_code=201, tags=["admin"])
async def create_ai_model(
    payload: AIModelIn,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    existing = (
        await db.execute(select(AIModel).where(AIModel.name == payload.name))
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(409, "ai_model.name_exists")
    m = AIModel(
        name=payload.name,
        provider=payload.provider,
        model_string=payload.model_string,
        modality=payload.modality,
        api_base=payload.api_base,
        api_key_encrypted=encrypt(payload.api_key) if payload.api_key else None,
        timeout_s=payload.timeout_s,
        is_active=payload.is_active,
        priority=payload.priority,
        capabilities=payload.capabilities,
    )
    db.add(m)
    db.add(
        AuditLog(
            actor_id=user.id,
            actor_name=user.display_name,
            event_type="admin.ai_model.created",
            resource_type="ai_model",
            resource_id=str(m.id),
            metadata_json={"name": m.name, "provider": m.provider},
        )
    )
    await db.commit()
    await db.refresh(m)
    return _serialize_model(m)


@router.patch("/ai-models/{model_id}", tags=["admin"])
async def update_ai_model(
    model_id: UUID,
    payload: AIModelIn,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    m = await db.get(AIModel, model_id)
    if m is None:
        raise HTTPException(404, "ai_model.not_found")
    m.name = payload.name
    m.provider = payload.provider
    m.model_string = payload.model_string
    m.modality = payload.modality
    m.api_base = payload.api_base
    m.timeout_s = payload.timeout_s
    m.is_active = payload.is_active
    m.priority = payload.priority
    m.capabilities = payload.capabilities
    if payload.api_key:
        m.api_key_encrypted = encrypt(payload.api_key)
    db.add(
        AuditLog(
            actor_id=user.id,
            actor_name=user.display_name,
            event_type="admin.ai_model.updated",
            resource_type="ai_model",
            resource_id=str(m.id),
        )
    )
    await db.commit()
    await db.refresh(m)
    return _serialize_model(m)


@router.delete("/ai-models/{model_id}", status_code=204, tags=["admin"])
async def delete_ai_model(
    model_id: UUID,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    m = await db.get(AIModel, model_id)
    if m is None:
        raise HTTPException(404, "ai_model.not_found")

    referencing_routings = (
        (
            await db.execute(
                select(AIFeatureRouting).where(AIFeatureRouting.primary_model_id == model_id)
            )
        )
        .scalars()
        .all()
    )
    for routing in referencing_routings:
        routing.primary_model_id = None

    all_routings = (
        (
            await db.execute(
                select(AIFeatureRouting).where(AIFeatureRouting.fallback_model_ids.isnot(None))
            )
        )
        .scalars()
        .all()
    )
    model_id_str = str(model_id)
    for routing in all_routings:
        if routing.fallback_model_ids and model_id_str in routing.fallback_model_ids:
            routing.fallback_model_ids = [
                fid for fid in routing.fallback_model_ids if fid != model_id_str
            ]

    await db.flush()
    await db.delete(m)
    db.add(
        AuditLog(
            actor_id=user.id,
            actor_name=user.display_name,
            event_type="admin.ai_model.deleted",
            resource_type="ai_model",
            resource_id=str(model_id),
        )
    )
    await db.commit()


@router.post("/ai-models/{model_id}/test-connection", tags=["admin"])
async def test_ai_model_connection(
    model_id: UUID,
    _user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    m = await db.get(AIModel, model_id)
    if m is None:
        raise HTTPException(404, "ai_model.not_found")

    start = time.monotonic()
    try:
        if m.provider == "mock":
            sample = "pong"
            latency_ms = int((time.monotonic() - start) * 1000)
            return {
                "success": True,
                "model_response": f"[mock] {sample}",
                "latency_ms": latency_ms,
                "error": None,
            }

        resolved_model = resolve_litellm_model(m.provider, m.model_string)
        common_kwargs: dict[str, Any] = {
            "model": resolved_model,
            "timeout": max(3, min(m.timeout_s, 30)),
        }
        if m.api_key_encrypted:
            common_kwargs["api_key"] = decrypt(m.api_key_encrypted)
        if m.api_base:
            common_kwargs["api_base"] = m.api_base

        if m.modality == "embedding":
            from litellm import aembedding

            resp = cast(
                object,
                await aembedding(
                    input=["ping"],
                    encoding_format="float",
                    **common_kwargs,
                ),
            )
            latency_ms = int((time.monotonic() - start) * 1000)
            data = getattr(resp, "data", None) or []
            dim = 0
            if data:
                emb = getattr(data[0], "embedding", None) or data[0].get("embedding", [])  # type: ignore[union-attr]
                dim = len(emb) if emb else 0
            return {
                "success": True,
                "model_response": f"[embedding] dim={dim}",
                "latency_ms": latency_ms,
                "error": None,
            }

        from litellm import acompletion

        resp = cast(
            object,
            await acompletion(
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=8,
                **common_kwargs,
            ),
        )
        latency_ms = int((time.monotonic() - start) * 1000)
        choices = getattr(resp, "choices", None)
        if isinstance(choices, list) and choices:
            message = getattr(choices[0], "message", None)
            content = str(getattr(message, "content", "") or "")
        else:
            content = str(resp)
        return {
            "success": True,
            "model_response": content[:200],
            "latency_ms": latency_ms,
            "error": None,
        }
    except Exception as e:
        return {
            "success": False,
            "model_response": None,
            "latency_ms": int((time.monotonic() - start) * 1000),
            "error": str(e)[:400],
        }


class AIFeatureRoutingIn(BaseModel):
    feature_code: str = Field(..., min_length=1, max_length=64)
    primary_model_id: UUID | None = None
    fallback_model_ids: list[UUID] | None = None
    prompt_template: str | None = None
    temperature: Decimal = Decimal("0.30")
    max_tokens: int = 1024
    enabled: bool = True


class AIFeatureRoutingOutAdmin(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    feature_code: str
    primary_model_id: UUID | None
    fallback_model_ids: list[UUID] | None
    prompt_template: str | None
    temperature: Decimal
    max_tokens: int
    enabled: bool


@router.get("/ai-routings", tags=["admin"])
async def list_routings(
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    rows = (
        (await db.execute(select(AIFeatureRouting).order_by(AIFeatureRouting.feature_code)))
        .scalars()
        .all()
    )
    return [AIFeatureRoutingOutAdmin.model_validate(r) for r in rows]


@router.put("/ai-routings/{feature_code}", tags=["admin"])
async def upsert_routing(
    feature_code: str,
    payload: AIFeatureRoutingIn,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    row = (
        await db.execute(
            select(AIFeatureRouting).where(AIFeatureRouting.feature_code == feature_code)
        )
    ).scalar_one_or_none()
    fallback_ids_raw = [str(i) for i in (payload.fallback_model_ids or [])]
    if row is None:
        row = AIFeatureRouting(
            feature_code=feature_code,
            primary_model_id=payload.primary_model_id,
            fallback_model_ids=fallback_ids_raw,
            prompt_template=payload.prompt_template,
            temperature=payload.temperature,
            max_tokens=payload.max_tokens,
            enabled=payload.enabled,
        )
        db.add(row)
    else:
        row.primary_model_id = payload.primary_model_id
        row.fallback_model_ids = fallback_ids_raw
        row.prompt_template = payload.prompt_template
        row.temperature = payload.temperature
        row.max_tokens = payload.max_tokens
        row.enabled = payload.enabled
    db.add(
        AuditLog(
            actor_id=user.id,
            actor_name=user.display_name,
            event_type="admin.ai_routing.upserted",
            resource_type="ai_feature_routing",
            resource_id=feature_code,
        )
    )
    await db.commit()
    await db.refresh(row)
    return AIFeatureRoutingOutAdmin.model_validate(row)


class UserCreateIn(BaseModel):
    username: str = Field(..., min_length=1, max_length=64)
    email: str
    display_name: str
    password: str = Field(..., min_length=8)
    role: Literal[
        "admin", "requester", "it_buyer", "dept_manager", "finance_auditor", "procurement_mgr"
    ]
    company_id: UUID
    department_id: UUID | None = None
    cost_center_ids: list[UUID] = Field(default_factory=list)
    department_ids: list[UUID] = Field(default_factory=list)
    preferred_locale: str = "zh-CN"


class PasswordResetIn(BaseModel):
    new_password: str = Field(..., min_length=8)


class UserOutAdmin(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    username: str
    email: str
    display_name: str
    role: str
    company_id: UUID
    company_code: str | None = None
    company_name_zh: str | None = None
    department_id: UUID | None
    department_code: str | None = None
    department_name_zh: str | None = None
    cost_center_ids: list[UUID] = Field(default_factory=list)
    department_ids: list[UUID] = Field(default_factory=list)
    preferred_locale: str
    is_active: bool
    is_local_admin: bool
    auth_provider: str
    last_login_at: datetime | None
    created_at: datetime


def _user_to_admin_out(u: User) -> UserOutAdmin:
    return UserOutAdmin(
        id=u.id,
        username=u.username,
        email=u.email,
        display_name=u.display_name,
        role=u.role,
        company_id=u.company_id,
        company_code=u.company.code if u.company else None,
        company_name_zh=u.company.name_zh if u.company else None,
        department_id=u.department_id,
        department_code=u.department.code if u.department else None,
        department_name_zh=u.department.name_zh if u.department else None,
        cost_center_ids=[],
        department_ids=[],
        preferred_locale=u.preferred_locale,
        is_active=u.is_active,
        is_local_admin=u.is_local_admin,
        auth_provider=u.auth_provider,
        last_login_at=u.last_login_at,
        created_at=u.created_at,
    )


async def _user_to_admin_out_with_m2m(db, u: User) -> UserOutAdmin:
    from app.models import user_cost_centers, user_departments

    cc_rows = (
        (
            await db.execute(
                select(user_cost_centers.c.cost_center_id).where(
                    user_cost_centers.c.user_id == u.id
                )
            )
        )
        .scalars()
        .all()
    )
    dep_rows = (
        (
            await db.execute(
                select(user_departments.c.department_id).where(user_departments.c.user_id == u.id)
            )
        )
        .scalars()
        .all()
    )

    out = _user_to_admin_out(u)
    out.cost_center_ids = list(cc_rows)
    out.department_ids = list(dep_rows)
    return out


@router.get("/users", tags=["admin"])
async def list_users(
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    rows = (
        (
            await db.execute(
                select(User)
                .order_by(User.username)
                .options(selectinload(User.company), selectinload(User.department))
            )
        )
        .scalars()
        .all()
    )
    out = []
    for u in rows:
        out.append(await _user_to_admin_out_with_m2m(db, u))
    return out


@router.post("/users", status_code=201, tags=["admin"])
async def create_user(
    payload: UserCreateIn,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    existing = (
        await db.execute(select(User).where(User.username == payload.username))
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(409, "user.username_exists")
    u = User(
        username=payload.username,
        email=payload.email,
        display_name=payload.display_name,
        password_hash=hash_password(payload.password),
        role=payload.role,
        company_id=payload.company_id,
        department_id=payload.department_id,
        preferred_locale=payload.preferred_locale,
    )
    db.add(u)
    await db.flush()

    if payload.cost_center_ids:
        from app.models import user_cost_centers

        for cc_id in payload.cost_center_ids:
            await db.execute(user_cost_centers.insert().values(user_id=u.id, cost_center_id=cc_id))
    if payload.department_ids:
        from app.models import user_departments

        for dep_id in payload.department_ids:
            await db.execute(user_departments.insert().values(user_id=u.id, department_id=dep_id))

    db.add(
        AuditLog(
            actor_id=user.id,
            actor_name=user.display_name,
            event_type="admin.user.created",
            resource_type="user",
            resource_id=str(u.id),
            metadata_json={"username": u.username, "role": u.role},
        )
    )
    await db.commit()
    await db.refresh(u, attribute_names=["company", "department"])
    return await _user_to_admin_out_with_m2m(db, u)


@router.post("/users/{user_id}/reset-password", status_code=204, tags=["admin"])
async def reset_user_password(
    user_id: UUID,
    payload: PasswordResetIn,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    u = await db.get(User, user_id)
    if u is None:
        raise HTTPException(404, "user.not_found")
    u.password_hash = hash_password(payload.new_password)
    db.add(
        AuditLog(
            actor_id=user.id,
            actor_name=user.display_name,
            event_type="admin.user.password_reset",
            resource_type="user",
            resource_id=str(user_id),
        )
    )
    await db.commit()


@router.delete("/users/{user_id}", status_code=204, tags=["admin"])
async def delete_user(
    user_id: UUID,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    _role: Annotated[None, Depends(require_roles("admin"))],
) -> Response:
    target = await db.get(User, user_id)
    if target is None:
        raise HTTPException(404, "user.not_found")
    if target.id == user.id:
        raise HTTPException(409, "user.cannot_delete_self")

    if target.role == UserRole.ADMIN.value:
        remaining_admins = (
            await db.execute(
                select(func.count(User.id)).where(
                    User.role == UserRole.ADMIN.value,
                    User.is_active.is_(True),
                    User.id != target.id,
                )
            )
        ).scalar_one()
        if remaining_admins == 0:
            raise HTTPException(409, "user.cannot_delete_last_admin")

    username = target.username
    display_name = target.display_name
    role = target.role
    try:
        await db.delete(target)
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, "user.has_references") from None

    db.add(
        AuditLog(
            actor_id=user.id,
            actor_name=user.display_name,
            event_type="admin.user.deleted",
            resource_type="user",
            resource_id=str(user_id),
            metadata_json={
                "username": username,
                "display_name": display_name,
                "role": role,
            },
        )
    )
    await db.commit()
    return Response(status_code=204)


class UserUpdateIn(BaseModel):
    display_name: str | None = None
    email: str | None = None
    role: (
        Literal[
            "admin", "requester", "it_buyer", "dept_manager", "finance_auditor", "procurement_mgr"
        ]
        | None
    ) = None
    company_id: UUID | None = None
    department_id: UUID | None = None
    cost_center_ids: list[UUID] | None = None
    department_ids: list[UUID] | None = None
    preferred_locale: str | None = None
    is_active: bool | None = None


@router.patch("/users/{user_id}", tags=["admin"])
async def update_user(
    user_id: UUID,
    payload: UserUpdateIn,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    from sqlalchemy import delete as sqla_delete

    from app.models import user_cost_centers, user_departments

    u = await db.get(User, user_id)
    if u is None:
        raise HTTPException(404, "user.not_found")
    changes: dict[str, object] = {}
    for field_name in payload.model_fields_set:
        if field_name in ("cost_center_ids", "department_ids"):
            continue
        new_val = getattr(payload, field_name)
        if new_val is not None or field_name == "department_id":
            old_val = getattr(u, field_name)
            if old_val != new_val:
                changes[field_name] = {"old": str(old_val), "new": str(new_val)}
                setattr(u, field_name, new_val)

    if payload.cost_center_ids is not None:
        await db.execute(
            sqla_delete(user_cost_centers).where(user_cost_centers.c.user_id == user_id)
        )
        for cc_id in payload.cost_center_ids:
            await db.execute(
                user_cost_centers.insert().values(user_id=user_id, cost_center_id=cc_id)
            )
        changes["cost_center_ids"] = {"old": "...", "new": str(payload.cost_center_ids)}

    if payload.department_ids is not None:
        await db.execute(sqla_delete(user_departments).where(user_departments.c.user_id == user_id))
        for dep_id in payload.department_ids:
            await db.execute(
                user_departments.insert().values(user_id=user_id, department_id=dep_id)
            )
        changes["department_ids"] = {"old": "...", "new": str(payload.department_ids)}

    if changes:
        db.add(
            AuditLog(
                actor_id=user.id,
                actor_name=user.display_name,
                event_type="admin.user.updated",
                resource_type="user",
                resource_id=str(user_id),
                metadata_json=changes,
            )
        )
        await db.commit()
        await db.refresh(u)
    await db.refresh(u, attribute_names=["company", "department"])
    return await _user_to_admin_out_with_m2m(db, u)


@router.get("/audit-logs", tags=["admin"])
async def list_audit_logs(
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = 100,
    event_type_prefix: str | None = None,
    resource_type: str | None = None,
    since_days: int | None = None,
):
    resolved_since_days = (
        since_days
        if since_days is not None
        else await system_params.get_int_or(db, "audit.default_lookback_days", 7)
    )
    since = datetime.now(UTC) - timedelta(days=resolved_since_days)
    stmt = (
        select(AuditLog)
        .where(AuditLog.occurred_at >= since)
        .order_by(AuditLog.occurred_at.desc())
        .limit(min(limit, 500))
    )
    if event_type_prefix:
        stmt = stmt.where(AuditLog.event_type.startswith(event_type_prefix))
    if resource_type:
        stmt = stmt.where(AuditLog.resource_type == resource_type)
    rows = (await db.execute(stmt)).scalars().all()
    return [
        {
            "id": str(r.id),
            "occurred_at": r.occurred_at.isoformat(),
            "actor_name": r.actor_name,
            "event_type": r.event_type,
            "resource_type": r.resource_type,
            "resource_id": r.resource_id,
            "comment": r.comment,
            "metadata": r.metadata_json,
        }
        for r in rows
    ]


@router.get("/ai-call-logs", tags=["admin"])
async def list_ai_call_logs(
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = 100,
    feature_code: str | None = None,
    since_days: int | None = None,
):
    resolved_since_days = (
        since_days
        if since_days is not None
        else await system_params.get_int_or(db, "audit.default_lookback_days", 7)
    )
    since = datetime.now(UTC) - timedelta(days=resolved_since_days)
    stmt = (
        select(AICallLog)
        .where(AICallLog.occurred_at >= since)
        .order_by(AICallLog.occurred_at.desc())
        .limit(min(limit, 500))
    )
    if feature_code:
        stmt = stmt.where(AICallLog.feature_code == feature_code)
    rows = (await db.execute(stmt)).scalars().all()
    return [
        {
            "id": str(r.id),
            "occurred_at": r.occurred_at.isoformat(),
            "feature_code": r.feature_code,
            "user_id": str(r.user_id) if r.user_id else None,
            "model_name": r.model_name,
            "provider": r.provider,
            "prompt_tokens": r.prompt_tokens,
            "completion_tokens": r.completion_tokens,
            "latency_ms": r.latency_ms,
            "status": r.status,
            "error": r.error,
        }
        for r in rows
    ]


@router.get("/ai-call-stats", tags=["admin"])
async def ai_call_stats(
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    since_days: int | None = None,
):
    resolved_since_days = (
        since_days
        if since_days is not None
        else await system_params.get_int_or(db, "audit.default_lookback_days", 7)
    )
    since = datetime.now(UTC) - timedelta(days=resolved_since_days)
    rows = (
        await db.execute(
            select(
                AICallLog.feature_code,
                func.count().label("total"),
                func.sum(AICallLog.prompt_tokens + AICallLog.completion_tokens).label("tokens"),
                func.avg(AICallLog.latency_ms).label("avg_latency_ms"),
            )
            .where(AICallLog.occurred_at >= since)
            .group_by(AICallLog.feature_code)
        )
    ).all()
    return [
        {
            "feature_code": r.feature_code,
            "total_calls": int(r.total or 0),
            "total_tokens": int(r.tokens or 0),
            "avg_latency_ms": float(r.avg_latency_ms or 0),
        }
        for r in rows
    ]


# === Notification triggers ===


@router.post("/notifications/run-contract-expiring", tags=["admin"])
async def run_contract_expiring_notifications(
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    within_days: int = 30,
):
    return await notification_svc.notify_expiring_contracts(db, within_days=within_days)


@router.post("/notifications/run-price-anomaly", tags=["admin"])
async def run_price_anomaly_notifications(
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await notification_svc.notify_new_price_anomalies(db)


# === Feishu integration settings ===


class FeishuSettingsOut(BaseModel):
    app_id: str = ""
    app_secret: str = ""  # always empty in response — user must re-enter to change
    app_secret_masked: str = ""
    enabled: bool = False
    notify_on_pr: bool = True
    notify_on_approval: bool = True
    notify_on_po: bool = True
    notify_on_payment: bool = True
    notify_on_contract_expiry: bool = True
    payment_workflow: bool = False
    approval_code: str = ""


class FeishuSettingsIn(BaseModel):
    app_id: str | None = None
    app_secret: str | None = None
    enabled: bool | None = None
    notify_on_pr: bool | None = None
    notify_on_approval: bool | None = None
    notify_on_po: bool | None = None
    notify_on_payment: bool | None = None
    notify_on_contract_expiry: bool | None = None
    payment_workflow: bool | None = None
    approval_code: str | None = None


def _mask_secret(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "****"
    return f"{value[:4]}****{value[-4:]}"


@router.get("/feishu/settings", tags=["admin"])
async def get_feishu_settings(
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> FeishuSettingsOut:
    return FeishuSettingsOut(
        app_id=str(await system_params.get(db, "auth.feishu.app_id", "")),
        app_secret="",  # never return real secret — user re-enters to change
        app_secret_masked=_mask_secret(
            str(await system_params.get(db, "auth.feishu.app_secret", ""))
        ),
        enabled=bool(await system_params.get(db, "auth.feishu.enabled", False)),
        notify_on_pr=bool(await system_params.get(db, "auth.feishu.notify_on_pr", True)),
        notify_on_approval=bool(
            await system_params.get(db, "auth.feishu.notify_on_approval", True)
        ),
        notify_on_po=bool(await system_params.get(db, "auth.feishu.notify_on_po", True)),
        notify_on_payment=bool(await system_params.get(db, "auth.feishu.notify_on_payment", True)),
        notify_on_contract_expiry=bool(
            await system_params.get(db, "auth.feishu.notify_on_contract_expiry", True)
        ),
        payment_workflow=bool(await system_params.get(db, "auth.feishu.payment_workflow", False)),
        approval_code=str(await system_params.get(db, "auth.feishu.approval_code", "")),
    )


@router.put("/feishu/settings", tags=["admin"])
async def update_feishu_settings(
    payload: FeishuSettingsIn,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> FeishuSettingsOut:
    updates: dict[str, Any] = {}
    if payload.app_id is not None:
        updates["auth.feishu.app_id"] = payload.app_id
    if payload.app_secret is not None and payload.app_secret:
        updates["auth.feishu.app_secret"] = payload.app_secret
    if payload.enabled is not None:
        updates["auth.feishu.enabled"] = payload.enabled
    if payload.notify_on_pr is not None:
        updates["auth.feishu.notify_on_pr"] = payload.notify_on_pr
    if payload.notify_on_approval is not None:
        updates["auth.feishu.notify_on_approval"] = payload.notify_on_approval
    if payload.notify_on_po is not None:
        updates["auth.feishu.notify_on_po"] = payload.notify_on_po
    if payload.notify_on_payment is not None:
        updates["auth.feishu.notify_on_payment"] = payload.notify_on_payment
    if payload.notify_on_contract_expiry is not None:
        updates["auth.feishu.notify_on_contract_expiry"] = payload.notify_on_contract_expiry
    if payload.payment_workflow is not None:
        updates["auth.feishu.payment_workflow"] = payload.payment_workflow
    if payload.approval_code is not None:
        updates["auth.feishu.approval_code"] = payload.approval_code

    for key, value in updates.items():
        await system_params.update(db, key, value, str(user.id))

    return await get_feishu_settings(user=user, db=db)


@router.post("/feishu/test", tags=["admin"])
async def test_feishu_connection(
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    from app.services.feishu.client import FeishuClient, FeishuError

    client = FeishuClient(db)
    try:
        await client._ensure_token()
        if not user.email:
            return {"success": False, "error": "admin user has no email"}

        feishu_user = await client.get_user_by_email(user.email)
        if not feishu_user:
            return {
                "success": True,
                "token_ok": True,
                "message_sent": False,
                "error": "feishu.test.user_not_found",
            }

        receive_id = feishu_user.get("open_id", "")
        if not receive_id:
            return {
                "success": True,
                "token_ok": True,
                "message_sent": False,
                "error": "feishu.test.no_open_id",
            }

        from app.services.feishu import messages as feishu_messages

        card = feishu_messages.build_pr_submitted_card(
            pr_title="测试消息 - Mica 飞书集成",
            applicant=user.display_name,
            department="系统管理",
            amount="¥0.00",
            line_count=1,
            pr_url="",
        )
        await client.send_card("open_id", receive_id, card)
        return {"success": True, "token_ok": True, "message_sent": True, "error": None}
    except FeishuError as e:
        return {"success": False, "token_ok": False, "message_sent": False, "error": str(e)}
    except Exception as e:
        return {"success": False, "token_ok": False, "message_sent": False, "error": str(e)}
    finally:
        await client.close()
