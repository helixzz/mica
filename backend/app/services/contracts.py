"""Contract attachments with OCR text extraction for full-text search.

Reuses documents module for physical storage; contract_documents is a M:N link
that also carries the OCR-extracted plain text for later search.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import Text, desc, func, literal_column, or_, select
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog, Contract, ContractDocument, ContractVersion, Document, User
from app.services import documents as doc_svc
from app.services import invoice_extract as extract_svc
from app.services.system_params import system_params


async def attach_document_to_contract(
    db: AsyncSession,
    actor: User,
    contract_id: UUID,
    document_id: UUID,
    role: str = "scan",
    run_ocr: bool = True,
) -> ContractDocument:
    contract = await db.get(Contract, contract_id)
    if contract is None:
        raise HTTPException(404, "contract.not_found")
    document = await db.get(Document, document_id)
    if document is None:
        raise HTTPException(404, "document.not_found")

    existing = (
        await db.execute(
            select(ContractDocument).where(
                ContractDocument.contract_id == contract_id,
                ContractDocument.document_id == document_id,
            )
        )
    ).scalar_one_or_none()
    if existing:
        return existing

    ocr_text: str | None = None
    if run_ocr:
        try:
            content = await doc_svc.read_document_bytes(document)
            extracted = await extract_svc.extract_invoice(
                db, actor, content, document.content_type, document.original_filename
            )
            parts: list[str] = []
            for field_name in (
                "invoice_number",
                "invoice_date",
                "seller_name",
                "seller_tax_id",
                "buyer_name",
                "buyer_tax_id",
                "subtotal",
                "tax_amount",
                "total_amount",
            ):
                val = getattr(extracted, field_name, None)
                if val:
                    parts.append(str(val))
            for line in extracted.lines or []:
                if line.item_name:
                    parts.append(line.item_name)
                if line.spec:
                    parts.append(line.spec)
            ocr_text = "\n".join(parts) if parts else None
        except Exception:
            ocr_text = None

    link = ContractDocument(
        contract_id=contract_id,
        document_id=document_id,
        role=role,
        ocr_text=ocr_text,
        display_order=0,
    )
    db.add(link)
    db.add(
        AuditLog(
            actor_id=actor.id,
            actor_name=actor.display_name,
            event_type="contract.document_attached",
            resource_type="contract",
            resource_id=str(contract_id),
            metadata_json={"document_id": str(document_id), "ocr_chars": len(ocr_text or "")},
        )
    )
    await db.commit()
    return link


async def list_contract_documents(
    db: AsyncSession, contract_id: UUID
) -> list[tuple[ContractDocument, Document]]:
    rows = (
        await db.execute(
            select(ContractDocument, Document)
            .join(Document, Document.id == ContractDocument.document_id)
            .where(ContractDocument.contract_id == contract_id)
            .order_by(ContractDocument.display_order, ContractDocument.created_at)
        )
    ).all()
    return [(cd, d) for cd, d in rows]


async def search_contracts(
    db: AsyncSession, query: str, limit: int = 50
) -> list[dict[str, object]]:
    if not query.strip():
        return []
    normalized_query = query.strip()
    pattern = f"%{normalized_query}%"
    contract_search_text = literal_column("contracts.search_text", type_=Text())
    contract_search_vector = literal_column("contracts.search_vector", type_=postgresql.TSVECTOR())
    document_search_text = literal_column("contract_documents.search_text", type_=Text())
    document_search_vector = literal_column(
        "contract_documents.search_vector", type_=postgresql.TSVECTOR()
    )
    tsquery = func.websearch_to_tsquery("simple", normalized_query)
    contract_score = func.greatest(
        func.ts_rank_cd(contract_search_vector, tsquery),
        func.similarity(contract_search_text, normalized_query),
    )
    document_score = func.greatest(
        func.ts_rank_cd(document_search_vector, tsquery),
        func.similarity(document_search_text, normalized_query),
    )
    rows = (
        await db.execute(
            select(
                Contract,
                ContractDocument,
                contract_score.label("contract_score"),
                document_score.label("document_score"),
            )
            .outerjoin(ContractDocument, ContractDocument.contract_id == Contract.id)
            .where(
                or_(
                    contract_search_vector.op("@@")(tsquery),
                    contract_search_text.ilike(pattern),
                    document_search_vector.op("@@")(tsquery),
                    document_search_text.ilike(pattern),
                )
            )
            .order_by(
                desc(func.greatest(contract_score, document_score)),
                Contract.created_at.desc(),
            )
            .limit(limit)
        )
    ).all()
    results: dict[UUID, dict[str, object]] = {}
    lowered_query = normalized_query.lower()
    typed_rows = cast(
        list[tuple[Contract, ContractDocument | None, float | None, float | None]], rows
    )
    for contract, doc_link, contract_rank, document_rank in typed_rows:
        entry = results.setdefault(
            contract.id,
            {
                "id": str(contract.id),
                "contract_number": contract.contract_number,
                "title": contract.title,
                "status": contract.status,
                "total_amount": str(contract.total_amount),
                "expiry_date": contract.expiry_date.isoformat() if contract.expiry_date else None,
                "matched_in": [],
                "_score": 0.0,
            },
        )
        matched_in = cast(list[str], entry["matched_in"])
        entry["_score"] = max(
            cast(float, entry["_score"]), float(contract_rank or 0), float(document_rank or 0)
        )
        if lowered_query in (contract.title or "").lower():
            matched_in.append("title")
        if lowered_query in (contract.contract_number or "").lower():
            matched_in.append("contract_number")
        if doc_link and doc_link.ocr_text and lowered_query in doc_link.ocr_text.lower():
            snippet_start = max(0, doc_link.ocr_text.lower().find(lowered_query) - 30)
            snippet = doc_link.ocr_text[snippet_start : snippet_start + 200]
            matched_in.append(f"ocr:…{snippet}…")
    return sorted(
        results.values(), key=lambda item: cast(float, item.get("_score", 0.0)), reverse=True
    )


async def expiring_contracts(db: AsyncSession, within_days: int | None = None) -> list[Contract]:
    resolved_within_days = (
        within_days
        if within_days is not None
        else await system_params.get_int(db, "contract.expiry_reminder_days")
    )
    today = datetime.now(UTC).date()
    cutoff = today + timedelta(days=resolved_within_days)
    rows = (
        (
            await db.execute(
                select(Contract)
                .where(
                    Contract.status == "active",
                    Contract.expiry_date.isnot(None),
                    Contract.expiry_date >= today,
                    Contract.expiry_date <= cutoff,
                )
                .order_by(Contract.expiry_date)
            )
        )
        .scalars()
        .all()
    )
    return list(rows)


def to_dict(cd: ContractDocument, d: Document) -> dict[str, object]:
    return {
        "document_id": str(cd.document_id),
        "role": cd.role,
        "display_order": cd.display_order,
        "has_ocr": bool(cd.ocr_text),
        "ocr_chars": len(cd.ocr_text or ""),
        "original_filename": d.original_filename,
        "content_type": d.content_type,
        "file_size": d.file_size,
    }


def contract_snapshot(contract: Contract) -> dict[str, object]:
    return {
        "contract_number": contract.contract_number,
        "po_id": str(contract.po_id),
        "supplier_id": str(contract.supplier_id),
        "title": contract.title,
        "current_version": contract.current_version,
        "status": contract.status,
        "currency": contract.currency,
        "total_amount": str(contract.total_amount),
        "signed_date": contract.signed_date.isoformat() if contract.signed_date else None,
        "effective_date": contract.effective_date.isoformat() if contract.effective_date else None,
        "expiry_date": contract.expiry_date.isoformat() if contract.expiry_date else None,
        "notes": contract.notes,
    }


async def create_contract_version(
    db: AsyncSession,
    *,
    contract: Contract,
    actor: User,
    change_type: str,
    change_reason: str | None = None,
) -> ContractVersion:
    version = ContractVersion(
        contract_id=contract.id,
        version_number=contract.current_version,
        change_type=change_type,
        change_reason=change_reason,
        snapshot_json=contract_snapshot(contract),
        changed_by_id=actor.id,
    )
    db.add(version)
    await db.flush()
    return version


async def list_contract_versions(db: AsyncSession, contract_id: UUID) -> list[ContractVersion]:
    rows = (
        await db.execute(
            select(ContractVersion)
            .where(ContractVersion.contract_id == contract_id)
            .order_by(desc(ContractVersion.version_number), desc(ContractVersion.created_at))
        )
    ).scalars().all()
    return list(rows)
