from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser
from app.db import get_db
from app.schemas import SearchResponse
from app.services.search import suggest_search, unified_search

router = APIRouter()


def _parse_types(raw_types: str | None) -> list[str] | None:
    if not raw_types:
        return None
    parsed = [item.strip() for item in raw_types.split(",") if item.strip()]
    return parsed or None


@router.get("/search", response_model=SearchResponse, tags=["search"])
async def search(
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    q: Annotated[str, Query(min_length=1)],
    types: str | None = None,
    limit: int = 30,
    limit_per_type: int = 5,
):
    return await unified_search(
        db,
        actor=user,
        query=q,
        entity_types=_parse_types(types),
        limit_per_type=limit_per_type,
        overall_limit=limit,
    )


@router.get("/search/suggest", tags=["search"])
async def suggest(
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    q: Annotated[str, Query(min_length=1)],
    limit: int = 10,
):
    return await suggest_search(db, actor=user, query=q, limit=limit)
