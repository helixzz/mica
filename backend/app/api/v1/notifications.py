from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser
from app.db import get_db
from app.models import Notification, NotificationCategory
from app.schemas import (
    MarkReadRequest,
    NotificationListResponse,
    NotificationOut,
    SubscriptionOut,
    SubscriptionUpdate,
    UnreadCountResponse,
)
from app.services import notifications as svc

router = APIRouter(prefix="/notifications")


@router.get("", response_model=NotificationListResponse, tags=["notifications"])
async def list_notifications(
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    unread_only: bool = False,
    category: NotificationCategory | None = None,
    limit: int = 20,
    before_id: UUID | None = None,
):
    before_created_at = None
    if before_id is not None:
        cursor = await db.get(Notification, before_id)
        if cursor is None or cursor.user_id != user.id:
            raise HTTPException(404, "notification.not_found")
        before_created_at = cursor.created_at

    page_limit = max(1, min(limit, 100))
    rows = await svc.list_notifications(
        db,
        user_id=user.id,
        unread_only=unread_only,
        category=category,
        limit=page_limit + 1,
        before_created_at=before_created_at,
    )
    items = rows[:page_limit]
    return NotificationListResponse(
        items=[NotificationOut.model_validate(item) for item in items],
        has_more=len(rows) > page_limit,
    )


@router.get("/unread-count", response_model=UnreadCountResponse, tags=["notifications"])
async def unread_count(
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    counts = await svc.count_unread(db, user_id=user.id)
    return UnreadCountResponse.model_validate(counts)


@router.post("/mark-read", tags=["notifications"])
async def mark_read(
    payload: MarkReadRequest,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    updated = await svc.mark_read(
        db,
        user_id=user.id,
        notification_ids=payload.ids,
        all=payload.all,
    )
    return {"updated": updated}


@router.get("/subscriptions", response_model=list[SubscriptionOut], tags=["notifications"])
async def get_subscriptions(
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    subscriptions = await svc.get_subscriptions(db, user_id=user.id)
    return [SubscriptionOut.model_validate(item) for item in subscriptions]


@router.put(
    "/subscriptions/{category}",
    response_model=SubscriptionOut,
    tags=["notifications"],
)
async def update_subscription(
    category: NotificationCategory,
    payload: SubscriptionUpdate,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    subscription = await svc.upsert_subscription(
        db,
        user_id=user.id,
        category=category,
        in_app_enabled=payload.in_app_enabled,
        email_enabled=payload.email_enabled,
    )
    return SubscriptionOut.model_validate(subscription)
