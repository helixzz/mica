"""Personal access token (PAT) service.

A PAT authenticates *as its owner*: the resolved principal is the very same
``User`` row a JWT login produces, so ``require_roles``, Cerbos field policies
and row-level scoping keep working with no per-endpoint change.

Storage rules:

* only ``sha256(secret)`` is persisted — the plaintext exists in exactly one
  HTTP response, at creation time;
* ``token_prefix`` is public (it is shown in the UI and indexed so the row can
  be located before the constant-time digest comparison);
* revocation is a soft delete (``revoked_at``) so the audit trail stays intact.
"""

from __future__ import annotations

import hashlib
import hmac
import ipaddress
import logging
import secrets
import time
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from fastapi import HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import ApiToken, AuditLog, User
from app.services.system_params import system_params

logger = logging.getLogger(__name__)

settings = get_settings()

TOKEN_PREFIX = "mica_pat_"
SECRET_BYTES = 32
PREFIX_BYTES = 6  # 12 hex characters

SCOPE_READ = "read"
SCOPE_WRITE = "write"
VALID_SCOPES: tuple[str, ...] = (SCOPE_READ, SCOPE_WRITE)
SAFE_METHODS: frozenset[str] = frozenset({"GET", "HEAD", "OPTIONS"})

PARAM_MAX_PER_USER = "api.token.max_per_user"
PARAM_DEFAULT_TTL_DAYS = "api.token.default_ttl_days"
PARAM_MAX_TTL_DAYS = "api.token.max_ttl_days"
PARAM_RATE_LIMIT = "api.rate_limit_per_minute"
PARAM_AUDIT_REQUESTS = "api.audit_requests"
PARAM_READ_ONLY_POST_ALLOWLIST = "api.read_only_post_allowlist"

DEFAULT_MAX_PER_USER = 10
DEFAULT_TTL_DAYS = 90
DEFAULT_MAX_TTL_DAYS = 365
DEFAULT_RATE_LIMIT = 600
DEFAULT_READ_ONLY_POST_ALLOWLIST = "/search,/exports,/insights,/ai,/dashboard"

# Paths a PAT may never reach: admin console and identity endpoints. Credential
# and privilege changes must be made by a human in the UI, otherwise a leaked
# token could escalate itself or mint replacements faster than it can be revoked.
_BLOCKED_PATH_PREFIXES: tuple[str, ...] = ("/admin", "/saml")
_ALLOWED_AUTH_PATH = "/auth/me"

_LAST_USED_THROTTLE_SECONDS = 60.0
_RATE_WINDOW_SECONDS = 60.0

_last_used_writes: dict[str, float] = {}
_rate_buckets: dict[str, list[float]] = {}


# ── token material ───────────────────────────────────────────────────────────


def hash_secret(secret: str) -> str:
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()


def generate_token() -> tuple[str, str, str]:
    """Return ``(plaintext, prefix, digest)`` for a brand-new token."""
    random_part = secrets.token_hex(PREFIX_BYTES)
    prefix = f"{TOKEN_PREFIX}{random_part}"
    plaintext = f"{prefix}_{secrets.token_urlsafe(SECRET_BYTES)}"
    return plaintext, prefix, hash_secret(plaintext[len(prefix) + 1 :])


def looks_like_pat(raw_token: str) -> bool:
    return raw_token.startswith(TOKEN_PREFIX)


def split_token(raw_token: str) -> tuple[str, str] | None:
    """Split ``mica_pat_<prefix>_<secret>``; ``None`` when malformed."""
    if not looks_like_pat(raw_token):
        return None
    body = raw_token[len(TOKEN_PREFIX) :]
    prefix_body, separator, secret = body.partition("_")
    if not separator or not prefix_body or not secret:
        return None
    return f"{TOKEN_PREFIX}{prefix_body}", secret


def _unauthorized() -> HTTPException:
    # One message for every failure mode: unknown, malformed, revoked, expired
    # or belonging to a disabled user. Nothing here should help an attacker
    # distinguish "wrong secret" from "revoked token".
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="api_token.invalid",
        headers={"WWW-Authenticate": "Bearer"},
    )


def _as_utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def is_expired(token_row: ApiToken, *, now: datetime | None = None) -> bool:
    if token_row.expires_at is None:
        return False
    return _as_utc(token_row.expires_at) <= (now or datetime.now(UTC))


def is_active(token_row: ApiToken, *, now: datetime | None = None) -> bool:
    return token_row.revoked_at is None and not is_expired(token_row, now=now)


# ── authentication ───────────────────────────────────────────────────────────


async def authenticate(
    db: AsyncSession,
    raw_token: str,
    *,
    client_ip: str | None = None,
) -> tuple[User, ApiToken]:
    """Resolve a PAT to its owner, or raise 401."""
    parsed = split_token(raw_token)
    if parsed is None:
        raise _unauthorized()
    token_prefix, secret = parsed
    digest = hash_secret(secret)

    rows = (
        (await db.execute(select(ApiToken).where(ApiToken.token_prefix == token_prefix)))
        .scalars()
        .all()
    )
    matched: ApiToken | None = None
    for row in rows:
        if hmac.compare_digest(row.token_hash, digest):
            matched = row
            break
    if matched is None:
        raise _unauthorized()

    now = datetime.now(UTC)
    if not is_active(matched, now=now):
        raise _unauthorized()

    user = await db.get(User, matched.user_id)
    if user is None or not user.is_active:
        raise _unauthorized()

    await _touch_last_used(db, matched, now=now, client_ip=client_ip)
    return user, matched


async def _touch_last_used(
    db: AsyncSession,
    token_row: ApiToken,
    *,
    now: datetime,
    client_ip: str | None,
) -> None:
    """Record usage, throttled to one write per token per minute.

    ``last_used_at`` is how an owner decides whether a token is still in use, so
    it must be roughly right — but not at the cost of a write on every request.
    """
    key = str(token_row.id)
    last_write = _last_used_writes.get(key, 0.0)
    if now.timestamp() - last_write < _LAST_USED_THROTTLE_SECONDS:
        return
    _last_used_writes[key] = now.timestamp()
    token_row.last_used_at = now
    if client_ip:
        token_row.last_used_ip = client_ip[:64]
    try:
        # Committed, not flushed: a read-only request never commits on its own, so
        # a flushed usage record was rolled back when the session closed and
        # `last_used_at` stayed NULL forever (found by testing a real token in
        # production). Bookkeeping must not fail the request either way.
        await db.commit()
    except Exception:  # pragma: no cover - usage tracking is best effort
        logger.warning("could not record usage for API token %s", token_row.id, exc_info=True)
        await db.rollback()


# ── request guardrails ───────────────────────────────────────────────────────


def _is_private_address(host: str) -> bool:
    try:
        return ipaddress.ip_address(host).is_private
    except ValueError:
        return False


def client_ip(request: Request) -> str | None:
    """Best-effort source address for usage bookkeeping.

    Behind the bundled nginx the socket peer is the proxy container, so the first
    ``X-Forwarded-For`` hop is what the token owner wants to see. That header is
    only trusted when the direct peer is a private address, so a publicly
    reachable backend port cannot be used to forge the recorded IP.
    """
    direct = request.client.host if request.client else None
    if direct and _is_private_address(direct):
        forwarded = request.headers.get("x-forwarded-for", "")
        first = forwarded.split(",")[0].strip()
        if first:
            return first[:64]
    return direct[:64] if direct else None


def relative_path(path: str) -> str:
    """Strip the ``/api/v1`` (or ``/api/v2``) mount point for policy checks."""
    for base in (f"{settings.api_prefix}/v1", f"{settings.api_prefix}/v2"):
        if path.startswith(base):
            return path[len(base) :] or "/"
    return path


def _is_blocked(rel_path: str, method: str) -> bool:
    if rel_path.startswith(_BLOCKED_PATH_PREFIXES):
        return True
    if rel_path.startswith("/auth") and rel_path != _ALLOWED_AUTH_PATH:
        return True
    # Credential management stays human-in-the-loop: a token may list itself, but
    # it can never mint, rotate or revoke credentials — otherwise a leaked token
    # could replace itself faster than its owner could revoke it.
    return rel_path.startswith("/me/tokens") and method.upper() not in SAFE_METHODS


def _read_only_post_allowlist(raw: Any) -> tuple[str, ...]:
    if not isinstance(raw, str) or not raw.strip():
        return tuple(DEFAULT_READ_ONLY_POST_ALLOWLIST.split(","))
    return tuple(item.strip() for item in raw.split(",") if item.strip())


def _is_read_only_post(rel_path: str, allowlist: tuple[str, ...]) -> bool:
    return any(rel_path.startswith(prefix) for prefix in allowlist)


def check_rate_limit(key: str, limit: int) -> None:
    now = time.monotonic()
    bucket = [stamp for stamp in _rate_buckets.get(key, []) if now - stamp < _RATE_WINDOW_SECONDS]
    if len(bucket) >= limit:
        retry_after = int(_RATE_WINDOW_SECONDS - (now - bucket[0])) + 1
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="api_token.rate_limited",
            headers={"Retry-After": str(retry_after)},
        )
    bucket.append(now)
    _rate_buckets[key] = bucket


async def guard_request(
    db: AsyncSession,
    request: Request,
    token_row: ApiToken,
    user: User,
) -> None:
    """Apply the three PAT-only rules: rate limit, path boundary, scope."""
    limit = await system_params.get_int_or(db, PARAM_RATE_LIMIT, DEFAULT_RATE_LIMIT)
    check_rate_limit(str(token_row.id), max(limit, 1))

    rel_path = relative_path(request.url.path)
    method = request.method.upper()
    if _is_blocked(rel_path, method):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="api_token.path_forbidden",
        )

    if SCOPE_WRITE not in (token_row.scopes or []):
        if method not in SAFE_METHODS:
            allowlist = _read_only_post_allowlist(
                await system_params.get(db, PARAM_READ_ONLY_POST_ALLOWLIST, None)
            )
            if not _is_read_only_post(rel_path, allowlist):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="api_token.read_only",
                )

    if await system_params.get_bool_or(db, PARAM_AUDIT_REQUESTS, False):
        await _audit(
            db,
            actor=user,
            token_row=token_row,
            event_type="api_token.request",
            metadata={"method": request.method, "path": rel_path},
            commit=False,
        )


# ── lifecycle ────────────────────────────────────────────────────────────────


def _normalize_name(name: str) -> str:
    normalized = (name or "").strip()
    if not normalized or len(normalized) > 64:
        raise HTTPException(400, "api_token.invalid_name")
    return normalized


def _normalize_scopes(scopes: list[str] | None, *, allowed: list[str] | None) -> list[str]:
    if scopes is None:
        requested = [SCOPE_READ]
    else:
        requested = list(dict.fromkeys(scopes))
    if not requested or any(scope not in VALID_SCOPES for scope in requested):
        raise HTTPException(400, "api_token.invalid_scope")
    if allowed is not None and any(scope not in allowed for scope in requested):
        # A read-only token cannot mint a token that outranks itself.
        raise HTTPException(403, "api_token.scope_escalation")
    return requested


async def _resolve_expiry(db: AsyncSession, expires_in_days: int | None) -> datetime | None:
    max_ttl = await system_params.get_int_or(db, PARAM_MAX_TTL_DAYS, DEFAULT_MAX_TTL_DAYS)
    if expires_in_days is None:
        days = await system_params.get_int_or(db, PARAM_DEFAULT_TTL_DAYS, DEFAULT_TTL_DAYS)
    else:
        if not isinstance(expires_in_days, int) or expires_in_days < 1:
            raise HTTPException(400, "api_token.invalid_expiry")
        days = expires_in_days
    if days > max_ttl:
        raise HTTPException(400, "api_token.invalid_expiry")
    return datetime.now(UTC) + timedelta(days=days)


async def count_active_tokens(db: AsyncSession, user_id: UUID) -> int:
    total = await db.scalar(
        select(func.count())
        .select_from(ApiToken)
        .where(ApiToken.user_id == user_id, ApiToken.revoked_at.is_(None))
    )
    return int(total or 0)


async def list_tokens(db: AsyncSession, user_id: UUID) -> list[ApiToken]:
    rows = await db.execute(
        select(ApiToken).where(ApiToken.user_id == user_id).order_by(ApiToken.created_at.desc())
    )
    return list(rows.scalars().all())


async def create_token(
    db: AsyncSession,
    *,
    actor: User,
    name: str,
    scopes: list[str] | None = None,
    expires_in_days: int | None = None,
    max_scopes: list[str] | None = None,
    created_by_id: UUID | None = None,
) -> tuple[ApiToken, str]:
    """Create a token for ``actor`` and return ``(row, plaintext)``."""
    normalized_name = _normalize_name(name)
    normalized_scopes = _normalize_scopes(scopes, allowed=max_scopes)
    expires_at = await _resolve_expiry(db, expires_in_days)

    max_per_user = await system_params.get_int_or(db, PARAM_MAX_PER_USER, DEFAULT_MAX_PER_USER)
    if await count_active_tokens(db, actor.id) >= max(max_per_user, 1):
        raise HTTPException(400, "api_token.too_many")

    plaintext, prefix, digest = generate_token()
    token_row = ApiToken(
        user_id=actor.id,
        name=normalized_name,
        token_prefix=prefix,
        token_hash=digest,
        scopes=normalized_scopes,
        expires_at=expires_at,
        created_by_id=created_by_id or actor.id,
    )
    db.add(token_row)
    await db.flush()
    await _audit(
        db,
        actor=actor,
        token_row=token_row,
        event_type="api_token.created",
        metadata={
            "name": normalized_name,
            "prefix": prefix,
            "scopes": normalized_scopes,
            "expires_at": expires_at.isoformat() if expires_at else None,
            **({"created_by_admin": True} if created_by_id and created_by_id != actor.id else {}),
        },
    )
    await db.commit()
    await db.refresh(token_row)
    return token_row, plaintext


async def get_token_for_actor(
    db: AsyncSession,
    token_id: UUID,
    *,
    actor: User,
    allow_others: bool = False,
) -> ApiToken:
    token_row = await db.get(ApiToken, token_id)
    if token_row is None or (not allow_others and token_row.user_id != actor.id):
        raise HTTPException(404, "api_token.not_found")
    return token_row


async def revoke_token(
    db: AsyncSession,
    token_row: ApiToken,
    *,
    actor: User,
    event_type: str = "api_token.revoked",
) -> ApiToken:
    """Revoke a token (idempotent)."""
    if token_row.revoked_at is not None:
        return token_row
    token_row.revoked_at = datetime.now(UTC)
    await db.flush()
    await _audit(
        db,
        actor=actor,
        token_row=token_row,
        event_type=event_type,
        metadata={"name": token_row.name, "prefix": token_row.token_prefix},
    )
    await db.commit()
    await db.refresh(token_row)
    return token_row


async def rotate_token(
    db: AsyncSession,
    token_row: ApiToken,
    *,
    actor: User,
) -> tuple[ApiToken, str]:
    """Revoke ``token_row`` and issue its replacement.

    The replacement inherits name, scopes and the original expiry instant, so
    rotation never silently extends a token's lifetime.
    """
    owner = await db.get(User, token_row.user_id)
    if owner is None:
        raise HTTPException(404, "api_token.not_found")

    await revoke_token(db, token_row, actor=actor, event_type="api_token.rotated")

    plaintext, prefix, digest = generate_token()
    replacement = ApiToken(
        user_id=token_row.user_id,
        name=token_row.name,
        token_prefix=prefix,
        token_hash=digest,
        scopes=list(token_row.scopes or [SCOPE_READ]),
        expires_at=token_row.expires_at,
        created_by_id=actor.id,
    )
    db.add(replacement)
    await db.flush()
    await _audit(
        db,
        actor=actor,
        token_row=replacement,
        event_type="api_token.created",
        metadata={
            "name": replacement.name,
            "prefix": prefix,
            "scopes": list(replacement.scopes or []),
            "expires_at": replacement.expires_at.isoformat() if replacement.expires_at else None,
            "rotated_from": str(token_row.id),
        },
    )
    await db.commit()
    await db.refresh(replacement)
    return replacement, plaintext


async def list_tokens_for_admin(
    db: AsyncSession,
    *,
    user_id: UUID | None = None,
    include_revoked: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[tuple[ApiToken, User]], int]:
    conditions = []
    if user_id is not None:
        conditions.append(ApiToken.user_id == user_id)
    if not include_revoked:
        conditions.append(ApiToken.revoked_at.is_(None))

    count_stmt = select(func.count()).select_from(ApiToken)
    if conditions:
        count_stmt = count_stmt.where(*conditions)
    total = await db.scalar(count_stmt)

    stmt = (
        select(ApiToken, User)
        .join(User, User.id == ApiToken.user_id)
        .order_by(ApiToken.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    if conditions:
        stmt = stmt.where(*conditions)
    rows = (await db.execute(stmt)).all()
    return [(row[0], row[1]) for row in rows], int(total or 0)


async def _audit(
    db: AsyncSession,
    *,
    actor: User,
    token_row: ApiToken,
    event_type: str,
    metadata: dict[str, Any],
    commit: bool = True,
) -> None:
    db.add(
        AuditLog(
            actor_id=actor.id,
            actor_name=actor.display_name,
            event_type=event_type,
            resource_type="api_token",
            resource_id=str(token_row.id),
            metadata_json=metadata,
        )
    )
    await db.flush()
    if commit:
        await db.commit()
