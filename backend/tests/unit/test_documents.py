# pyright: reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnusedCallResult=false, reportPrivateUsage=false, reportPrivateLocalImportUsage=false, reportUnusedFunction=false
import hashlib
from datetime import UTC, datetime, timedelta
from io import BytesIO
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi import HTTPException, UploadFile
from sqlalchemy import select

from app.models import Document, DocumentDownloadToken, SystemParameter, User
from app.services import documents as svc


@pytest.fixture(autouse=True)
def _clear_system_param_cache():
    svc.system_params.invalidate()
    yield
    svc.system_params.invalidate()


async def _user(db, username: str = "alice") -> User:
    return (await db.execute(select(User).where(User.username == username))).scalar_one()


async def _create_document(db, *, actor: User, deleted: bool = False) -> Document:
    document = Document(
        storage_key=f"docs/{uuid4().hex}.pdf",
        storage_backend="local",
        original_filename="invoice.pdf",
        content_type="application/pdf",
        file_size=12,
        content_hash=uuid4().hex * 2,
        doc_category="invoice",
        uploaded_by_id=actor.id,
        deleted_at=datetime.now(UTC) if deleted else None,
    )
    db.add(document)
    await db.flush()
    return document


async def _set_param_value(db, key: str, value: int) -> None:
    param = (
        await db.execute(select(SystemParameter).where(SystemParameter.key == key))
    ).scalar_one()
    param.value = value
    await db.flush()
    svc.system_params.invalidate(key)


@pytest.mark.parametrize(
    ("original_filename", "expected_suffix"),
    [("Invoice.PDF", ".pdf"), ("no-extension", ".bin")],
)
def test_storage_key_uses_hash_prefix_and_expected_suffix(original_filename, expected_suffix):
    content_hash = "ab" * 32

    key = svc._storage_key(content_hash, original_filename)

    assert key.startswith("ab/")
    assert key.endswith(expected_suffix)


def test_document_path_uses_uploads_dir():
    document = Document(
        storage_key="aa/test.pdf",
        storage_backend="local",
        original_filename="test.pdf",
        content_type="application/pdf",
        file_size=1,
        content_hash="cd" * 32,
        doc_category="invoice",
        uploaded_by_id=uuid4(),
    )

    path = svc.document_path(document)

    assert path == Path(svc.settings.media_root) / "uploads" / document.storage_key


async def test_stream_read_and_hash_returns_digest_size_and_content(seeded_db_session):
    payload = b"invoice-bytes"
    file = UploadFile(filename="invoice.pdf", file=BytesIO(payload))

    content_hash, file_size, content = await svc._stream_read_and_hash(seeded_db_session, file)

    assert content_hash == hashlib.sha256(payload).hexdigest()
    assert file_size == len(payload)
    assert content == payload


async def test_stream_read_and_hash_raises_for_large_file(seeded_db_session):
    await _set_param_value(seeded_db_session, "upload.chunk_size_bytes", 4)
    await _set_param_value(seeded_db_session, "upload.max_file_size_bytes", 5)
    file = UploadFile(filename="too-large.pdf", file=BytesIO(b"123456"))

    with pytest.raises(HTTPException) as exc:
        await svc._stream_read_and_hash(seeded_db_session, file)

    assert exc.value.status_code == 413
    assert exc.value.detail == "file.too_large"


async def test_create_download_token_persists_token_and_respects_custom_ttl(seeded_db_session):
    actor = await _user(seeded_db_session)
    document = await _create_document(seeded_db_session, actor=actor)
    before = datetime.now(UTC)

    token = await svc.create_download_token(
        seeded_db_session,
        document.id,
        actor,
        ttl_seconds=90,
    )
    stored = await seeded_db_session.get(DocumentDownloadToken, token.token)
    after = datetime.now(UTC)

    assert stored is not None
    assert token.document_id == document.id
    assert token.created_by_id == actor.id
    assert before + timedelta(seconds=89) <= token.expires_at <= after + timedelta(seconds=91)


@pytest.mark.parametrize("deleted", [False, True])
async def test_create_download_token_rejects_missing_or_deleted_document(
    seeded_db_session, deleted
):
    actor = await _user(seeded_db_session)
    document_id = uuid4()
    if deleted:
        document_id = (await _create_document(seeded_db_session, actor=actor, deleted=True)).id

    with pytest.raises(HTTPException) as exc:
        await svc.create_download_token(seeded_db_session, document_id, actor)

    assert exc.value.status_code == 404
    assert exc.value.detail == "document.not_found"


async def test_consume_token_returns_document_and_marks_token_used(seeded_db_session):
    actor = await _user(seeded_db_session)
    document = await _create_document(seeded_db_session, actor=actor)
    token = await svc.create_download_token(seeded_db_session, document.id, actor)

    resolved = await svc.consume_token(seeded_db_session, token.token)
    stored = await seeded_db_session.get(DocumentDownloadToken, token.token)

    assert resolved.id == document.id
    assert stored is not None
    assert stored.used_at is not None


async def test_consume_token_rejects_reused_token(seeded_db_session):
    actor = await _user(seeded_db_session)
    document = await _create_document(seeded_db_session, actor=actor)
    token = await svc.create_download_token(seeded_db_session, document.id, actor)
    await svc.consume_token(seeded_db_session, token.token)

    with pytest.raises(HTTPException) as exc:
        await svc.consume_token(seeded_db_session, token.token)

    assert exc.value.status_code == 403
    assert exc.value.detail == "download.invalid_token"


async def test_consume_token_rejects_expired_token(seeded_db_session):
    actor = await _user(seeded_db_session)
    document = await _create_document(seeded_db_session, actor=actor)
    token = await svc.create_download_token(
        seeded_db_session,
        document.id,
        actor,
        ttl_seconds=-1,
    )

    with pytest.raises(HTTPException) as exc:
        await svc.consume_token(seeded_db_session, token.token)

    assert exc.value.status_code == 403
    assert exc.value.detail == "download.invalid_token"


async def test_consume_token_rejects_unknown_token(seeded_db_session):
    with pytest.raises(HTTPException) as exc:
        await svc.consume_token(seeded_db_session, "missing-token")

    assert exc.value.status_code == 403
    assert exc.value.detail == "download.invalid_token"
