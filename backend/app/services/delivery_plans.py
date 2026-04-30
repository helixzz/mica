from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    DeliveryPlan,
    Item,
    POContractLink,
    POItem,
    PurchaseOrder,
    Shipment,
    ShipmentItem,
)
from app.schemas import (
    DeliveryPlanCreate,
    DeliveryPlanOut,
    DeliveryPlanOverview,
    DeliveryPlanUpdate,
)


async def _get_actual_qty_for_plan(db: AsyncSession, plan: DeliveryPlan) -> tuple[int, date | None]:
    """Compute actual shipped qty for a delivery plan by matching items through shipments."""
    conditions = []
    if plan.po_id is not None:
        conditions.append(Shipment.po_id == plan.po_id)
    if plan.contract_id is not None:
        conditions.append(Shipment.contract_id == plan.contract_id)

    actual = await db.execute(
        select(func.coalesce(func.sum(ShipmentItem.qty_shipped), 0))
        .join(Shipment, Shipment.id == ShipmentItem.shipment_id)
        .join(POItem, POItem.id == ShipmentItem.po_item_id)
        .where(and_(POItem.item_id == plan.item_id, or_(*conditions)))
    )
    qty = actual.scalar() or 0
    actual_qty = int(qty) if isinstance(qty, (Decimal, float)) else qty

    latest_date_result = await db.execute(
        select(func.max(Shipment.actual_date))
        .join(ShipmentItem, ShipmentItem.shipment_id == Shipment.id)
        .join(POItem, POItem.id == ShipmentItem.po_item_id)
        .where(and_(POItem.item_id == plan.item_id, or_(*conditions)))
    )
    actual_date = latest_date_result.scalar()

    return actual_qty, actual_date


async def _plan_to_out(db: AsyncSession, plan: DeliveryPlan) -> DeliveryPlanOut:
    item_name: str | None = None
    if plan.item_id:
        item = await db.get(Item, plan.item_id)
        if item:
            item_name = item.name

    actual_qty, actual_date = await _get_actual_qty_for_plan(db, plan)

    return DeliveryPlanOut(
        id=plan.id,
        po_id=plan.po_id,
        contract_id=plan.contract_id,
        item_id=plan.item_id,
        item_name=item_name,
        plan_name=plan.plan_name,
        planned_qty=plan.planned_qty,
        planned_date=plan.planned_date,
        actual_qty=actual_qty,
        actual_date=actual_date,
        status=plan.status,
        notes=plan.notes,
        created_at=plan.created_at,
        updated_at=plan.updated_at,
    )


async def create_delivery_plan(
    db: AsyncSession, data: DeliveryPlanCreate, user_id: UUID
) -> DeliveryPlan:
    plan = DeliveryPlan(
        po_id=data.po_id,
        contract_id=data.contract_id,
        item_id=data.item_id,
        plan_name=data.plan_name,
        planned_qty=data.planned_qty,
        planned_date=data.planned_date,
        notes=data.notes,
        created_by_id=user_id,
    )
    db.add(plan)
    await db.flush()
    await db.refresh(plan)
    return plan


async def update_delivery_plan(
    db: AsyncSession, plan_id: UUID, data: DeliveryPlanUpdate
) -> DeliveryPlan:
    plan = await db.get(DeliveryPlan, plan_id)
    if plan is None:
        raise HTTPException(404, "delivery_plan.not_found")

    upd = data.model_dump(exclude_unset=True)
    for key, value in upd.items():
        setattr(plan, key, value)

    await db.flush()
    await db.refresh(plan)
    return plan


async def delete_delivery_plan(db: AsyncSession, plan_id: UUID) -> None:
    plan = await db.get(DeliveryPlan, plan_id)
    if plan is None:
        raise HTTPException(404, "delivery_plan.not_found")
    await db.delete(plan)
    await db.flush()


async def get_delivery_plan(db: AsyncSession, plan_id: UUID) -> DeliveryPlan | None:
    return await db.get(DeliveryPlan, plan_id, options=[selectinload(DeliveryPlan.item)])


async def list_delivery_plans(
    db: AsyncSession,
    po_id: UUID | None = None,
    contract_id: UUID | None = None,
    status: str | None = None,
) -> list[DeliveryPlanOut]:
    stmt = select(DeliveryPlan).options(selectinload(DeliveryPlan.item))
    if po_id is not None:
        stmt = stmt.where(DeliveryPlan.po_id == po_id)
    if contract_id is not None:
        stmt = stmt.where(DeliveryPlan.contract_id == contract_id)
    if status is not None:
        stmt = stmt.where(DeliveryPlan.status == status)

    result = await db.execute(stmt)
    plans = result.scalars().all()

    outs: list[DeliveryPlanOut] = []
    for plan in plans:
        out = await _plan_to_out(db, plan)
        outs.append(out)
    return outs


async def get_po_delivery_summary(db: AsyncSession, po_id: UUID) -> DeliveryPlanOverview:
    po = await db.get(PurchaseOrder, po_id)
    if po is None:
        raise HTTPException(404, "po.not_found")

    # Get PO's own delivery plans
    own_plans_result = await db.execute(
        select(DeliveryPlan)
        .options(selectinload(DeliveryPlan.item))
        .where(DeliveryPlan.po_id == po_id)
    )
    own_plans = own_plans_result.scalars().all()

    # Get linked contract plans via po_contract_links
    link_result = await db.execute(
        select(POContractLink.contract_id).where(POContractLink.po_id == po_id)
    )
    linked_contract_ids = [r[0] for r in link_result.all()]

    linked_plans: list[DeliveryPlan] = []
    if linked_contract_ids:
        linked_result = await db.execute(
            select(DeliveryPlan)
            .options(selectinload(DeliveryPlan.item))
            .where(DeliveryPlan.contract_id.in_(linked_contract_ids))
        )
        linked_plans = list(linked_result.scalars().all())

    all_plans = list(own_plans) + linked_plans
    plan_outs: list[DeliveryPlanOut] = []
    total_planned: int = 0
    total_actual: int = 0

    for plan in all_plans:
        out = await _plan_to_out(db, plan)
        plan_outs.append(out)
        total_planned += plan.planned_qty
        total_actual += out.actual_qty

    completion_pct = (total_actual / total_planned * 100.0) if total_planned > 0 else 0.0

    return DeliveryPlanOverview(
        total_planned=total_planned,
        total_actual=total_actual,
        completion_pct=round(completion_pct, 1),
        plans=plan_outs,
    )
