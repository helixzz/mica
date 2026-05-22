import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser, require_roles
from app.db import get_db
from app.models import Contract, NotificationCategory, PurchaseOrder, User, UserRole
from app.schemas import (
    DeliveryPlanCreate,
    DeliveryPlanOut,
    DeliveryPlanOverview,
    DeliveryPlanUpdate,
)
from app.services import delivery_plans as svc
from app.services.notifications import create_notification
from app.services.system_params import notification_enabled

logger = logging.getLogger("mica.delivery_plans")

router = APIRouter()


async def _get_labels() -> dict[str, dict[str, str]]:
    from app.i18n import notification_labels

    return {"zh-CN": notification_labels("zh-CN"), "en-US": notification_labels("en-US")}


async def _resolve_po(
    db: AsyncSession, po_id: UUID | None, contract_id: UUID | None
) -> tuple[PurchaseOrder | None, Contract | None]:
    """Get the PO for a delivery plan, resolving through contract if needed."""
    if po_id:
        return await db.get(PurchaseOrder, po_id), None
    if contract_id:
        contract = await db.get(Contract, contract_id)
        if contract:
            return await db.get(PurchaseOrder, contract.po_id), contract
    return None, None


async def _admin_recipients(db: AsyncSession) -> set[UUID]:
    rows = (
        (
            await db.execute(
                select(User.id).where(
                    User.role.in_([UserRole.ADMIN.value, UserRole.PROCUREMENT_MGR.value]),
                    User.is_active.is_(True),
                )
            )
        )
        .scalars()
        .all()
    )
    return set(rows)


async def _notify(
    db: AsyncSession, recipients: set[UUID], title_fn, body_fn, link_url: str, biz_id: UUID
) -> None:
    for uid in recipients:
        await create_notification(
            db,
            user_id=uid,
            category=NotificationCategory.SYSTEM,
            title=title_fn,
            body=body_fn,
            link_url=link_url,
            biz_type="delivery_plan",
            biz_id=biz_id,
        )
    await db.commit()


@router.get("/delivery-plans", response_model=list[DeliveryPlanOut], tags=["delivery-plans"])
async def list_plans(
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    po_id: UUID | None = Query(None),
    contract_id: UUID | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
):
    return await svc.list_delivery_plans(
        db, po_id=po_id, contract_id=contract_id, status=status_filter, actor=user
    )


@router.get(
    "/delivery-plans/overview", response_model=DeliveryPlanOverview, tags=["delivery-plans"]
)
async def list_all_plans_overview(user: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]):
    plans = await svc.list_delivery_plans(db, actor=user)
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
    _role: Annotated[None, Depends(require_roles("admin", "procurement_mgr", "it_buyer"))],
):
    plan = await svc.create_delivery_plan(db, payload, user.id)
    try:
        if await notification_enabled(db, "delivery_plan_created"):
            po, contract = await _resolve_po(db, payload.po_id, payload.contract_id)
            if po and po.created_by_id:
                recipients = {po.created_by_id} | await _admin_recipients(db)
                from app.models import PurchaseRequisition

                pr = await db.get(PurchaseRequisition, po.pr_id)
                if pr and pr.requester_id:
                    recipients.add(pr.requester_id)
                labels = await _get_labels()
                pn = plan.plan_name
                po_n = po.po_number
                pr_t = po.pr_title
                ct_n = contract.contract_number if contract else None
                item = plan.item_name
                qty = plan.planned_qty
                dt = plan.planned_date
                actor_n = user.display_name

                def _created_title(u, _pn=pn):
                    return f"Delivery plan created: {_pn}"

                def _created_body(u):
                    loc = u.preferred_locale if u and u.preferred_locale else "zh-CN"
                    L = labels.get(loc, labels["zh-CN"])
                    return (
                        f"**{L['plan']}**: {pn}\n**{L['po']}**: {po_n}\n**{L['pr']}**: {pr_t or '—'}\n"
                        + (f"**{L['contract']}**: {ct_n}\n" if ct_n else "")
                        + f"**{L['item']}**: {item or '—'}\n**{L['qty']}**: {qty} | **{L['date']}**: {dt}\n**{L['created_by']}**: {actor_n}"
                    )

                await _notify(
                    db,
                    recipients,
                    _created_title,
                    _created_body,
                    f"/purchase-orders/{po.id}",
                    plan.id,
                )
    except Exception:
        logger.warning("Failed delivery plan created notification", exc_info=True)
    return await svc._plan_to_out(db, plan)


@router.patch("/delivery-plans/{plan_id}", response_model=DeliveryPlanOut, tags=["delivery-plans"])
async def update_plan(
    plan_id: UUID,
    payload: DeliveryPlanUpdate,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    _role: Annotated[None, Depends(require_roles("admin", "procurement_mgr", "it_buyer"))],
):
    plan = await svc.update_delivery_plan(db, plan_id, payload)
    result = await svc._plan_to_out(db, plan)
    try:
        if await notification_enabled(db, "delivery_plan_updated"):
            po, _ = await _resolve_po(db, plan.po_id, plan.contract_id)
            if po and po.created_by_id:
                recipients = {po.created_by_id} | await _admin_recipients(db)
                from app.models import PurchaseRequisition

                pr = await db.get(PurchaseRequisition, po.pr_id)
                if pr and pr.requester_id:
                    recipients.add(pr.requester_id)
                labels = await _get_labels()
                changes = [
                    f"- **{k}**: {getattr(plan, k, None)} → {v}"
                    for k, v in payload.model_dump(exclude_unset=True).items()
                    if k != "item_id"
                    and getattr(plan, k, None) != v
                    and not (getattr(plan, k, None) is None and v is None)
                ]
                changes_str = "\n".join(changes) if changes else "—"
                plan_out = await svc._plan_to_out(db, plan)
                item_name = plan_out.item_name
                pn = plan.plan_name
                po_n = po.po_number
                pr_t = po.pr_title
                qty = plan.planned_qty
                dt = plan.planned_date
                actor_n = user.display_name

                def _updated_title(u, _pn=pn):
                    return f"Delivery plan updated: {_pn}"

                def _updated_body(u):
                    loc = u.preferred_locale if u and u.preferred_locale else "zh-CN"
                    L = labels.get(loc, labels["zh-CN"])
                    return (
                        f"**{L['plan']}**: {pn} | **{L['po']}**: {po_n}\n**{L['pr']}**: {pr_t or '—'}\n**{L['item']}**: {item_name or '—'}\n"
                        f"**{L['qty']}**: {qty} | **{L['date']}**: {dt}\n"
                        + (f"**{L['changes']}**:\n{changes_str}\n" if changes else "")
                        + f"**{L['updated_by']}**: {actor_n}"
                    )

                await _notify(
                    db,
                    recipients,
                    _updated_title,
                    _updated_body,
                    f"/purchase-orders/{po.id}",
                    plan.id,
                )
    except Exception:
        logger.warning("Failed delivery plan updated notification", exc_info=True)
    return result


@router.delete(
    "/delivery-plans/{plan_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["delivery-plans"]
)
async def delete_plan(
    plan_id: UUID,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    _role: Annotated[None, Depends(require_roles("admin", "procurement_mgr"))],
):
    await svc.delete_delivery_plan(db, plan_id)


@router.get(
    "/purchase-orders/{po_id}/delivery-plan",
    response_model=DeliveryPlanOverview,
    tags=["delivery-plans"],
)
async def get_po_delivery_summary(
    po_id: UUID, user: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]
):
    return await svc.get_po_delivery_summary(db, po_id)
