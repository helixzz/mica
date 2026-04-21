from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser
from app.db import get_db
from app.schemas import AIFeaturePromptIn, InvoiceExtractOut
from app.services import ai as ai_svc
from app.services import documents as doc_svc
from app.services import invoice_extract as extract_svc

router = APIRouter()


@router.post("/ai/stream", tags=["ai"])
async def ai_stream(
    payload: AIFeaturePromptIn,
    request: Request,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    if payload.feature_code == "pr_description_polish":
        prompt = ai_svc.render_prompt("pr_description_polish", draft=payload.draft or "")
    else:
        query = payload.query or ""
        from sqlalchemy import select

        from app.models import Item

        items = (
            (
                await db.execute(
                    select(Item).where(Item.is_active.is_(True)).order_by(Item.name).limit(30)
                )
            )
            .scalars()
            .all()
        )
        catalog = (
            "\n".join(f"{i.code} | {i.name} | {i.specification or ''}" for i in items)
            or "(catalog empty)"
        )
        prompt = ai_svc.render_prompt("sku_suggest", query=query, catalog=catalog)

    async def event_generator():
        try:
            async for chunk in ai_svc.stream_feature(db, user, payload.feature_code, prompt):
                if await request.is_disconnected():
                    break
                yield f"data: {chunk}\n\n"
        finally:
            yield "event: done\ndata: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.post("/ai/invoice-extract", response_model=InvoiceExtractOut, tags=["ai"])
async def ai_invoice_extract(
    document_id: UUID,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    from app.models import Document

    doc = await db.get(Document, document_id)
    if doc is None or doc.deleted_at is not None:
        raise HTTPException(404, "document.not_found")
    content = await doc_svc.read_document_bytes(doc)
    result = await extract_svc.extract_invoice(
        db, user, content, doc.content_type, doc.original_filename
    )
    await db.commit()
    return InvoiceExtractOut(**extract_svc.to_dict(result))
