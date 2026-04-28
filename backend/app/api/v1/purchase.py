from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser
from app.db import get_db
from app.schemas import (
    POListOut,
    POOut,
    PRConversionPreviewGroup,
    PRCreateIn,
    PRDecisionIn,
    PRListOut,
    PROut,
    PRQuoteCandidate,
    PRSaveQuotesIn,
    PRSaveQuotesOut,
    PRUpdateIn,
)
from app.services import export_pdf
from app.services import purchase as svc

router = APIRouter()


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


@router.post("/purchase-requisitions/{pr_id}/decide", response_model=PROut, tags=["purchase"])
async def decide_pr(
    pr_id: UUID,
    payload: PRDecisionIn,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
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
):
    pos = await svc.convert_pr_to_po(db, user, pr_id)
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


@router.get("/purchase-orders/{po_id}/export/pdf", tags=["purchase"])
async def export_po_pdf(
    po_id: UUID,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
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
