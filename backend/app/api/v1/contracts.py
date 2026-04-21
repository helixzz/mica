from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser
from app.db import get_db
from app.services import contracts as svc

router = APIRouter()


class AttachDocumentIn(BaseModel):
    document_id: UUID
    role: str = "scan"
    run_ocr: bool = True


@router.post("/contracts/{contract_id}/attachments", status_code=201, tags=["contracts"])
async def attach_doc(
    contract_id: UUID,
    payload: AttachDocumentIn,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    link = await svc.attach_document_to_contract(
        db, user, contract_id, payload.document_id, payload.role, payload.run_ocr
    )
    return {
        "contract_id": str(link.contract_id),
        "document_id": str(link.document_id),
        "role": link.role,
        "ocr_chars": len(link.ocr_text or ""),
    }


@router.get("/contracts/{contract_id}/attachments", tags=["contracts"])
async def list_attachments(
    contract_id: UUID,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    pairs = await svc.list_contract_documents(db, contract_id)
    return [svc.to_dict(cd, d) for cd, d in pairs]


@router.get("/contracts-search", tags=["contracts"])
async def search(
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    q: Annotated[str, Query(min_length=1)],
):
    return await svc.search_contracts(db, q)


@router.get("/contracts-expiring", tags=["contracts"])
async def list_expiring(
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    within_days: int | None = None,
):
    rows = await svc.expiring_contracts(db, within_days)
    return [
        {
            "id": str(r.id),
            "contract_number": r.contract_number,
            "title": r.title,
            "total_amount": str(r.total_amount),
            "currency": r.currency,
            "expiry_date": r.expiry_date.isoformat() if r.expiry_date else None,
        }
        for r in rows
    ]
