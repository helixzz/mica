"""End-to-end tests for PAT authentication over the real HTTP surface.

Uses the legacy ``seeded_client`` fixture on purpose: PAT writes really commit,
so these tests exercise the same commit/flush path production uses.
"""

from __future__ import annotations

from typing import Any

from httpx import AsyncClient

from app.config import get_settings

PASSWORD = get_settings().seed_default_password


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _login(client: AsyncClient, username: str) -> str:
    resp = await client.post(
        "/api/v1/auth/login/json", json={"username": username, "password": PASSWORD}
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


async def _purge_test_tokens(client: AsyncClient) -> None:
    """Keep the shared test database from accumulating PATs across runs."""
    jwt = await _login(client, "admin")
    listed = await client.get(
        "/api/v1/admin/api-tokens?include_revoked=false&limit=200", headers=_auth(jwt)
    )
    if listed.status_code != 200:
        return
    for item in listed.json()["items"]:
        if str(item["name"]).startswith("pytest-"):
            await client.delete(f"/api/v1/admin/api-tokens/{item['id']}", headers=_auth(jwt))


async def _issue(
    client: AsyncClient,
    *,
    username: str = "alice",
    name: str = "pytest-pat",
    scopes: list[str] | None = None,
    expires_in_days: int | None = None,
) -> tuple[str, dict[str, Any]]:
    jwt = await _login(client, username)
    payload: dict[str, Any] = {"name": name}
    if scopes is not None:
        payload["scopes"] = scopes
    if expires_in_days is not None:
        payload["expires_in_days"] = expires_in_days
    resp = await client.post("/api/v1/me/tokens", json=payload, headers=_auth(jwt))
    assert resp.status_code == 201, resp.text
    return jwt, resp.json()


async def test_created_token_acts_as_its_owner(seeded_client: AsyncClient) -> None:
    await _purge_test_tokens(seeded_client)
    _jwt, created = await _issue(seeded_client, name="pytest-owner")

    assert created["token"].startswith("mica_pat_")
    assert created["prefix"].startswith("mica_pat_")
    assert created["scopes"] == ["read"]
    assert created["is_active"] is True
    assert created["is_expired"] is False

    me = await seeded_client.get("/api/v1/auth/me", headers=_auth(created["token"]))
    assert me.status_code == 200, me.text
    assert me.json()["username"] == "alice"

    # Same identity as the JWT that created it.
    jwt_me = await seeded_client.get("/api/v1/auth/me", headers=_auth(_jwt))
    assert jwt_me.json()["id"] == me.json()["id"]


async def test_plaintext_token_is_never_returned_again(seeded_client: AsyncClient) -> None:
    await _purge_test_tokens(seeded_client)
    jwt, created = await _issue(seeded_client, name="pytest-once")

    listed = await seeded_client.get("/api/v1/me/tokens", headers=_auth(jwt))
    assert listed.status_code == 200
    match = next(item for item in listed.json() if item["id"] == created["id"])
    assert "token" not in match
    assert match["prefix"] == created["prefix"]


async def test_read_only_token_cannot_write(seeded_client: AsyncClient) -> None:
    await _purge_test_tokens(seeded_client)
    _jwt, created = await _issue(seeded_client, name="pytest-readonly", scopes=["read"])
    headers = _auth(created["token"])

    read = await seeded_client.get("/api/v1/purchase-requisitions", headers=headers)
    assert read.status_code == 200, read.text

    write = await seeded_client.post(
        "/api/v1/purchase-requisitions", json={"title": "blocked"}, headers=headers
    )
    assert write.status_code == 403, write.text
    assert write.json()["code"] == "api_token.read_only"

    delete = await seeded_client.delete(
        f"/api/v1/purchase-requisitions/{created['id']}", headers=headers
    )
    assert delete.status_code == 403, delete.text
    assert delete.json()["code"] == "api_token.read_only"


async def test_write_scope_is_not_blocked(seeded_client: AsyncClient) -> None:
    await _purge_test_tokens(seeded_client)
    _jwt, created = await _issue(seeded_client, name="pytest-write", scopes=["read", "write"])
    headers = _auth(created["token"])

    # The payload here is intentionally incomplete; what matters is that the
    # request gets past the token scope guard instead of a 403 read_only.
    resp = await seeded_client.post(
        "/api/v1/purchase-requisitions", json={"title": "x"}, headers=headers
    )
    assert resp.json().get("code") != "api_token.read_only"


async def test_token_cannot_reach_admin_paths(seeded_client: AsyncClient) -> None:
    await _purge_test_tokens(seeded_client)
    _jwt, created = await _issue(seeded_client, username="admin", name="pytest-admin-path")
    headers = _auth(created["token"])

    resp = await seeded_client.get("/api/v1/admin/users", headers=headers)
    assert resp.status_code == 403, resp.text
    assert resp.json()["code"] == "api_token.path_forbidden"

    resp = await seeded_client.post(
        "/api/v1/auth/login/json", json={"username": "admin", "password": "irrelevant"}
    )
    assert resp.status_code in (401, 422)


async def test_token_cannot_manage_credentials(seeded_client: AsyncClient) -> None:
    """A leaked token must not be able to re-mint or revoke credentials."""
    await _purge_test_tokens(seeded_client)
    jwt, created = await _issue(seeded_client, name="pytest-no-mint", scopes=["read", "write"])
    headers = _auth(created["token"])

    minted = await seeded_client.post(
        "/api/v1/me/tokens",
        json={"name": "pytest-should-not-exist", "scopes": ["read"]},
        headers=headers,
    )
    assert minted.status_code == 403, minted.text
    assert minted.json()["code"] == "api_token.path_forbidden"

    revoked = await seeded_client.delete(f"/api/v1/me/tokens/{created['id']}", headers=headers)
    assert revoked.status_code == 403, revoked.text
    assert revoked.json()["code"] == "api_token.path_forbidden"

    # Reading its own list stays allowed, and the token is still alive.
    listed = await seeded_client.get("/api/v1/me/tokens", headers=headers)
    assert listed.status_code == 200, listed.text
    assert (await seeded_client.get("/api/v1/auth/me", headers=headers)).status_code == 200

    # The owner (JWT) can still do it.
    assert (
        await seeded_client.delete(f"/api/v1/me/tokens/{created['id']}", headers=_auth(jwt))
    ).status_code == 204


async def test_revoked_token_is_rejected(seeded_client: AsyncClient) -> None:
    await _purge_test_tokens(seeded_client)
    jwt, created = await _issue(seeded_client, name="pytest-revoke")
    headers = _auth(created["token"])

    assert (await seeded_client.get("/api/v1/auth/me", headers=headers)).status_code == 200

    revoked = await seeded_client.delete(f"/api/v1/me/tokens/{created['id']}", headers=_auth(jwt))
    assert revoked.status_code == 204, revoked.text

    after = await seeded_client.get("/api/v1/auth/me", headers=headers)
    assert after.status_code == 401, after.text
    assert after.json()["code"] == "api_token.invalid"


async def test_rotated_token_replaces_the_old_one(seeded_client: AsyncClient) -> None:
    await _purge_test_tokens(seeded_client)
    jwt, created = await _issue(seeded_client, name="pytest-rotate")

    rotated = await seeded_client.post(
        f"/api/v1/me/tokens/{created['id']}/rotate", headers=_auth(jwt)
    )
    assert rotated.status_code == 201, rotated.text
    replacement = rotated.json()
    assert replacement["token"] != created["token"]

    old = await seeded_client.get("/api/v1/auth/me", headers=_auth(created["token"]))
    assert old.status_code == 401

    new = await seeded_client.get("/api/v1/auth/me", headers=_auth(replacement["token"]))
    assert new.status_code == 200, new.text


async def test_malformed_and_unknown_tokens_are_rejected(seeded_client: AsyncClient) -> None:
    for raw in (
        "mica_pat_0123456789ab_not-a-real-secret",
        "mica_pat_",
        "eyJhbGciOiJIUzI1NiJ9.not.a.jwt",
    ):
        resp = await seeded_client.get("/api/v1/auth/me", headers=_auth(raw))
        assert resp.status_code == 401, (raw, resp.text)

    missing = await seeded_client.get("/api/v1/auth/me")
    assert missing.status_code == 401


async def test_admin_can_list_and_revoke_any_token(seeded_client: AsyncClient) -> None:
    await _purge_test_tokens(seeded_client)
    _jwt, created = await _issue(seeded_client, name="pytest-admin-view")
    admin_jwt = await _login(seeded_client, "admin")
    headers = _auth(admin_jwt)

    listed = await seeded_client.get("/api/v1/admin/api-tokens?limit=200", headers=headers)
    assert listed.status_code == 200, listed.text
    body = listed.json()
    match = next(item for item in body["items"] if item["id"] == created["id"])
    assert match["username"] == "alice"
    assert match["user_display_name"]
    assert body["total"] >= 1

    revoked = await seeded_client.delete(
        f"/api/v1/admin/api-tokens/{created['id']}", headers=headers
    )
    assert revoked.status_code == 204, revoked.text

    after = await seeded_client.get("/api/v1/auth/me", headers=_auth(created["token"]))
    assert after.status_code == 401


async def test_non_admin_cannot_list_all_tokens(seeded_client: AsyncClient) -> None:
    await _purge_test_tokens(seeded_client)
    alice_jwt = await _login(seeded_client, "alice")
    resp = await seeded_client.get("/api/v1/admin/api-tokens", headers=_auth(alice_jwt))
    assert resp.status_code == 403


async def test_expiry_defaults_and_limits(seeded_client: AsyncClient) -> None:
    await _purge_test_tokens(seeded_client)
    jwt, created = await _issue(seeded_client, name="pytest-ttl", expires_in_days=30)
    assert created["expires_at"] is not None

    too_long = await seeded_client.post(
        "/api/v1/me/tokens",
        json={"name": "pytest-ttl-long", "expires_in_days": 100000},
        headers=_auth(jwt),
    )
    assert too_long.status_code == 400, too_long.text
    assert too_long.json()["code"] == "api_token.invalid_expiry"


async def test_v2_path_also_accepts_pat(seeded_client: AsyncClient) -> None:
    await _purge_test_tokens(seeded_client)
    _jwt, created = await _issue(seeded_client, name="pytest-v2")
    resp = await seeded_client.get("/api/v2/auth/me", headers=_auth(created["token"]))
    assert resp.status_code == 200, resp.text
    assert resp.json()["username"] == "alice"
