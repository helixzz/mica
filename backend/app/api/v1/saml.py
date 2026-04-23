"""SAML SSO endpoints."""

from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse, Response
from onelogin.saml2.auth import OneLogin_Saml2_Auth
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.db import get_db
from app.i18n import detect_locale, t
from app.models import AuditLog
from app.services.saml_config import build_onelogin_settings, get_saml_config
from app.services.saml_jit import upsert_saml_user
from app.services.system_params import system_params

router = APIRouter()


@router.get("/saml/metadata", tags=["saml"])
async def saml_metadata(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    locale = detect_locale(request)
    config = await get_saml_config(db, request, locale)
    if not config.enabled:
        raise HTTPException(503, t("saml.not_enabled", locale))
    try:
        saml_settings = build_onelogin_settings(config)
        metadata = saml_settings.get_sp_metadata()
        errors = saml_settings.validate_metadata(metadata)
    except HTTPException:
        raise
    except Exception as exc:
        await _write_saml_system_audit(
            db,
            event_type="auth.sso.misconfigured",
            metadata={"reason": str(exc)},
        )
        await db.commit()
        raise HTTPException(500, t("saml.misconfigured", locale)) from exc
    if errors:
        await _write_saml_system_audit(
            db,
            event_type="auth.sso.misconfigured",
            metadata={"errors": errors},
        )
        await db.commit()
        raise HTTPException(500, t("saml.metadata_invalid", locale))
    return Response(content=metadata, media_type="text/xml")


@router.get("/saml/login", tags=["saml"])
async def saml_login_init(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RedirectResponse:
    locale = detect_locale(request)
    config = await get_saml_config(db, request, locale)
    if not config.enabled:
        raise HTTPException(503, t("saml.not_enabled", locale))
    relay_state = _validated_relay_state(request.query_params.get("next"), locale)
    try:
        auth = OneLogin_Saml2_Auth(
            _build_onelogin_request(request),
            old_settings=config.to_onelogin_settings(),
        )
        redirect_url = auth.login(return_to=relay_state)
    except HTTPException:
        raise
    except Exception as exc:
        await _write_saml_system_audit(
            db,
            event_type="auth.sso.misconfigured",
            metadata={"reason": str(exc)},
        )
        await db.commit()
        raise HTTPException(500, t("saml.misconfigured", locale)) from exc
    return RedirectResponse(url=redirect_url, status_code=302)


@router.post("/saml/acs", tags=["saml"])
async def saml_acs(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RedirectResponse:
    locale = detect_locale(request)
    config = await get_saml_config(db, request, locale)
    if not config.enabled:
        raise HTTPException(503, t("saml.not_enabled", locale))
    form_data = await request.form()
    if "SAMLResponse" not in form_data:
        raise HTTPException(400, t("saml.invalid_response", locale))

    try:
        auth = OneLogin_Saml2_Auth(
            _build_onelogin_request(request, form_data),
            old_settings=config.to_onelogin_settings(),
        )
        auth.process_response()
        errors = auth.get_errors()
        if errors or not auth.is_authenticated():
            raise HTTPException(403, t("saml.authentication_failed", locale))
        attributes = auth.get_attributes()
        external_id = auth.get_nameid()
        user = await upsert_saml_user(
            db,
            config=config,
            external_id=external_id,
            attributes=attributes,
            locale=locale,
        )
    except HTTPException as exc:
        if exc.status_code >= 500:
            await _write_saml_system_audit(
                db,
                event_type="auth.sso.misconfigured",
                metadata={"detail": str(exc.detail)},
            )
            await db.commit()
        raise
    except Exception as exc:
        await _write_saml_system_audit(
            db,
            event_type="auth.sso.misconfigured",
            metadata={"reason": str(exc)},
        )
        await db.commit()
        raise HTTPException(500, t("saml.misconfigured", locale)) from exc

    access_token_ttl_minutes = int(
        await system_params.get_int_or(db, "auth.access_token_expire_minutes", 480)
    )
    token = create_access_token(
        str(user.id),
        extra={"role": user.role},
        expire_minutes=access_token_ttl_minutes,
    )
    next_path = _validated_relay_state(form_data.get("RelayState"), locale)
    await db.commit()
    location = f"/sso-callback#token={quote(token)}&next={quote(next_path)}"
    return RedirectResponse(url=location, status_code=302)


def _build_onelogin_request(request: Request, form_data=None) -> dict[str, object]:
    scheme = request.headers.get("x-forwarded-proto", request.url.scheme)
    host = request.headers.get("x-forwarded-host", request.headers.get("host", "localhost"))
    if ":" in host:
        hostname, port_str = host.rsplit(":", 1)
        port = int(port_str) if port_str.isdigit() else (443 if scheme == "https" else 80)
    else:
        hostname = host
        port = 443 if scheme == "https" else 80
    return {
        "https": "on" if scheme == "https" else "off",
        "http_host": hostname,
        "server_port": port,
        "script_name": request.url.path,
        "query_string": request.url.query,
        "get_data": dict(request.query_params),
        "post_data": dict(form_data) if form_data is not None else {},
        "lowercase_urlencoding": True,
    }


def _validated_relay_state(value: object, locale: str) -> str:
    if not isinstance(value, str) or not value.strip():
        return "/dashboard"
    relay_state = value.strip()
    if not relay_state.startswith("/") or relay_state.startswith("//") or "://" in relay_state:
        raise HTTPException(400, t("saml.invalid_relay_state", locale))
    return relay_state


async def _write_saml_system_audit(
    db: AsyncSession,
    *,
    event_type: str,
    metadata: dict[str, object],
) -> None:
    db.add(
        AuditLog(
            actor_id=None,
            actor_name=None,
            event_type=event_type,
            resource_type="auth_provider",
            resource_id="saml",
            metadata_json=metadata,
            comment=event_type,
        )
    )
