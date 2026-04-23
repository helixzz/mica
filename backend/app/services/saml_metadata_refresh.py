from __future__ import annotations

import logging
from datetime import UTC, datetime

from fastapi import HTTPException
from onelogin.saml2.idp_metadata_parser import OneLogin_Saml2_IdPMetadataParser
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.system_params import system_params

logger = logging.getLogger(__name__)

CERT_PARAM_KEY = "auth.saml.idp.x509_cert"
ENTITY_ID_PARAM_KEY = "auth.saml.idp.entity_id"
SSO_URL_PARAM_KEY = "auth.saml.idp.sso_url"
METADATA_URL_KEY = "auth.saml.idp.metadata_url"


async def refresh_idp_metadata(
    session: AsyncSession,
    *,
    metadata_url: str | None = None,
    updated_by_id: str,
    timeout: int = 15,
) -> dict[str, str]:
    if not metadata_url:
        metadata_url = str(await system_params.get(session, METADATA_URL_KEY, "") or "").strip()
    if not metadata_url:
        raise HTTPException(400, "auth.saml.idp.metadata_url is not configured")

    try:
        data = OneLogin_Saml2_IdPMetadataParser.parse_remote(
            metadata_url,
            validate_cert=False,
            timeout=timeout,
        )
    except Exception as exc:
        logger.error("Failed to fetch IdP metadata from %s: %s", metadata_url, exc)
        raise HTTPException(502, f"Failed to fetch IdP metadata: {exc}") from exc

    idp = data.get("idp", {})
    if not idp:
        raise HTTPException(502, "IdP metadata did not contain an IDPSSODescriptor")

    certs = idp.get("x509certMulti", {}).get("signing") or []
    if not certs and idp.get("x509cert"):
        certs = [idp["x509cert"]]
    if not certs:
        raise HTTPException(502, "No signing certificate found in IdP metadata")

    new_cert = certs[0]
    old_cert = str(await system_params.get(session, CERT_PARAM_KEY, "") or "").strip()
    cert_changed = _normalize(new_cert) != _normalize(old_cert)

    result: dict[str, str] = {
        "metadata_url": metadata_url,
        "cert_changed": str(cert_changed),
        "signing_certs_found": str(len(certs)),
        "refreshed_at": datetime.now(UTC).isoformat(),
    }

    if cert_changed:
        await system_params.update(session, CERT_PARAM_KEY, new_cert, updated_by_id)
        logger.info("IdP signing certificate updated from metadata")

    entity_id = idp.get("entityId")
    if entity_id:
        old_entity_id = str(await system_params.get(session, ENTITY_ID_PARAM_KEY, "") or "").strip()
        if entity_id != old_entity_id and old_entity_id:
            result["entity_id_in_metadata"] = entity_id
            result["entity_id_current"] = old_entity_id

    sso_service = idp.get("singleSignOnService", {})
    sso_url = sso_service.get("url") if isinstance(sso_service, dict) else None
    if sso_url:
        result["sso_url_in_metadata"] = sso_url

    await session.commit()
    return result


def _normalize(cert: str) -> str:
    return (
        cert.replace("-----BEGIN CERTIFICATE-----", "")
        .replace("-----END CERTIFICATE-----", "")
        .replace("\n", "")
        .replace("\r", "")
        .replace(" ", "")
        .strip()
    )
