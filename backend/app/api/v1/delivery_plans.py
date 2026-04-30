from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser, require_roles
from app.db import get_db
from app.schemas import (
    DeliveryPlanCreate,
    DeliveryPlanOut,
    DeliveryPlanOverview,
    DeliveryPlanUpdate,
)
from app.services import delivery_plans as svc

router = APIRouter()


@router.get(
    "/delivery-plans",
    response_model=list[DeliveryPlanOut],
    tags=["delivery-plans"],
)
async def list_plans(
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    po_id: UUID | None = Query(None),
    contract_id: UUID | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
):
    return await svc.list_delivery_plans(
        db, po_id=po_id, contract_id=contract_id, status=status_filter
    )


@router.get(
    "/delivery-plans/overview",
    response_model=DeliveryPlanOverview,
    tags=["delivery-plans"],
)
async def list_all_plans_overview(
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    plans = await svc.list_delivery_plans(db)
    total_planned = sum(p.planned_qty for p in plans)
    total_actual = sum(p.actual_qty for p in plans)
    return DeliveryPlanOverview(
        total_planned=total_planned,
        total_actual=total_actual,
        completion_pct=round(total_actual / total_planned * 100, 1) if total_planned > 0 else 0,
        plans=plans,
    )


@router.post(
    "/delivery-plans",
    response_model=DeliveryPlanOut,
    status_code=status.HTTP_201_CREATED,
    tags=["delivery-plans"],
)
async def create_plan(
    payload: DeliveryPlanCreate,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    _role: Annotated[
        None,
        Depends(require_roles("admin", "procurement_mgr", "it_buyer")),
    ],
):
    plan = await svc.create_delivery_plan(db, payload, user.id)
    return await svc._plan_to_out(db, plan)


@router.put(
    "/delivery-plans/{plan_id}",
    response_model=DeliveryPlanOut,
    tags=["delivery-plans"],
)
async def update_plan(
    plan_id: UUID,
    payload: DeliveryPlanUpdate,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    _role: Annotated[
        None,
        Depends(require_roles("admin", "procurement_mgr", "it_buyer")),
    ],
):
    plan = await svc.update_delivery_plan(db, plan_id, payload)
    return await svc._plan_to_out(db, plan)


@router.delete(
    "/delivery-plans/{plan_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["delivery-plans"],
)
async def delete_plan(
    plan_id: UUID,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    _role: Annotated[
        None,
        Depends(require_roles("admin", "procurement_mgr")),
    ],
):
    await svc.delete_delivery_plan(db, plan_id)


@router.get(
    "/purchase-orders/{po_id}/delivery-plan",
    response_model=DeliveryPlanOverview,
    tags=["delivery-plans"],
)
async def get_po_delivery_summary(
    po_id: UUID,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await svc.get_po_delivery_summary(db, po_id)
