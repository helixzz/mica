from __future__ import annotations

import uuid
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import CurrentUser, require_roles
from app.db import get_db
from app.models import AuditLog, Document, DocumentTemplate
from app.services import document_templates as svc

router = APIRouter()

_DOCX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
_XLSX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


class DocumentTemplateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    code: str
    name: str
    description: str | None
    template_document_id: UUID | None
    template_filename: str | None = None
    template_size: int | None = None
    filename_template: str
    is_enabled: bool


class DocumentTemplateUpdateIn(BaseModel):
    name: str | None = Field(default=None, max_length=128)
    description: str | None = None
    filename_template: str | None = None
    is_enabled: bool | None = None


def _to_out(row: DocumentTemplate) -> DocumentTemplateOut:
    data = DocumentTemplateOut.model_validate(row)
    if row.template_document is not None:
        data.template_filename = row.template_document.original_filename
        data.template_size = row.template_document.file_size
    return data


@router.get(
    "/admin/document-templates",
    response_model=list[DocumentTemplateOut],
    tags=["admin"],
)
async def list_document_templates(
    _user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    _role: Annotated[None, Depends(require_roles("admin", "finance_auditor"))],
):
    rows = (
        (
            await db.execute(
                select(DocumentTemplate)
                .order_by(DocumentTemplate.code)
                .options(selectinload(DocumentTemplate.template_document))
            )
        )
        .scalars()
        .all()
    )
    return [_to_out(r) for r in rows]


@router.patch(
    "/admin/document-templates/{template_id}",
    response_model=DocumentTemplateOut,
    tags=["admin"],
)
async def update_document_template(
    template_id: UUID,
    payload: DocumentTemplateUpdateIn,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    _role: Annotated[None, Depends(require_roles("admin"))],
):
    row = await db.get(DocumentTemplate, template_id)
    if row is None:
        raise HTTPException(404, "template.not_found")
    updates = payload.model_dump(exclude_unset=True)
    changes: dict[str, object] = {}
    for key, value in updates.items():
        old = getattr(row, key)
        if old != value:
            changes[key] = {"from": old, "to": value}
            setattr(row, key, value)
    if changes:
        db.add(
            AuditLog(
                actor_id=user.id,
                actor_name=user.display_name,
                event_type="document_template.updated",
                resource_type="document_template",
                resource_id=str(row.id),
                metadata_json={"changes": changes},
            )
        )
        await db.commit()
        await db.refresh(row, attribute_names=["template_document"])
    return _to_out(row)


@router.post(
    "/admin/document-templates/{template_id}/upload",
    response_model=DocumentTemplateOut,
    tags=["admin"],
)
async def upload_document_template(
    template_id: UUID,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    file: UploadFile = File(...),
    _role: Annotated[None, Depends(require_roles("admin"))] = None,
):
    row = await db.get(DocumentTemplate, template_id)
    if row is None:
        raise HTTPException(404, "template.not_found")

    content = await file.read()
    if not file.filename or not (
        file.filename.lower().endswith(".docx") or file.filename.lower().endswith(".xlsx")
    ):
        raise HTTPException(400, "template.only_docx_supported")

    import hashlib
    from pathlib import Path

    from app.config import get_settings

    settings = get_settings()
    media_root = Path(getattr(settings, "media_root", "/app/media"))
    media_root.mkdir(parents=True, exist_ok=True)

    content_hash = hashlib.sha256(content).hexdigest()
    storage_key = f"templates/{content_hash}_{file.filename}"
    abs_path = media_root / storage_key
    abs_path.parent.mkdir(parents=True, exist_ok=True)
    abs_path.write_bytes(content)

    document = Document(
        id=uuid.uuid4(),
        storage_key=storage_key,
        storage_backend="local",
        original_filename=file.filename,
        content_type=(
            file.content_type
            or (
                _XLSX_CONTENT_TYPE
                if file.filename.lower().endswith(".xlsx")
                else _DOCX_CONTENT_TYPE
            )
        ),
        file_size=len(content),
        content_hash=content_hash,
        doc_category="document_template",
        is_private=True,
        uploaded_by_id=user.id,
    )
    db.add(document)
    await db.flush()

    row.template_document_id = document.id
    db.add(
        AuditLog(
            actor_id=user.id,
            actor_name=user.display_name,
            event_type="document_template.uploaded",
            resource_type="document_template",
            resource_id=str(row.id),
            metadata_json={
                "original_filename": file.filename,
                "size": len(content),
            },
        )
    )
    await db.commit()
    await db.refresh(row, attribute_names=["template_document"])
    return _to_out(row)


@router.get(
    "/document-templates/{template_id}/placeholders",
    tags=["document-templates"],
)
async def inspect_template_placeholders(
    template_id: UUID,
    _user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    row = await db.get(DocumentTemplate, template_id)
    if row is None:
        raise HTTPException(404, "template.not_found")
    await db.refresh(row, attribute_names=["template_document"])
    file_bytes = None
    if row.template_document is not None:
        file_bytes = svc._read_document_bytes(row.template_document)
    placeholders = svc.extract_placeholders(file_bytes, row.filename_template)
    return {"placeholders": placeholders}


@router.post(
    "/payment-schedule-items/{schedule_item_id}/generate-document",
    tags=["document-templates"],
)
async def generate_schedule_document(
    schedule_item_id: UUID,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    template_code: str = Form(...),
):
    _ = user
    content, filename = await svc.generate_payment_document(
        db, template_code, schedule_item_id, actor=user
    )
    media_type = _XLSX_CONTENT_TYPE if filename.lower().endswith(".xlsx") else _DOCX_CONTENT_TYPE
    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(content)),
        },
    )
