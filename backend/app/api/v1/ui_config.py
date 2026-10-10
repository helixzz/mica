"""User-facing UI configuration.

``pagination.default_page_size`` was seeded back in migration 0003 but nothing
ever read it, so an admin could change "默认分页大小" and every list kept its
hardcoded 20. This endpoint exposes the whitelisted, non-sensitive subset of
``system_parameters`` that the web client needs at boot.
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser
from app.db import get_db
from app.services.system_params import system_params

router = APIRouter()

# Keep this list explicit: only values that are safe for every signed-in user
# and that the UI genuinely consumes.
DEFAULT_PAGE_SIZE_PARAM = "pagination.default_page_size"
_FALLBACK_PAGE_SIZE = 20
_MIN_PAGE_SIZE = 5
_MAX_PAGE_SIZE = 200


@router.get("/ui-config", tags=["meta"])
async def get_ui_config(
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    page_size = await system_params.get_int_or(db, DEFAULT_PAGE_SIZE_PARAM, _FALLBACK_PAGE_SIZE)
    return {"default_page_size": max(_MIN_PAGE_SIZE, min(page_size, _MAX_PAGE_SIZE))}
