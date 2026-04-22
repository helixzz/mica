"""Cerbos HTTP client for field-level authorization checks.

Wraps the Cerbos PDP ``/api/check/resources`` endpoint. Falls back to
the in-process ``FIELD_PERMISSIONS`` dict when the sidecar is
unreachable (graceful degradation for dev environments without Cerbos).
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.field_authz import filter_dict_by_role as _fallback_filter

logger = logging.getLogger(__name__)

CERBOS_BASE_URL = "http://cerbos:3593"
CERBOS_TIMEOUT = 2.0


async def check_field_access(
    *,
    principal_id: str,
    principal_role: str,
    resource_kind: str,
    resource_id: str,
    fields: list[str],
) -> set[str]:
    """Return the subset of *fields* the principal may read.

    On Cerbos failure, falls back to the static FIELD_PERMISSIONS dict
    so that the application never hard-fails on authorization checks.
    """
    actions = [f"read:{f}" for f in fields]
    payload: dict[str, Any] = {
        "principal": {
            "id": principal_id,
            "roles": [principal_role],
        },
        "resources": [
            {
                "resource": {
                    "kind": resource_kind,
                    "id": resource_id,
                },
                "actions": actions,
            }
        ],
    }

    try:
        async with httpx.AsyncClient(base_url=CERBOS_BASE_URL, timeout=CERBOS_TIMEOUT) as client:
            resp = await client.post("/api/check/resources", json=payload)
            resp.raise_for_status()
            data = resp.json()

        results = data.get("results", [])
        if not results:
            return set(fields)

        action_map = results[0].get("actions", {})
        allowed: set[str] = set()
        for field in fields:
            effect = action_map.get(f"read:{field}", {})
            if isinstance(effect, str):
                if effect == "EFFECT_ALLOW":
                    allowed.add(field)
            elif isinstance(effect, dict):
                if effect.get("effect") == "EFFECT_ALLOW":
                    allowed.add(field)
        return allowed

    except Exception:
        logger.debug(
            "Cerbos unreachable, falling back to static FIELD_PERMISSIONS",
            exc_info=True,
        )
        dummy = dict.fromkeys(fields, True)
        filtered = _fallback_filter(dummy, resource_kind, principal_role)
        return set(filtered.keys())


async def filter_dict_via_cerbos(
    data: dict[str, Any],
    *,
    principal_id: str,
    principal_role: str,
    resource_kind: str,
    resource_id: str,
) -> dict[str, Any]:
    """Filter a dict's keys through Cerbos field-level checks."""
    allowed = await check_field_access(
        principal_id=principal_id,
        principal_role=principal_role,
        resource_kind=resource_kind,
        resource_id=resource_id,
        fields=list(data.keys()),
    )
    return {k: v for k, v in data.items() if k in allowed}
