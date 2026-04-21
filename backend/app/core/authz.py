from __future__ import annotations

import yaml
from pathlib import Path

from app.models import User, UserRole


POLICIES_DIR = Path(__file__).resolve().parents[2] / "cerbos-policies"


def _load_policies() -> dict:
    policies: dict[str, dict] = {}
    if not POLICIES_DIR.exists():
        return policies
    for p in POLICIES_DIR.glob("*.yaml"):
        try:
            data = yaml.safe_load(p.read_text(encoding="utf-8"))
        except yaml.YAMLError:
            continue
        rp = data.get("resourcePolicy") if isinstance(data, dict) else None
        if rp and rp.get("resource"):
            policies[rp["resource"]] = rp
    return policies


_POLICY_CACHE: dict | None = None


def _policies() -> dict:
    global _POLICY_CACHE
    if _POLICY_CACHE is None:
        _POLICY_CACHE = _load_policies()
    return _POLICY_CACHE


def reload_policies() -> None:
    global _POLICY_CACHE
    _POLICY_CACHE = None


def check_permission(user: User, resource: str, action: str, attrs: dict | None = None) -> bool:
    if user.role == UserRole.ADMIN.value:
        return True
    policy = _policies().get(resource)
    if not policy:
        return True
    attrs = attrs or {}
    for rule in policy.get("rules", []):
        actions = rule.get("actions", [])
        if "*" not in actions and action not in actions:
            continue
        roles = rule.get("roles", [])
        if roles and user.role not in roles:
            continue
        effect = rule.get("effect", "EFFECT_ALLOW")
        if effect == "EFFECT_ALLOW":
            return True
    return False
