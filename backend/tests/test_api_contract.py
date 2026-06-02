# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportPrivateUsage=false
"""API contract smoke tests.

Auto-discovers parameterless GET endpoints under /api/v1 and verifies each
returns a non-5xx status with a valid JSON body when called as admin. This
catches accidental 500s, broken SQLAlchemy eager-loading, and Pydantic
response_model serialization regressions across the whole API surface with
near-zero maintenance: new GET endpoints are covered automatically.

See mica-internal discussion on test strategy (oracle recommendation):
Option C (auto-discovery) + curated path-param supplement.
"""

import pytest
from fastapi.routing import APIRoute

from app.main import app

# GET endpoints excluded from auto-discovery, each with a reason.
_EXCLUDED_GET_PATHS: dict[str, str] = {
    # Non-JSON binary responses (Excel export)
    "/api/v1/payments/export/excel": "returns xlsx binary, not JSON",
    # SAML browser-redirect flows (302 to IdP, not JSON)
    "/api/v1/saml/login": "redirects to IdP",
    "/api/v1/saml/metadata": "returns XML metadata",
    # AI quarterly summary may trigger an external LLM call
    "/api/v1/insights/quarterly-summary": "may call external LLM",
}


def _discover_parameterless_get_paths() -> list[str]:
    paths: list[str] = []
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        if "GET" not in route.methods:
            continue
        if not route.path.startswith("/api/v1/"):
            continue
        if route.path in _EXCLUDED_GET_PATHS:
            continue
        if route.dependant.path_params:
            continue
        has_required_query = any(
            getattr(q, "default", ...) is ... for q in route.dependant.query_params
        )
        if has_required_query:
            continue
        paths.append(route.path)
    return sorted(set(paths))


_GET_PATHS = _discover_parameterless_get_paths()


async def _admin_token(seeded_client) -> str:
    resp = await seeded_client.post(
        "/api/v1/auth/login/json",
        json={"username": "admin", "password": "MicaDev2026!"},
    )
    assert resp.status_code == 200, f"admin login failed: {resp.status_code} {resp.text}"
    return resp.json()["access_token"]


def test_discovery_found_endpoints():
    # Guard: if discovery breaks (returns 0), the parametrized test would
    # silently pass with no cases. Fail loudly instead.
    assert len(_GET_PATHS) >= 50, f"expected many GET endpoints, found {len(_GET_PATHS)}"


@pytest.mark.parametrize("path", _GET_PATHS)
async def test_get_endpoint_contract(seeded_client, path: str):
    token = await _admin_token(seeded_client)
    resp = await seeded_client.get(path, headers={"Authorization": f"Bearer {token}"})

    # No server errors — catches 500s from serialization / eager-load bugs
    assert resp.status_code < 500, f"GET {path} returned {resp.status_code}: {resp.text[:500]}"

    # Successful responses must be valid JSON (response_model serialization)
    if resp.status_code == 200 and resp.content:
        ctype = resp.headers.get("content-type", "")
        if "application/json" in ctype:
            resp.json()  # raises if body is not valid JSON
