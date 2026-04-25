from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import aiofiles
from fastapi import HTTPException, UploadFile
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import Document, DocumentDownloadToken, User
from app.services.system_params import system_params

settings = get_settings()

ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "application/xml",
    "text/xml",
    "application/ofd",
    "application/octet-stream",
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
    "image/tiff",
    "image/bmp",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
    "text/csv",
    "text/plain",
    "application/zip",
    "application/x-zip-compressed",
}


def _media_root() -> Path:
    return Path(settings.media_root)


def _uploads_dir() -> Path:
    return _media_root() / "uploads"


def _storage_key(content_hash: str, original_filename: str) -> str:
    suffix = Path(original_filename).suffix.lower() or ".bin"
    return f"{content_hash[:2]}/{content_hash}{suffix}"


async def _stream_read_and_hash(db: AsyncSession, file: UploadFile) -> tuple[str, int, bytes]:
    hasher = hashlib.sha256()
    chunks: list[bytes] = []
    size = 0
    chunk_size = await system_params.get_int(db, "upload.chunk_size_bytes")
    max_file_size = await system_params.get_int(db, "upload.max_file_size_bytes")
    while True:
        chunk = await file.read(chunk_size)
        if not chunk:
            break
        hasher.update(chunk)
        chunks.append(chunk)
        size += len(chunk)
        if size > max_file_size:
            raise HTTPException(413, "file.too_large")
    return hasher.hexdigest(), size, b"".join(chunks)


async def upload_document(
    db: AsyncSession,
    file: UploadFile,
    doc_category: str,
    uploaded_by: User,
) -> Document:
    content_type = file.content_type or "application/octet-stream"
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(415, f"file.unsupported_type:{content_type}")

    content_hash, file_size, content = await _stream_read_and_hash(db, file)

    existing = (
        await db.execute(
            select(Document).where(
                Document.content_hash == content_hash,
                Document.storage_backend == "local",
                Document.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if existing:
        return existing

    key = _storage_key(content_hash, file.filename or "upload.bin")
    dest = _uploads_dir() / key
    dest.parent.mkdir(parents=True, exist_ok=True)

    tmp = dest.with_suffix(dest.suffix + ".tmp")
    async with aiofiles.open(tmp, "wb") as f:
        await f.write(content)
    _ = tmp.rename(dest)

    doc = Document(
        storage_key=key,
        storage_backend="local",
        original_filename=file.filename or "upload.bin",
        content_type=content_type,
        file_size=file_size,
        content_hash=content_hash,
        doc_category=doc_category,
        uploaded_by_id=uploaded_by.id,
    )
    db.add(doc)
    await db.flush()
    return doc


async def read_document_bytes(doc: Document) -> bytes:
    path = _uploads_dir() / doc.storage_key
    async with aiofiles.open(path, "rb") as f:
        return await f.read()


def document_path(doc: Document) -> Path:
    return _uploads_dir() / doc.storage_key


async def create_download_token(
    db: AsyncSession,
    document_id: UUID,
    created_by: User,
    ttl_seconds: int | None = None,
) -> DocumentDownloadToken:
    doc = await db.get(Document, document_id)
    if doc is None or doc.deleted_at is not None:
        raise HTTPException(404, "document.not_found")
    resolved_ttl_seconds = ttl_seconds or settings.download_token_ttl_seconds
    tok = DocumentDownloadToken(
        token=secrets.token_urlsafe(32),
        document_id=document_id,
        created_by_id=created_by.id,
        expires_at=datetime.now(UTC) + timedelta(seconds=resolved_ttl_seconds),
    )
    db.add(tok)
    await db.flush()
    return tok


async def consume_token(db: AsyncSession, token: str) -> Document:
    now = datetime.now(UTC)
    row = (
        await db.execute(
            select(DocumentDownloadToken).where(
                DocumentDownloadToken.token == token,
                DocumentDownloadToken.expires_at > now,
                DocumentDownloadToken.used_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(403, "download.invalid_token")
    _ = await db.execute(
        update(DocumentDownloadToken)
        .where(DocumentDownloadToken.token == token)
        .values(used_at=now)
    )
    doc = await db.get(Document, row.document_id)
    if doc is None:
        raise HTTPException(404, "document.not_found")
    return doc
