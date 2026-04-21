"""SAML SSO endpoints (scaffolded, not wired to production ADFS yet).

Dev-mode: returns a helpful placeholder indicating how to configure SAML.
The local password login at /auth/login remains the primary dev flow.
"""

import os
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db

router = APIRouter()


@router.get("/saml/metadata", tags=["saml"])
async def saml_metadata() -> dict:
    return {
        "status": "not_configured",
        "message": (
            "SAML is scaffolded but not configured. "
            "To enable ADFS SAML: set SAML_ENABLED=true and provide IdP metadata "
            "(entityId, SSO URL, x509 cert) in environment variables, then install "
            "python3-saml in the backend image."
        ),
        "sp_entity_id_suggestion": os.environ.get(
            "SAML_SP_ENTITY_ID", "https://mica.example/saml/metadata"
        ),
        "sp_acs_suggestion": os.environ.get("SAML_SP_ACS", "https://mica.example/saml/acs"),
    }


@router.get("/saml/login", tags=["saml"])
async def saml_login_init() -> dict:
    if os.environ.get("SAML_ENABLED", "false").lower() != "true":
        raise HTTPException(
            503,
            "saml.not_enabled",
        )
    return {"status": "pending_implementation"}


@router.post("/saml/acs", tags=["saml"])
async def saml_acs(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    if os.environ.get("SAML_ENABLED", "false").lower() != "true":
        raise HTTPException(503, "saml.not_enabled")
    raise HTTPException(501, "saml.not_implemented")
