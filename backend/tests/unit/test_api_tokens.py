"""Unit tests for the personal access token service."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from app.models import ApiToken, AuditLog, User
from app.services import api_tokens as svc


async def _user(db: AsyncSession, username: str = "alice") -> User:
    return (await db.execute(select(User).where(User.username == username))).scalar_one()


def _request(method: str = "GET", path: str = "/api/v1/purchase-requisitions") -> Request:
    return Request(
        {
            "type": "http",
            "method": method,
            "path": path,
            "headers": [],
            "query_string": b"",
            "client": ("127.0.0.1", 51234),
        }
    )


def test_generate_token_shape_and_hash() -> None:
    plaintext, prefix, digest = svc.generate_token()

    assert plaintext.startswith(svc.TOKEN_PREFIX)
    assert plaintext.startswith(f"{prefix}_")
    parsed = svc.split_token(plaintext)
    assert parsed is not None
    assert parsed[0] == prefix
    assert digest == svc.hash_secret(parsed[1])
    assert len(digest) == 64


@pytest.mark.parametrize(
    "raw",
    ["", "not-a-pat", "mica_pat_onlyprefix", "mica_pat__nosecret", "Bearer something"],
)
def test_split_token_rejects_malformed(raw: str) -> None:
    assert svc.split_token(raw) is None


def test_looks_like_pat_is_a_prefix_check_only() -> None:
    assert svc.looks_like_pat(f"{svc.TOKEN_PREFIX}0123456789ab_secret") is True
    # Malformed but still carrying the prefix: the guard must route it to the
    # PAT path, where it fails with 401 rather than being treated as a JWT.
    assert svc.looks_like_pat(f"{svc.TOKEN_PREFIX}onlyprefix") is True
    assert svc.looks_like_pat("eyJhbGciOiJIUzI1NiJ9.payload.sig") is False
    assert svc.looks_like_pat("") is False


async def test_create_stores_hash_and_authenticates(seeded_db_session: AsyncSession) -> None:
    user = await _user(seeded_db_session)
    row, plaintext = await svc.create_token(
        seeded_db_session, actor=user, name="unit-create", scopes=["read"]
    )

    secret = svc.split_token(plaintext)[1]  # type: ignore[index]
    assert row.token_hash == svc.hash_secret(secret)
    assert secret not in row.token_hash
    assert row.scopes == ["read"]
    assert row.expires_at is not None

    resolved_user, resolved_row = await svc.authenticate(seeded_db_session, plaintext)
    assert resolved_user.id == user.id
    assert resolved_row.id == row.id
    assert resolved_row.last_used_at is not None

    audit = (
        await seeded_db_session.execute(
            select(AuditLog).where(
                AuditLog.event_type == "api_token.created",
                AuditLog.resource_id == str(row.id),
            )
        )
    ).scalar_one()
    assert audit.metadata_json is not None
    assert plaintext not in str(audit.metadata_json)


async def test_authenticate_rejects_unknown_and_malformed(seeded_db_session: AsyncSession) -> None:
    for raw in ("mica_pat_0123456789ab_unknown-secret", "totally-not-a-token"):
        with pytest.raises(HTTPException) as excinfo:
            await svc.authenticate(seeded_db_session, raw)
        assert excinfo.value.status_code == 401
        assert excinfo.value.detail == "api_token.invalid"


async def test_authenticate_rejects_revoked_and_expired(seeded_db_session: AsyncSession) -> None:
    user = await _user(seeded_db_session)
    revoked_row, revoked_plain = await svc.create_token(
        seeded_db_session, actor=user, name="unit-revoked"
    )
    await svc.revoke_token(seeded_db_session, revoked_row, actor=user)
    with pytest.raises(HTTPException):
        await svc.authenticate(seeded_db_session, revoked_plain)

    expired_row, expired_plain = await svc.create_token(
        seeded_db_session, actor=user, name="unit-expired"
    )
    expired_row.expires_at = datetime.now(UTC) - timedelta(minutes=1)
    await seeded_db_session.flush()
    with pytest.raises(HTTPException):
        await svc.authenticate(seeded_db_session, expired_plain)


async def test_revoke_is_idempotent(seeded_db_session: AsyncSession) -> None:
    user = await _user(seeded_db_session)
    row, _ = await svc.create_token(seeded_db_session, actor=user, name="unit-idempotent")
    first = await svc.revoke_token(seeded_db_session, row, actor=user)
    second = await svc.revoke_token(seeded_db_session, first, actor=user)
    assert second.revoked_at == first.revoked_at


@pytest.mark.parametrize("name", ["", "   ", "x" * 65])
async def test_create_rejects_bad_name(seeded_db_session: AsyncSession, name: str) -> None:
    user = await _user(seeded_db_session)
    with pytest.raises(HTTPException) as excinfo:
        await svc.create_token(seeded_db_session, actor=user, name=name)
    assert excinfo.value.status_code == 400
    assert excinfo.value.detail == "api_token.invalid_name"


async def test_create_rejects_unknown_scope(seeded_db_session: AsyncSession) -> None:
    user = await _user(seeded_db_session)
    with pytest.raises(HTTPException) as excinfo:
        await svc.create_token(seeded_db_session, actor=user, name="unit-scope", scopes=["admin"])
    assert excinfo.value.detail == "api_token.invalid_scope"


async def test_read_only_caller_cannot_mint_write_token(seeded_db_session: AsyncSession) -> None:
    user = await _user(seeded_db_session)
    with pytest.raises(HTTPException) as excinfo:
        await svc.create_token(
            seeded_db_session,
            actor=user,
            name="unit-escalate",
            scopes=["read", "write"],
            max_scopes=["read"],
        )
    assert excinfo.value.status_code == 403
    assert excinfo.value.detail == "api_token.scope_escalation"


async def test_expiry_beyond_max_ttl_is_rejected(seeded_db_session: AsyncSession) -> None:
    user = await _user(seeded_db_session)
    with pytest.raises(HTTPException) as excinfo:
        await svc.create_token(
            seeded_db_session, actor=user, name="unit-ttl", expires_in_days=99999
        )
    assert excinfo.value.detail == "api_token.invalid_expiry"


async def test_rotate_revokes_old_and_keeps_expiry(seeded_db_session: AsyncSession) -> None:
    user = await _user(seeded_db_session)
    row, old_plain = await svc.create_token(seeded_db_session, actor=user, name="unit-rotate")

    replacement, new_plain = await svc.rotate_token(seeded_db_session, row, actor=user)

    assert replacement.expires_at == row.expires_at
    assert replacement.scopes == row.scopes
    with pytest.raises(HTTPException):
        await svc.authenticate(seeded_db_session, old_plain)
    resolved_user, _ = await svc.authenticate(seeded_db_session, new_plain)
    assert resolved_user.id == user.id


async def test_guard_blocks_admin_and_identity_paths(seeded_db_session: AsyncSession) -> None:
    user = await _user(seeded_db_session)
    row, _ = await svc.create_token(seeded_db_session, actor=user, name="unit-guard-path")

    for method, path in (
        ("GET", "/api/v1/admin/users"),
        ("GET", "/api/v2/admin/api-tokens"),
        ("POST", "/api/v1/auth/login/json"),
        ("GET", "/api/v1/saml/metadata"),
        ("POST", "/api/v1/me/tokens"),
        ("DELETE", "/api/v1/me/tokens/11111111-1111-1111-1111-111111111111"),
    ):
        with pytest.raises(HTTPException) as excinfo:
            await svc.guard_request(seeded_db_session, _request(method, path), row, user)
        assert excinfo.value.status_code == 403
        assert excinfo.value.detail == "api_token.path_forbidden"

    # /auth/me is the one identity path a token may use to verify itself, and a
    # token may always list its own siblings.
    await svc.guard_request(seeded_db_session, _request("GET", "/api/v1/auth/me"), row, user)
    await svc.guard_request(seeded_db_session, _request("GET", "/api/v1/me/tokens"), row, user)


async def test_read_only_scope_allows_safe_methods_and_allowlisted_posts(
    seeded_db_session: AsyncSession,
) -> None:
    user = await _user(seeded_db_session)
    row, _ = await svc.create_token(seeded_db_session, actor=user, name="unit-guard-ro")

    await svc.guard_request(
        seeded_db_session, _request("GET", "/api/v1/purchase-requisitions"), row, user
    )
    await svc.guard_request(seeded_db_session, _request("POST", "/api/v1/search"), row, user)

    with pytest.raises(HTTPException) as excinfo:
        await svc.guard_request(
            seeded_db_session, _request("POST", "/api/v1/purchase-requisitions"), row, user
        )
    assert excinfo.value.status_code == 403
    assert excinfo.value.detail == "api_token.read_only"

    with pytest.raises(HTTPException) as excinfo:
        await svc.guard_request(
            seeded_db_session, _request("DELETE", "/api/v1/purchase-requisitions/abc"), row, user
        )
    assert excinfo.value.detail == "api_token.read_only"


async def test_write_scope_allows_writes(seeded_db_session: AsyncSession) -> None:
    user = await _user(seeded_db_session)
    row, _ = await svc.create_token(
        seeded_db_session, actor=user, name="unit-guard-rw", scopes=["read", "write"]
    )
    await svc.guard_request(
        seeded_db_session, _request("POST", "/api/v1/purchase-requisitions"), row, user
    )


def test_client_ip_prefers_forwarded_for_behind_a_private_peer() -> None:
    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/api/v1/auth/me",
            "headers": [(b"x-forwarded-for", b"203.0.113.9, 172.18.0.2")],
            "client": ("172.18.0.5", 4321),
        }
    )
    assert svc.client_ip(request) == "203.0.113.9"


def test_client_ip_ignores_forwarded_for_from_a_public_peer() -> None:
    """A publicly reachable backend port must not let anyone forge the IP.

    ``8.8.8.8`` on purpose: ``ipaddress`` also counts the documentation ranges
    (198.51.100.0/24, 203.0.113.0/24) as private, so they cannot express
    "direct peer is on the internet" here.
    """
    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/api/v1/auth/me",
            "headers": [(b"x-forwarded-for", b"1.2.3.4")],
            "client": ("8.8.8.8", 4321),
        }
    )
    assert svc.client_ip(request) == "8.8.8.8"


def test_client_ip_without_forwarding_or_peer() -> None:
    plain = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/api/v1/auth/me",
            "headers": [],
            "client": ("172.18.0.5", 4321),
        }
    )
    assert svc.client_ip(plain) == "172.18.0.5"

    anonymous = Request(
        {"type": "http", "method": "GET", "path": "/api/v1/auth/me", "headers": [], "client": None}
    )
    assert svc.client_ip(anonymous) is None


def test_rate_limit_window() -> None:
    key = "unit-rate-limit"
    svc.check_rate_limit(key, 2)
    svc.check_rate_limit(key, 2)
    with pytest.raises(HTTPException) as excinfo:
        svc.check_rate_limit(key, 2)
    assert excinfo.value.status_code == 429
    assert excinfo.value.detail == "api_token.rate_limited"
    assert "Retry-After" in (excinfo.value.headers or {})


async def test_admin_listing_filters_revoked(seeded_db_session: AsyncSession) -> None:
    user = await _user(seeded_db_session)
    active, _ = await svc.create_token(seeded_db_session, actor=user, name="unit-admin-active")
    revoked, _ = await svc.create_token(seeded_db_session, actor=user, name="unit-admin-revoked")
    await svc.revoke_token(seeded_db_session, revoked, actor=user)

    rows, total = await svc.list_tokens_for_admin(seeded_db_session, user_id=user.id)
    ids = {token_row.id for token_row, _owner in rows}
    assert active.id in ids
    assert revoked.id not in ids
    assert total == len(rows) or total >= 1

    rows_all, _ = await svc.list_tokens_for_admin(
        seeded_db_session, user_id=user.id, include_revoked=True
    )
    ids_all = {token_row.id for token_row, _owner in rows_all}
    assert {active.id, revoked.id} <= ids_all


async def test_list_tokens_is_scoped_to_owner(seeded_db_session: AsyncSession) -> None:
    alice = await _user(seeded_db_session, "alice")
    bob = await _user(seeded_db_session, "bob")
    alice_row, _ = await svc.create_token(seeded_db_session, actor=alice, name="unit-scope-alice")

    alice_tokens = await svc.list_tokens(seeded_db_session, alice.id)
    bob_tokens = await svc.list_tokens(seeded_db_session, bob.id)

    assert alice_row.id in {row.id for row in alice_tokens}
    assert alice_row.id not in {row.id for row in bob_tokens}


async def test_get_token_for_actor_hides_foreign_tokens(seeded_db_session: AsyncSession) -> None:
    alice = await _user(seeded_db_session, "alice")
    bob = await _user(seeded_db_session, "bob")
    row, _ = await svc.create_token(seeded_db_session, actor=alice, name="unit-foreign")

    with pytest.raises(HTTPException) as excinfo:
        await svc.get_token_for_actor(seeded_db_session, row.id, actor=bob)
    assert excinfo.value.status_code == 404

    same = await svc.get_token_for_actor(seeded_db_session, row.id, actor=bob, allow_others=True)
    assert same.id == row.id


async def test_is_active_helpers() -> None:
    now = datetime.now(UTC)
    row = ApiToken(
        user_id=None,  # type: ignore[arg-type]
        name="helper",
        token_prefix=f"{svc.TOKEN_PREFIX}0123456789ab",
        token_hash="0" * 64,
        scopes=["read"],
        expires_at=None,
    )
    assert svc.is_expired(row) is False
    assert svc.is_active(row) is True

    row.expires_at = now - timedelta(seconds=1)
    assert svc.is_expired(row) is True
    assert svc.is_active(row) is False

    row.expires_at = now + timedelta(days=1)
    row.revoked_at = now
    assert svc.is_active(row) is False
