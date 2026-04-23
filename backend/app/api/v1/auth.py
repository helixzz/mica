from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.security import (
    CurrentUser,
    create_access_token,
    verify_password,
)
from app.db import get_db
from app.i18n import detect_locale, t
from app.models import Company, Department, User
from app.schemas import (
    CompanyOut,
    DepartmentOut,
    LoginOptionsResponse,
    LoginRequest,
    TokenResponse,
    UserOut,
)
from app.services.saml_config import SAML_LOGIN_URL, is_saml_login_available
from app.services.system_params import system_params

settings = get_settings()

router = APIRouter()


async def _access_token_ttl_minutes(db: AsyncSession) -> int:
    return await system_params.get_int_or(
        db,
        "auth.access_token_expire_minutes",
        settings.access_token_expire_minutes,
    )


@router.post("/auth/login", response_model=TokenResponse, tags=["auth"])
async def login(
    request: Request,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    locale = detect_locale(request)
    result = await db.execute(select(User).where(User.username == form_data.username))
    user = result.scalar_one_or_none()
    if (
        user is None
        or not user.password_hash
        or not verify_password(form_data.password, user.password_hash)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=t("auth.invalid_credentials", locale),
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(401, detail=t("auth.user_inactive", locale))

    user.last_login_at = datetime.now(UTC)
    await db.commit()

    access_token_ttl_minutes = int(await _access_token_ttl_minutes(db))
    token = create_access_token(
        str(user.id),
        extra={"role": user.role},
        expire_minutes=access_token_ttl_minutes,
    )
    return TokenResponse(
        access_token=token,
        expires_in=access_token_ttl_minutes * 60,
    )


@router.post("/auth/login/json", response_model=TokenResponse, tags=["auth"])
async def login_json(
    request: Request,
    payload: LoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    locale = detect_locale(request)
    result = await db.execute(select(User).where(User.username == payload.username))
    user = result.scalar_one_or_none()
    if (
        user is None
        or not user.password_hash
        or not verify_password(payload.password, user.password_hash)
    ):
        raise HTTPException(401, detail=t("auth.invalid_credentials", locale))
    if not user.is_active:
        raise HTTPException(401, detail=t("auth.user_inactive", locale))

    user.last_login_at = datetime.now(UTC)
    await db.commit()

    access_token_ttl_minutes = int(await _access_token_ttl_minutes(db))
    token = create_access_token(
        str(user.id),
        extra={"role": user.role},
        expire_minutes=access_token_ttl_minutes,
    )
    return TokenResponse(
        access_token=token,
        expires_in=access_token_ttl_minutes * 60,
    )


@router.get("/auth/me", response_model=UserOut, tags=["auth"])
async def get_me(user: CurrentUser) -> UserOut:
    return UserOut.model_validate(user)


@router.get("/auth/login-options", response_model=LoginOptionsResponse, tags=["auth"])
async def get_login_options(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> LoginOptionsResponse:
    locale = detect_locale(request)
    saml_enabled = await is_saml_login_available(db, request, locale)
    return LoginOptionsResponse(
        saml_enabled=saml_enabled,
        saml_login_url=SAML_LOGIN_URL if saml_enabled else None,
    )


@router.get("/companies", response_model=list[CompanyOut], tags=["org"])
async def list_companies(
    _user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    include_inactive: bool = False,
) -> list[CompanyOut]:
    stmt = select(Company).order_by(Company.code)
    if not include_inactive:
        stmt = stmt.where(Company.is_deleted.is_(False), Company.is_enabled.is_(True))
    result = await db.execute(stmt)
    return [CompanyOut.model_validate(c) for c in result.scalars().all()]


@router.get("/departments", response_model=list[DepartmentOut], tags=["org"])
async def list_departments(
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[DepartmentOut]:
    result = await db.execute(
        select(Department).where(
            Department.company_id == user.company_id,
            Department.is_deleted.is_(False),
            Department.is_enabled.is_(True),
        )
    )
    return [DepartmentOut.model_validate(d) for d in result.scalars().all()]
