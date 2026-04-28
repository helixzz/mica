"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api import api_router
from app.config import get_settings
from app.db import AsyncSessionLocal
from app.i18n import detect_locale, t
from app.middleware.request_id import RequestIdMiddleware, install_log_filter
from app.services.seed import seed_dev_data

settings = get_settings()
install_log_filter()


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

app.add_middleware(RequestIdMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.cors_allow_all else settings.cors_origins,
    allow_origin_regex=None
    if settings.cors_allow_all
    else r"^http://(localhost|127\.0\.0\.1|10\.[0-9.]+|172\.(1[6-9]|2[0-9]|3[0-1])\.[0-9.]+|192\.168\.[0-9.]+)(:[0-9]+)?$",
    allow_credentials=not settings.cors_allow_all,
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
    request_id = getattr(request.state, "request_id", None)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": detail,
            "code": exc.detail if isinstance(exc.detail, str) else None,
            "request_id": request_id,
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    locale = detect_locale(request)
    errors = exc.errors()
    for error in errors:
        if "ctx" in error and isinstance(error["ctx"], dict):
            error["ctx"] = {k: str(v) for k, v in error["ctx"].items()}
    detail_parts = [
        f"{'.'.join(str(x) for x in e['loc'] if x != '__root__')}: {e['msg']}" for e in errors
    ]
    request_id = getattr(request.state, "request_id", None)
    return JSONResponse(
        status_code=422,
        content={
            "detail": "; ".join(detail_parts)
            if detail_parts
            else t("common.validation_error", locale),
            "errors": errors,
            "request_id": request_id,
        },
    )


@app.get("/health", tags=["meta"])
async def health() -> dict:
    import httpx
    from sqlalchemy import text

    checks: dict[str, bool | str] = {}
    overall = True

    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        checks["db"] = True
    except Exception:
        checks["db"] = False
        overall = False

    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get("http://cerbos:3593/")
            checks["cerbos"] = 200 <= resp.status_code < 300
            if not checks["cerbos"]:
                overall = False
    except Exception:
        checks["cerbos"] = False
        overall = False

    return {
        "status": "healthy" if overall else "degraded",
        "app": settings.app_name,
        "version": settings.app_version,
        "checks": checks,
    }


@app.get("/", tags=["meta"])
async def root() -> dict:
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": f"{settings.api_prefix}/docs",
    }


app.include_router(api_router, prefix=settings.api_prefix)
