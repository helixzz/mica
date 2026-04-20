from datetime import datetime, timezone
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
from app.schemas import CompanyOut, DepartmentOut, LoginRequest, TokenResponse, UserOut

settings = get_settings()

router = APIRouter()


@router.post("/auth/login", response_model=TokenResponse, tags=["auth"])
async def login(
    request: Request,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    locale = detect_locale(request)
    result = await db.execute(select(User).where(User.username == form_data.username))
    user = result.scalar_one_or_none()
    if user is None or not user.password_hash or not verify_password(
        form_data.password, user.password_hash
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=t("auth.invalid_credentials", locale),
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(401, detail=t("auth.user_inactive", locale))

    user.last_login_at = datetime.now(timezone.utc)
    await db.commit()

    token = create_access_token(str(user.id), extra={"role": user.role})
    return TokenResponse(
        access_token=token,
        expires_in=settings.access_token_expire_minutes * 60,
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
    if user is None or not user.password_hash or not verify_password(
        payload.password, user.password_hash
    ):
        raise HTTPException(401, detail=t("auth.invalid_credentials", locale))
    if not user.is_active:
        raise HTTPException(401, detail=t("auth.user_inactive", locale))

    user.last_login_at = datetime.now(timezone.utc)
    await db.commit()

    token = create_access_token(str(user.id), extra={"role": user.role})
    return TokenResponse(
        access_token=token,
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.get("/auth/me", response_model=UserOut, tags=["auth"])
async def get_me(user: CurrentUser) -> UserOut:
    return UserOut.model_validate(user)


@router.get("/companies", response_model=list[CompanyOut], tags=["org"])
async def list_companies(
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[CompanyOut]:
    result = await db.execute(select(Company).where(Company.is_active == True))  # noqa: E712
    return [CompanyOut.model_validate(c) for c in result.scalars().all()]


@router.get("/departments", response_model=list[DepartmentOut], tags=["org"])
async def list_departments(
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[DepartmentOut]:
    result = await db.execute(
        select(Department).where(
            Department.company_id == user.company_id,
            Department.is_active == True,  # noqa: E712
        )
    )
    return [DepartmentOut.model_validate(d) for d in result.scalars().all()]
