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

from fastapi.routing import APIRoute

from app.main import app

_EXCLUDED_GET_PATHS: dict[str, str] = {
    "/api/v1/payments/export/excel": "returns xlsx binary, not JSON",
    "/api/v1/saml/login": "redirects to IdP",
    "/api/v1/saml/metadata": "returns XML metadata",
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


async def _admin_token(seeded_client) -> str:
    resp = await seeded_client.post(
        "/api/v1/auth/login/json",
        json={"username": "admin", "password": "MicaDev2026!"},
    )
    assert resp.status_code == 200, f"admin login failed: {resp.status_code} {resp.text}"
    return resp.json()["access_token"]


async def test_all_parameterless_get_endpoints_contract(seeded_client):
    """Drive every parameterless GET /api/v1/* and assert no 5xx / valid JSON.

    Discovery happens inside the test (not at module import) so router
    registration is guaranteed to be complete regardless of pytest
    collection ordering. Previously this was a module-level constant fed
    into @pytest.mark.parametrize, which in CI saw an empty route table
    when collected before fixtures imported the full app.
    """
    paths = _discover_parameterless_get_paths()
    assert len(paths) >= 50, f"expected many GET endpoints, found {len(paths)}"

    token = await _admin_token(seeded_client)
    headers = {"Authorization": f"Bearer {token}"}
    failures: list[str] = []

    for path in paths:
        resp = await seeded_client.get(path, headers=headers)
        if resp.status_code >= 500:
            failures.append(f"GET {path} → {resp.status_code}: {resp.text[:200]}")
            continue
        if resp.status_code == 200 and resp.content:
            ctype = resp.headers.get("content-type", "")
            if "application/json" in ctype:
                try:
                    resp.json()
                except Exception as exc:
                    failures.append(f"GET {path} → invalid JSON: {exc}")

    assert not failures, "API contract failures:\n" + "\n".join(failures)
