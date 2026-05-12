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
    try:
        from sqlalchemy import select

        from app.models import NotificationCategory, PurchaseOrder, User, UserRole
        from app.services.notifications import create_notification
        from app.services.system_params import notification_enabled

        if await notification_enabled(db, "delivery_plan_created"):
            po = None
            contract = None
            if payload.po_id:
                po = await db.get(PurchaseOrder, payload.po_id)
            elif payload.contract_id:
                from app.models import Contract

                contract = await db.get(Contract, payload.contract_id)
                if contract:
                    po = await db.get(PurchaseOrder, contract.po_id)

            if po and po.created_by_id:
                recipients = {po.created_by_id}
                admin_rows = (
                    (
                        await db.execute(
                            select(User.id).where(
                                User.role.in_(
                                    [UserRole.ADMIN.value, UserRole.PROCUREMENT_MGR.value]
                                ),
                                User.is_active.is_(True),
                            )
                        )
                    )
                    .scalars()
                    .all()
                )
                recipients.update(admin_rows)
                for uid in recipients:
                    await create_notification(
                        db,
                        user_id=uid,
                        category=NotificationCategory.SYSTEM,
                        title=f"Delivery plan created: {plan.plan_name}",
                        body=(
                            f"**Plan**: {plan.plan_name}\n"
                            f"**PO**: {po.po_number}\n"
                            + (f"**Contract**: {contract.contract_number}\n" if contract else "")
                            + f"**Item**: {plan.item_name or '—'}\n"
                            f"**Qty**: {plan.planned_qty} | **Date**: {plan.planned_date}\n"
                            f"**Created by**: {user.display_name}"
                        ),
                        link_url=f"/purchase-orders/{payload.po_id}",
                        biz_type="delivery_plan",
                        biz_id=plan.id,
                    )
                await db.commit()
    except Exception:
        pass

    return await svc._plan_to_out(db, plan)


@router.patch(
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
    result = await svc._plan_to_out(db, plan)

    try:
        from sqlalchemy import select

        from app.models import NotificationCategory, PurchaseOrder, User, UserRole
        from app.services.notifications import create_notification
        from app.services.system_params import notification_enabled

        if await notification_enabled(db, "delivery_plan_updated"):
            po = None
            contract = None
            if plan.po_id:
                po = await db.get(PurchaseOrder, plan.po_id)
            elif plan.contract_id:
                from app.models import Contract

                contract = await db.get(Contract, plan.contract_id)
                if contract:
                    po = await db.get(PurchaseOrder, contract.po_id)
            if po and po.created_by_id:
                recipients = {po.created_by_id}
                admin_rows = (
                    (
                        await db.execute(
                            select(User.id).where(
                                User.role.in_(
                                    [UserRole.ADMIN.value, UserRole.PROCUREMENT_MGR.value]
                                ),
                                User.is_active.is_(True),
                            )
                        )
                    )
                    .scalars()
                    .all()
                )
                recipients.update(admin_rows)
                changes = []
                upd = payload.model_dump(exclude_unset=True)
                for k, v in upd.items():
                    if k == "item_id":
                        continue
                    old_val = getattr(plan, k, None)
                    if old_val == v:
                        continue
                    if old_val is None and v is None:
                        continue
                    label = k
                    if k == "plan_name":
                        label = "计划名称"
                    elif k == "planned_qty":
                        label = "计划数量"
                    elif k == "planned_date":
                        label = "计划日期"
                    elif k == "notes":
                        label = "备注"
                    elif k == "status":
                        label = "状态"
                    elif k == "contract_id":
                        label = "关联合同"
                    elif k == "po_id":
                        label = "关联PO"
                    changes.append(f"- **{label}**: {old_val} → {v}")
                changes_str = "\n".join(changes) if changes else "—"
                item_name = getattr(plan.item, "name", "") if plan.item else ""
                for uid in recipients:
                    await create_notification(
                        db,
                        user_id=uid,
                        category=NotificationCategory.SYSTEM,
                        title=f"Delivery plan updated: {plan.plan_name}",
                        body=(
                            f"**Plan**: {plan.plan_name} | **PO**: {po.po_number if po else '—'}\n"
                            f"**Item**: {item_name or '—'}\n"
                            f"**Qty**: {plan.planned_qty} | **Date**: {plan.planned_date}\n"
                            + (f"**Changes**:\n{changes_str}\n" if changes else "")
                            + f"**Updated by**: {user.display_name}"
                        ),
                        link_url=f"/purchase-orders/{po.id}",
                        biz_type="delivery_plan",
                        biz_id=plan.id,
                    )
                await db.commit()
    except Exception:
        pass

    return result


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
