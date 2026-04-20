"""FastAPI application entry point."""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api import api_router
from app.config import get_settings
from app.db import AsyncSessionLocal
from app.i18n import detect_locale, t
from app.services.seed import seed_dev_data

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.auto_seed_on_startup and settings.app_env == "development":
        async with AsyncSessionLocal() as session:
            try:
                await seed_dev_data(session)
            except Exception as e:  # pragma: no cover
                print(f"[seed] warning: {e}")
    yield


app = FastAPI(
    title=f"{settings.app_name} API",
    version=settings.app_version,
    lifespan=lifespan,
    openapi_url=f"{settings.api_prefix}/openapi.json",
    docs_url=f"{settings.api_prefix}/docs",
    redoc_url=f"{settings.api_prefix}/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    locale = detect_locale(request)
    detail = exc.detail
    if isinstance(detail, str) and "." in detail and " " not in detail:
        translated = t(detail, locale)
        if translated != detail:
            detail = translated
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": detail, "code": exc.detail if isinstance(exc.detail, str) else None},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    locale = detect_locale(request)
    return JSONResponse(
        status_code=422,
        content={"detail": t("common.validation_error", locale), "errors": exc.errors()},
    )


@app.get("/health", tags=["meta"])
async def health() -> dict:
    return {"status": "ok", "app": settings.app_name, "version": settings.app_version}


@app.get("/", tags=["meta"])
async def root() -> dict:
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": f"{settings.api_prefix}/docs",
    }


app.include_router(api_router, prefix=settings.api_prefix)
