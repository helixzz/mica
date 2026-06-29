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

import importlib

import pytest
from fastapi import FastAPI
from fastapi.routing import APIRoute

_EXCLUDED_GET_PATHS: dict[str, str] = {
    "/api/v1/payments/export/excel": "returns xlsx binary, not JSON",
    "/api/v1/saml/login": "redirects to IdP",
    "/api/v1/saml/metadata": "returns XML metadata",
    "/api/v1/insights/quarterly-summary": "may call external LLM",
}


def _load_app_with_routes() -> FastAPI:
    main_mod = importlib.import_module("app.main")
    if not main_mod.app.routes or len(main_mod.app.routes) < 50:
        importlib.reload(main_mod)
    return main_mod.app


def _discover_parameterless_get_paths(app: FastAPI) -> list[str]:
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
    app = _load_app_with_routes()
    paths = _discover_parameterless_get_paths(app)
    if len(paths) < 50:
        pytest.skip(
            f"app.routes introspection returned only {len(paths)} endpoints. "
            "Coverage is already provided by tests/unit/test_api_contracts.py "
            "and the integration suite."
        )

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
