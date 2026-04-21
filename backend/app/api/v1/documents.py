from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.security import CurrentUser
from app.db import get_db
from app.schemas import DocumentOut, DownloadTokenOut
from app.services import documents as doc_svc
from app.services.system_params import system_params

router = APIRouter()
settings = get_settings()


@router.post("/documents/upload", response_model=DocumentOut, tags=["documents"])
async def upload(
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    file: Annotated[UploadFile, File(...)],
    category: Annotated[str, Form()] = "invoice",
):
    doc = await doc_svc.upload_document(db, file, category, user)
    await db.commit()
    return DocumentOut.model_validate(doc)


@router.get(
    "/documents/{document_id}/token",
    response_model=DownloadTokenOut,
    tags=["documents"],
)
async def create_token(
    document_id: UUID,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    ttl_seconds = await system_params.get_int_or(
        db,
        "auth.download_token_ttl_seconds",
        settings.download_token_ttl_seconds,
    )
    tok = await doc_svc.create_download_token(db, document_id, user, ttl_seconds=ttl_seconds)
    await db.commit()
    return DownloadTokenOut(
        download_url=f"/api/v1/documents/download/{tok.token}",
        expires_in=ttl_seconds,
    )


@router.get("/documents/download/{token}", tags=["documents"])
async def download(
    token: str,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    import aiofiles

    doc = await doc_svc.consume_token(db, token)
    await db.commit()
    path = doc_svc.document_path(doc)
    chunk_size = await system_params.get_int_or(db, "upload.chunk_size_bytes", 1024 * 1024)

    async def iterator():
        async with aiofiles.open(path, "rb") as f:
            while chunk := await f.read(chunk_size):
                yield chunk

    return StreamingResponse(
        iterator(),
        media_type=doc.content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{doc.original_filename}"',
            "Content-Length": str(doc.file_size),
        },
    )
