from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser, require_roles
from app.db import get_db
from app.models import User, UserRole
from app.schemas import (
    FulfillmentLinkCreateIn,
    FulfillmentLinkOut,
    FulfillmentLinkUpdateIn,
    POItemOut,
    POListOut,
    POOut,
    PRConversionPreviewGroup,
    PRCreateIn,
    PRDecisionIn,
    PRListOut,
    PROut,
    PRPartialConvertIn,
    PRQuoteCandidate,
    PRSaveQuotesIn,
    PRSaveQuotesOut,
    PRUpdateIn,
    SupplementaryPOItemIn,
)
from app.services import export_pdf
from app.services import purchase as svc

router = APIRouter()


class ProxyCandidateOut(BaseModel):
    id: UUID
    display_name: str
    email: str
    role: str
    department_id: UUID | None
    company_id: UUID


@router.get(
    "/purchase-requisitions/proxy-candidates",
    response_model=list[ProxyCandidateOut],
    tags=["purchase"],
)
async def list_proxy_candidates(
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[ProxyCandidateOut]:
    allowed = {
        UserRole.ADMIN.value,
        UserRole.PROCUREMENT_MGR.value,
        UserRole.IT_BUYER.value,
    }
    if user.role not in allowed:
        raise HTTPException(403, "pr.proxy_not_allowed")
    rows = (
        (await db.execute(select(User).where(User.is_active.is_(True)).order_by(User.display_name)))
        .scalars()
        .all()
    )
    return [
        ProxyCandidateOut(
            id=u.id,
            display_name=u.display_name,
            email=u.email,
            role=u.role,
            department_id=u.department_id,
            company_id=u.company_id,
        )
        for u in rows
    ]


@router.get("/purchase-requisitions", response_model=list[PRListOut], tags=["purchase"])
async def list_prs(
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    items = await svc.list_prs_for_user(db, user)
    return [PRListOut.model_validate(i) for i in items]


@router.post(
    "/purchase-requisitions",
    response_model=PROut,
    status_code=status.HTTP_201_CREATED,
    tags=["purchase"],
)
async def create_pr(
    payload: PRCreateIn,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    pr = await svc.create_pr(db, user, payload)
    return PROut.model_validate(pr)


@router.get("/purchase-requisitions/{pr_id}", response_model=PROut, tags=["purchase"])
async def get_pr(
    pr_id: UUID,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    pr = await svc.get_pr(db, user, pr_id)
    return PROut.model_validate(pr)


@router.get("/purchase-requisitions/{pr_id}/downstream", tags=["purchase"])
async def get_pr_downstream(
    pr_id: UUID,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await svc.get_pr_downstream(db, user, pr_id)


@router.patch("/purchase-requisitions/{pr_id}", response_model=PROut, tags=["purchase"])
async def update_pr(
    pr_id: UUID,
    payload: PRUpdateIn,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    pr = await svc.update_pr(db, user, pr_id, payload)
    return PROut.model_validate(pr)


@router.post("/purchase-requisitions/{pr_id}/submit", response_model=PROut, tags=["purchase"])
async def submit_pr(
    pr_id: UUID,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    pr = await svc.submit_pr(db, user, pr_id)
    return PROut.model_validate(pr)


@router.delete("/purchase-requisitions/{pr_id}", status_code=204, tags=["purchase"])
async def delete_pr(
    pr_id: UUID,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await svc.delete_pr(db, user, pr_id)


@router.post("/purchase-requisitions/{pr_id}/decide", response_model=PROut, tags=["purchase"])
async def decide_pr(
    pr_id: UUID,
    payload: PRDecisionIn,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    _role: Annotated[None, Depends(require_roles("admin", "dept_manager", "procurement_mgr"))],
):
    pr = await svc.decide_pr(db, user, pr_id, payload)
    return PROut.model_validate(pr)


@router.get(
    "/purchase-requisitions/{pr_id}/conversion-preview",
    response_model=list[PRConversionPreviewGroup],
    tags=["purchase"],
)
async def preview_pr_conversion(
    pr_id: UUID,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await svc.preview_pr_conversion(db, user, pr_id)


@router.post(
    "/purchase-requisitions/{pr_id}/convert-to-po",
    response_model=list[POOut],
    status_code=status.HTTP_201_CREATED,
    tags=["purchase"],
)
async def convert_pr_to_po(
    pr_id: UUID,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    _role: Annotated[None, Depends(require_roles("admin", "it_buyer", "procurement_mgr"))],
):
    pos = await svc.convert_pr_to_po(db, user, pr_id)
    return [POOut.model_validate(po) for po in pos]


@router.post(
    "/purchase-requisitions/{pr_id}/convert-to-po/partial",
    response_model=list[POOut],
    status_code=status.HTTP_201_CREATED,
    tags=["purchase"],
)
async def convert_pr_to_po_partial(
    pr_id: UUID,
    payload: PRPartialConvertIn,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    _role: Annotated[None, Depends(require_roles("admin", "it_buyer", "procurement_mgr"))],
):
    pos = await svc.convert_pr_to_po_partial(db, user, pr_id, payload.pr_item_ids)
    return [POOut.model_validate(po) for po in pos]


@router.get(
    "/purchase-requisitions/{pr_id}/quote-candidates",
    response_model=list[PRQuoteCandidate],
    tags=["purchase"],
)
async def list_pr_quote_candidates(
    pr_id: UUID,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await svc.list_pr_quote_candidates(db, user, pr_id)


@router.post(
    "/purchase-requisitions/{pr_id}/save-quotes",
    response_model=PRSaveQuotesOut,
    tags=["purchase"],
)
async def save_pr_supplier_quotes(
    pr_id: UUID,
    payload: PRSaveQuotesIn,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    _role: Annotated[None, Depends(require_roles("admin", "it_buyer", "procurement_mgr"))],
):
    candidates_before = await svc.list_pr_quote_candidates(db, user, pr_id)
    rows = await svc.save_pr_supplier_quotes(db, user, pr_id, payload.line_nos)
    skipped = sum(
        1
        for c in candidates_before
        if c["already_up_to_date"]
        and (payload.line_nos is None or c["line_no"] in set(payload.line_nos))
    )
    return PRSaveQuotesOut(
        written_count=len(rows) - skipped,
        skipped_unchanged_count=skipped,
    )


@router.get("/purchase-orders", response_model=list[POListOut], tags=["purchase"])
async def list_pos(
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    items = await svc.list_pos(db, user)
    return [POListOut.model_validate(i) for i in items]


@router.get("/purchase-orders/{po_id}", response_model=POOut, tags=["purchase"])
async def get_po(
    po_id: UUID,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    po = await svc.get_po(db, po_id, actor=user)
    return POOut.model_validate(po)


@router.delete("/purchase-orders/{po_id}", status_code=204, tags=["purchase"])
async def delete_po(
    po_id: UUID,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    _role: Annotated[None, Depends(require_roles("admin"))],
):
    await svc.delete_po(db, user, po_id)


@router.get("/purchase-orders/{po_id}/delivery-plans", tags=["purchase"])
async def get_po_delivery_plans(
    po_id: UUID,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    _role: Annotated[
        None,
        Depends(require_roles("admin", "it_buyer", "procurement_mgr", "finance_auditor")),
    ],
):
    """Return delivery plans for a specific PO."""
    from app.services import delivery_plans as dp_svc

    plans = await dp_svc.list_delivery_plans(db, po_id=po_id)
    # Also include contract-linked plans
    from sqlalchemy import select

    from app.models import Contract

    contracts = (
        (await db.execute(select(Contract.id).where(Contract.po_id == po_id))).scalars().all()
    )
    for cid in contracts:
        plans += await dp_svc.list_delivery_plans(db, contract_id=cid)
    plan_outs = [await dp_svc._plan_to_out(db, plan) for plan in plans]
    total_planned = sum(p.planned_qty for p in plans)
    total_actual = sum(p.actual_qty for p in plans)
    completion_pct = round(total_actual / total_planned * 100, 1) if total_planned > 0 else 0
    return {
        "po_plans": plan_outs,
        "contract_plans": [],
        "all_plans": plan_outs,
        "summary": {
            "total_planned": total_planned,
            "total_actual": total_actual,
            "completion_pct": completion_pct,
        },
    }


@router.get("/purchase-orders/{po_id}/export/pdf", tags=["purchase"])
async def export_po_pdf(
    po_id: UUID,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    _role: Annotated[
        None,
        Depends(require_roles("admin", "it_buyer", "procurement_mgr", "finance_auditor")),
    ],
):
    await svc.get_po(db, po_id, actor=user)
    pdf_bytes = await export_pdf.render_po_pdf(db, po_id)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="PO-{po_id}.pdf"',
            "Content-Length": str(len(pdf_bytes)),
        },
    )


@router.get("/purchase-requisitions/{pr_id}/collaborators", tags=["purchase"])
async def list_collaborators(
    pr_id: UUID,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await svc.get_pr(db, user, pr_id)
    return await svc.list_collaborators(db, pr_id)


class CollaboratorIn(BaseModel):
    user_id: UUID


@router.post(
    "/purchase-requisitions/{pr_id}/collaborators",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["purchase"],
)
async def add_collaborator(
    pr_id: UUID,
    payload: CollaboratorIn,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await svc.add_collaborator(db, user, pr_id, payload.user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete(
    "/purchase-requisitions/{pr_id}/collaborators/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["purchase"],
)
async def remove_collaborator(
    pr_id: UUID,
    user_id: UUID,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await svc.remove_collaborator(db, user, pr_id, user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/purchase-orders/{po_id}/items/{po_item_id}/fulfillment-link",
    response_model=FulfillmentLinkOut,
    status_code=status.HTTP_201_CREATED,
    tags=["purchase"],
)
async def create_fulfillment_link(
    po_id: UUID,
    po_item_id: UUID,
    payload: FulfillmentLinkCreateIn,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    _role: Annotated[None, Depends(require_roles("admin", "it_buyer", "procurement_mgr"))],
):
    po_item = await svc.get_po(db, po_id, user)
    if not any(item.id == po_item_id for item in po_item.items):
        raise HTTPException(404, "po_item.not_found")
    link = await svc.create_fulfillment_link(
        db,
        user,
        po_item_id=po_item_id,
        pr_item_id=payload.pr_item_id,
        fulfillment_type=payload.fulfillment_type,
        qty_contribution=payload.qty_contribution,
        deviation_note=payload.deviation_note,
    )
    return FulfillmentLinkOut.model_validate(link)


@router.patch(
    "/fulfillment-links/{link_id}",
    response_model=FulfillmentLinkOut,
    tags=["purchase"],
)
async def update_fulfillment_link(
    link_id: UUID,
    payload: FulfillmentLinkUpdateIn,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    _role: Annotated[None, Depends(require_roles("admin", "it_buyer", "procurement_mgr"))],
):
    link = await svc.update_fulfillment_link(
        db,
        user,
        link_id,
        fulfillment_type=payload.fulfillment_type,
        qty_contribution=payload.qty_contribution,
        deviation_note=payload.deviation_note,
    )
    return FulfillmentLinkOut.model_validate(link)


@router.delete(
    "/fulfillment-links/{link_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["purchase"],
)
async def delete_fulfillment_link(
    link_id: UUID,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    _role: Annotated[None, Depends(require_roles("admin", "it_buyer", "procurement_mgr"))],
):
    await svc.delete_fulfillment_link(db, user, link_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/purchase-orders/{po_id}/supplementary-items",
    response_model=POItemOut,
    status_code=status.HTTP_201_CREATED,
    tags=["purchase"],
)
async def add_supplementary_po_item(
    po_id: UUID,
    payload: SupplementaryPOItemIn,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    _role: Annotated[None, Depends(require_roles("admin", "it_buyer", "procurement_mgr"))],
):
    po_item = await svc.add_supplementary_po_item(
        db,
        user,
        po_id=po_id,
        item_name=payload.item_name,
        specification=payload.specification,
        item_id=payload.item_id,
        qty=payload.qty,
        uom=payload.uom,
        unit_price=payload.unit_price,
        supplementary_for_pr_item_id=payload.supplementary_for_pr_item_id,
        deviation_note=payload.deviation_note,
    )
    return POItemOut.model_validate(po_item)
