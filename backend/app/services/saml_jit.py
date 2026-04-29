from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.i18n import t
from app.models import AuditLog, User
from app.services.saml_config import SamlConfig, resolve_default_company, resolve_department

logger = logging.getLogger(__name__)


def _first_attribute(attributes: dict[str, list[str]], candidates: list[str]) -> str | None:
    for candidate in candidates:
        values = attributes.get(candidate)
        if not values:
            continue
        for value in values:
            stripped = value.strip()
            if stripped:
                return stripped
    return None


def _all_groups(attributes: dict[str, list[str]], candidates: list[str]) -> list[str]:
    seen: set[str] = set()
    groups: list[str] = []
    for candidate in candidates:
        for value in attributes.get(candidate, []):
            stripped = value.strip()
            if stripped and stripped not in seen:
                seen.add(stripped)
                groups.append(stripped)
    return groups


async def upsert_saml_user(
    session: AsyncSession,
    *,
    config: SamlConfig,
    external_id: str | None,
    attributes: dict[str, list[str]],
    locale: str,
) -> User:
    logger.info("SAML claims received: %s", json.dumps(attributes))
    email = _first_attribute(attributes, config.email_attribute_candidates())
    if not email:
        raise HTTPException(400, t("saml.missing_email", locale))
    identity = (external_id or email).strip()
    if not identity:
        raise HTTPException(400, t("saml.missing_external_id", locale))

    display_name = _first_attribute(attributes, config.display_name_candidates()) or email
    groups = _all_groups(attributes, config.group_attribute_candidates())

    user = (
        await session.execute(select(User).where(User.sso_external_id == identity))
    ).scalar_one_or_none()
    created = False
    linked = False
    if user is None:
        user = (await session.execute(select(User).where(User.email == email))).scalar_one_or_none()
        if user is None:
            if not config.jit_enabled:
                raise HTTPException(403, t("saml.jit_disabled", locale))
            company = await resolve_default_company(session, config, locale)
            default_department = await resolve_department(
                session,
                company_id=company.id,
                department_code=config.default_department_code,
                locale=locale,
            )
            user = User(
                username=await _generate_username(session, email),
                email=email,
                display_name=display_name,
                password_hash=None,
                role=config.default_role,
                company_id=company.id,
                department_id=default_department.id if default_department else None,
                preferred_locale=locale,
                auth_provider="saml",
                sso_external_id=identity,
                is_active=True,
            )
            session.add(user)
            await session.flush()
            created = True
        else:
            if user.sso_external_id and user.sso_external_id != identity:
                raise HTTPException(409, t("saml.authentication_failed", locale))
            user.sso_external_id = identity
            user.auth_provider = "saml"
            linked = True

    user.email = email
    user.display_name = display_name
    user.preferred_locale = locale
    user.auth_provider = "saml"
    user.sso_external_id = identity

    target_role, target_department_id = await _resolve_role_and_department(
        session,
        user=user,
        config=config,
        groups=groups,
        locale=locale,
        created=created,
    )
    user.role = target_role
    user.department_id = target_department_id
    user.last_login_at = datetime.now(UTC)
    await session.flush()

    await _write_auth_audit(
        session,
        event_type="auth.sso.login",
        user=user,
        metadata={
            "groups": groups,
            "created": created,
            "linked": linked,
        },
    )
    if created:
        await _write_auth_audit(
            session,
            event_type="auth.sso.provisioned",
            user=user,
            metadata={"email": email, "role": user.role},
        )
    if linked:
        await _write_auth_audit(
            session,
            event_type="auth.sso.linked",
            user=user,
            metadata={"email": email, "external_id": identity},
        )
    return user


async def _resolve_role_and_department(
    session: AsyncSession,
    *,
    user: User,
    config: SamlConfig,
    groups: list[str],
    locale: str,
    created: bool,
) -> tuple[str, UUID | None]:
    role = user.role
    department_id = user.department_id

    if config.group_mapping_enabled:
        matched = next((rule for rule in config.group_mapping if rule.group in groups), None)
        if matched is not None:
            role = matched.role
            department = await resolve_department(
                session,
                company_id=user.company_id,
                department_code=matched.department_code,
                locale=locale,
            )
            department_id = department.id if department else None
            return role, department_id

    if created:
        role = config.default_role
        department = await resolve_department(
            session,
            company_id=user.company_id,
            department_code=config.default_department_code,
            locale=locale,
        )
        department_id = department.id if department else None
    return role, department_id


async def _generate_username(session: AsyncSession, email: str) -> str:
    local_part = email.split("@", 1)[0].lower()
    base = "".join(char if char.isalnum() else "_" for char in local_part).strip("_") or "saml_user"
    candidate = base
    suffix = 1
    while (
        await session.execute(select(User.id).where(User.username == candidate))
    ).scalar_one_or_none() is not None:
        suffix += 1
        candidate = f"{base}_{suffix}"
    return candidate


async def _write_auth_audit(
    session: AsyncSession,
    *,
    event_type: str,
    user: User,
    metadata: dict[str, object],
) -> None:
    session.add(
        AuditLog(
            actor_id=user.id,
            actor_name=user.display_name,
            event_type=event_type,
            resource_type="user",
            resource_id=str(user.id),
            metadata_json=metadata,
            comment=event_type,
        )
    )
