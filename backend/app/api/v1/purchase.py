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
    PRCreateIn,
    PRDecisionIn,
    PRListOut,
    PROut,
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


@router.post(
    "/purchase-requisitions/{pr_id}/convert-to-po",
    response_model=POOut,
    status_code=status.HTTP_201_CREATED,
    tags=["purchase"],
)
async def convert_pr_to_po(
    pr_id: UUID,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    po = await svc.convert_pr_to_po(db, user, pr_id)
    return POOut.model_validate(po)


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
    po = await svc.get_po(db, po_id)
    return POOut.model_validate(po)


@router.get("/purchase-orders/{po_id}/export/pdf", tags=["purchase"])
async def export_po_pdf(
    po_id: UUID,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await svc.get_po(db, po_id)
    pdf_bytes = await export_pdf.render_po_pdf(db, po_id)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="PO-{po_id}.pdf"',
            "Content-Length": str(len(pdf_bytes)),
        },
    )
