from __future__ import annotations

import json
from dataclasses import dataclass
from urllib.parse import urlparse

from fastapi import HTTPException, Request
from onelogin.saml2.settings import OneLogin_Saml2_Settings
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.i18n import t
from app.models import Company, Department, UserRole
from app.services.system_params import system_params

settings = get_settings()

SAML_LOGIN_URL = "/api/v1/saml/login"
SAML_METADATA_URL = "/api/v1/saml/metadata"
SAML_ACS_URL = "/api/v1/saml/acs"

EMAIL_FALLBACKS = [
    "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress",
    "email",
    "mail",
]
DISPLAY_NAME_FALLBACKS = [
    "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name",
    "displayName",
    "name",
]
GROUP_FALLBACKS = [
    "http://schemas.xmlsoap.org/claims/group",
    "http://schemas.microsoft.com/ws/2008/06/identity/claims/role",
    "groups",
    "group",
    "memberOf",
    "role",
]


@dataclass(slots=True)
class SamlGroupMapping:
    group: str
    role: str
    department_code: str | None = None


@dataclass(slots=True)
class SamlConfig:
    enabled: bool
    idp_entity_id: str
    idp_sso_url: str
    idp_slo_url: str | None
    idp_x509_cert: str
    sp_entity_id: str
    sp_acs_url: str
    email_attribute: str
    display_name_attribute: str
    groups_attribute: str
    jit_enabled: bool
    default_role: str
    default_company_code: str | None
    default_department_code: str | None
    group_mapping_enabled: bool
    group_mapping: list[SamlGroupMapping]

    def email_attribute_candidates(self) -> list[str]:
        return _unique_candidates(self.email_attribute, EMAIL_FALLBACKS)

    def display_name_candidates(self) -> list[str]:
        return _unique_candidates(self.display_name_attribute, DISPLAY_NAME_FALLBACKS)

    def group_attribute_candidates(self) -> list[str]:
        return _unique_candidates(self.groups_attribute, GROUP_FALLBACKS)

    def to_onelogin_settings(self) -> dict[str, object]:
        allow_single_label_domains = _host_is_single_label(
            self.sp_entity_id
        ) or _host_is_single_label(self.sp_acs_url)
        idp: dict[str, object] = {
            "entityId": self.idp_entity_id,
            "singleSignOnService": {
                "url": self.idp_sso_url,
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
            },
            "x509cert": self.idp_x509_cert,
        }
        if self.idp_slo_url:
            idp["singleLogoutService"] = {
                "url": self.idp_slo_url,
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
            }
        return {
            "strict": True,
            "debug": settings.debug,
            "sp": {
                "entityId": self.sp_entity_id,
                "assertionConsumerService": {
                    "url": self.sp_acs_url,
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST",
                },
                "NameIDFormat": "urn:oasis:names:tc:SAML:1.1:nameid-format:unspecified",
                "x509cert": "",
                "privateKey": "",
            },
            "idp": idp,
            "security": {
                "authnRequestsSigned": False,
                "logoutRequestSigned": False,
                "logoutResponseSigned": False,
                "wantAssertionsSigned": True,
                "wantMessagesSigned": False,
                "wantAssertionsEncrypted": False,
                "wantNameIdEncrypted": False,
                "signatureAlgorithm": "http://www.w3.org/2001/04/xmldsig-more#rsa-sha256",
                "digestAlgorithm": "http://www.w3.org/2001/04/xmlenc#sha256",
                "rejectDeprecatedAlgorithm": True,
                "allowSingleLabelDomains": allow_single_label_domains,
            },
        }


def _normalize_optional_string(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _normalize_x509_cert(value: str | None) -> str:
    if not value:
        return ""
    return (
        value.replace("-----BEGIN CERTIFICATE-----", "")
        .replace("-----END CERTIFICATE-----", "")
        .replace("\n", "")
        .replace("\r", "")
        .replace(" ", "")
        .strip()
    )


def _absolute_url(request: Request, path: str) -> str:
    scheme = request.headers.get("x-forwarded-proto", request.url.scheme)
    host = request.headers.get("x-forwarded-host", request.headers.get("host", request.url.netloc))
    return f"{scheme}://{host}{path}"


def _unique_candidates(primary: str, fallbacks: list[str]) -> list[str]:
    candidates = [primary, *fallbacks]
    seen: set[str] = set()
    ordered: list[str] = []
    for candidate in candidates:
        stripped = candidate.strip()
        if stripped and stripped not in seen:
            ordered.append(stripped)
            seen.add(stripped)
    return ordered


def _parse_group_mapping(value: str | None, locale: str) -> list[SamlGroupMapping]:
    if value is None or not value.strip():
        return []
    try:
        raw = json.loads(value)
    except json.JSONDecodeError as exc:
        raise HTTPException(500, t("saml.group_mapping_invalid", locale)) from exc
    if not isinstance(raw, list):
        raise HTTPException(500, t("saml.group_mapping_invalid", locale))

    valid_roles = {role.value for role in UserRole}
    rules: list[SamlGroupMapping] = []
    for item in raw:
        if not isinstance(item, dict):
            raise HTTPException(500, t("saml.group_mapping_invalid", locale))
        group = item.get("group")
        role = item.get("role")
        department_code = item.get("department_code")
        if not isinstance(group, str) or not group.strip():
            raise HTTPException(500, t("saml.group_mapping_invalid", locale))
        if not isinstance(role, str) or role not in valid_roles:
            raise HTTPException(500, t("saml.group_mapping_invalid", locale))
        if department_code is not None and not isinstance(department_code, str):
            raise HTTPException(500, t("saml.group_mapping_invalid", locale))
        rules.append(
            SamlGroupMapping(
                group=group.strip(),
                role=role,
                department_code=_normalize_optional_string(department_code),
            )
        )
    return rules


async def get_saml_config(
    session: AsyncSession,
    request: Request,
    locale: str,
) -> SamlConfig:
    enabled = bool(await system_params.get(session, "auth.saml.enabled", False))
    idp_entity_id = _normalize_optional_string(
        await system_params.get(session, "auth.saml.idp.entity_id", "")
    )
    idp_sso_url = _normalize_optional_string(
        await system_params.get(session, "auth.saml.idp.sso_url", "")
    )
    idp_slo_url = _normalize_optional_string(
        await system_params.get(session, "auth.saml.idp.slo_url", "")
    )
    idp_x509_cert = _normalize_x509_cert(
        _normalize_optional_string(await system_params.get(session, "auth.saml.idp.x509_cert", ""))
    )
    sp_entity_id = _normalize_optional_string(
        await system_params.get(session, "auth.saml.sp.entity_id", "")
    ) or _absolute_url(request, SAML_METADATA_URL)
    sp_acs_url = _normalize_optional_string(
        await system_params.get(session, "auth.saml.sp.acs_url", "")
    ) or _absolute_url(request, SAML_ACS_URL)
    email_attribute = (
        _normalize_optional_string(
            await system_params.get(session, "auth.saml.attr.email", EMAIL_FALLBACKS[0])
        )
        or EMAIL_FALLBACKS[0]
    )
    display_name_attribute = (
        _normalize_optional_string(
            await system_params.get(
                session, "auth.saml.attr.display_name", DISPLAY_NAME_FALLBACKS[0]
            )
        )
        or DISPLAY_NAME_FALLBACKS[0]
    )
    groups_attribute = (
        _normalize_optional_string(
            await system_params.get(session, "auth.saml.attr.groups", GROUP_FALLBACKS[0])
        )
        or GROUP_FALLBACKS[0]
    )
    jit_enabled = bool(await system_params.get(session, "auth.saml.jit.enabled", True))
    default_role = (
        _normalize_optional_string(
            await system_params.get(session, "auth.saml.jit.default_role", UserRole.REQUESTER.value)
        )
        or UserRole.REQUESTER.value
    )
    default_company_code = _normalize_optional_string(
        await system_params.get(session, "auth.saml.jit.default_company_code", "")
    )
    default_department_code = _normalize_optional_string(
        await system_params.get(session, "auth.saml.jit.default_department_code", "")
    )
    group_mapping_enabled = bool(
        await system_params.get(session, "auth.saml.group_mapping_enabled", False)
    )
    group_mapping_raw = (
        _normalize_optional_string(
            await system_params.get(session, "auth.saml.group_mapping", "[]")
        )
        or "[]"
    )

    config = SamlConfig(
        enabled=enabled,
        idp_entity_id=idp_entity_id or "",
        idp_sso_url=idp_sso_url or "",
        idp_slo_url=idp_slo_url,
        idp_x509_cert=idp_x509_cert,
        sp_entity_id=sp_entity_id,
        sp_acs_url=sp_acs_url,
        email_attribute=email_attribute,
        display_name_attribute=display_name_attribute,
        groups_attribute=groups_attribute,
        jit_enabled=jit_enabled,
        default_role=default_role,
        default_company_code=default_company_code,
        default_department_code=default_department_code,
        group_mapping_enabled=group_mapping_enabled,
        group_mapping=_parse_group_mapping(group_mapping_raw, locale),
    )
    _validate_saml_config(config, locale)
    return config


async def is_saml_login_available(session: AsyncSession, request: Request, locale: str) -> bool:
    try:
        config = await get_saml_config(session, request, locale)
    except HTTPException:
        return False
    return config.enabled


def build_onelogin_settings(config: SamlConfig) -> OneLogin_Saml2_Settings:
    return OneLogin_Saml2_Settings(config.to_onelogin_settings())


async def resolve_default_company(
    session: AsyncSession, config: SamlConfig, locale: str
) -> Company:
    if config.default_company_code:
        company = (
            await session.execute(
                select(Company).where(Company.code == config.default_company_code)
            )
        ).scalar_one_or_none()
        if company is not None:
            return company
    companies = list(
        (
            await session.execute(
                select(Company).where(Company.is_deleted.is_(False), Company.is_enabled.is_(True))
            )
        ).scalars()
    )
    if len(companies) == 1:
        return companies[0]
    raise HTTPException(500, t("saml.default_company_required", locale))


async def resolve_department(
    session: AsyncSession,
    *,
    company_id,
    department_code: str | None,
    locale: str,
) -> Department | None:
    if not department_code:
        return None
    department = (
        await session.execute(
            select(Department).where(
                Department.company_id == company_id,
                Department.code == department_code,
                Department.is_deleted.is_(False),
                Department.is_enabled.is_(True),
            )
        )
    ).scalar_one_or_none()
    if department is None:
        raise HTTPException(500, t("saml.default_department_not_found", locale))
    return department


def _validate_saml_config(config: SamlConfig, locale: str) -> None:
    if not config.enabled:
        return
    if config.default_role not in {role.value for role in UserRole}:
        raise HTTPException(500, t("saml.default_role_invalid", locale))
    required_values = [config.idp_entity_id, config.idp_sso_url, config.idp_x509_cert]
    if any(not value for value in required_values):
        raise HTTPException(500, t("saml.misconfigured", locale))
    for url in [config.idp_sso_url, config.sp_entity_id, config.sp_acs_url, config.idp_slo_url]:
        if url and not _looks_like_url(url):
            raise HTTPException(500, t("saml.misconfigured", locale))


def _looks_like_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _host_is_single_label(value: str) -> bool:
    hostname = urlparse(value).hostname
    return bool(hostname and hostname != "localhost" and "." not in hostname)
