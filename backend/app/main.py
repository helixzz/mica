"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api import api_router, v2_router
from app.config import get_settings
from app.db import AsyncSessionLocal
from app.i18n import detect_locale, t
from app.middleware.perf_monitor import PerfMonitorMiddleware
from app.middleware.request_id import RequestIdMiddleware, install_log_filter
from app.services.seed import seed_dev_data

logging.basicConfig(level=logging.INFO, force=True)

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


_API_DESCRIPTION = """
Mica｜觅采 内部采购管理系统的 REST API。

## 认证

所有业务端点都要求在请求头携带凭据：

```
Authorization: Bearer <token>
```

服务端接受两种凭据，且两者都会解析为同一个用户：

* **PAT（Personal Access Token，推荐给脚本、其他系统与 AI Agent）** — 形如
  `mica_pat_...`，在「个人 → API 令牌」页面自助创建；可设有效期、可限定为只读、
  可随时撤销，明文只在创建响应里出现一次。
* **登录 JWT** — `POST /api/v1/auth/login`（form-urlencoded）或
  `POST /api/v1/auth/login/json`（JSON）获取，TTL 较短，适合人类在 UI 里使用。

PAT 以创建者的身份行事，权限与其本人完全一致；但凭据类与管理类操作必须由人类完成，
因此 PAT **不能**访问 `/admin/**`、`/auth/**`（`GET /auth/me` 除外）、`/saml/**`，
也不能创建、轮换或撤销令牌（`/me/tokens` 的写方法会返回 `403`）——否则一个泄露的令牌
可以比它被撤销更快地换新。读取自己的令牌列表（`GET /me/tokens`）是允许的。

## 约定

* 列表端点用 `limit` / `offset` 分页；单条资源用其 `id`（UUID）。
* 错误响应统一为 `{"detail": ..., "code": ..., "request_id": ...}`，`detail`
  可能是 i18n key（例如 `api_token.read_only`），`code` 与原始 key 一致。
* 每个 PAT 默认限流 600 请求/分钟（`api.rate_limit_per_minute`），超限返回
  `429` 与 `Retry-After`。
* 排障时请记录响应里的 `request_id`，它同时出现在后端日志中。
* 存在 `/api/v1` 与 `/api/v2` 两套等价路径；新集成建议使用 `/api/v1`。

更完整的接入说明（创建令牌、作用域、错误处理、AI Agent 建议）见仓库
`docs/API.md`。
"""

_OPENAPI_TAGS = [
    {"name": "auth", "description": "登录、当前用户、登录方式探测。"},
    {
        "name": "api-tokens",
        "description": (
            "API 令牌（PAT）自助管理：列表、创建、轮换、撤销。令牌以当前用户身份行事。"
        ),
    },
    {
        "name": "admin",
        "description": "后台管理端点。仅限 admin 角色，且 PAT 无法访问。",
    },
    {"name": "purchase", "description": "采购申请（PR）与采购订单（PO）。"},
    {"name": "flow", "description": "合同、到货、付款、发票等履约流程。"},
    {"name": "activity-logs", "description": "资源活动日志（时间线）。"},
    {"name": "exports", "description": "通用导出（xlsx / csv）。"},
]

app = FastAPI(
    title=f"{settings.app_name} API",
    version=settings.app_version,
    description=_API_DESCRIPTION,
    openapi_tags=_OPENAPI_TAGS,
    lifespan=lifespan,
    openapi_url=f"{settings.api_prefix}/openapi.json",
    docs_url=f"{settings.api_prefix}/docs",
    redoc_url=f"{settings.api_prefix}/redoc",
)

app.add_middleware(PerfMonitorMiddleware)
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
app.include_router(v2_router, prefix=settings.api_prefix)
