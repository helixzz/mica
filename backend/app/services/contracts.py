"""Contract attachments with OCR text extraction for full-text search.

Reuses documents module for physical storage; contract_documents is a M:N link
that also carries the OCR-extracted plain text for later search.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog, Contract, ContractDocument, Document, User
from app.services import documents as doc_svc
from app.services import invoice_extract as extract_svc


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
                "invoice_number", "invoice_date", "seller_name", "seller_tax_id",
                "buyer_name", "buyer_tax_id", "subtotal", "tax_amount", "total_amount",
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
) -> list[dict]:
    if not query.strip():
        return []
    pattern = f"%{query}%"
    rows = (
        await db.execute(
            select(Contract, ContractDocument)
            .outerjoin(ContractDocument, ContractDocument.contract_id == Contract.id)
            .where(
                or_(
                    Contract.title.ilike(pattern),
                    Contract.contract_number.ilike(pattern),
                    ContractDocument.ocr_text.ilike(pattern),
                )
            )
            .limit(limit)
        )
    ).all()
    results: dict[UUID, dict] = {}
    for contract, doc_link in rows:
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
            },
        )
        if pattern.strip("%").lower() in (contract.title or "").lower():
            entry["matched_in"].append("title")
        if doc_link and doc_link.ocr_text and pattern.strip("%").lower() in doc_link.ocr_text.lower():
            snippet_start = max(0, doc_link.ocr_text.lower().find(pattern.strip("%").lower()) - 30)
            snippet = doc_link.ocr_text[snippet_start:snippet_start + 200]
            entry["matched_in"].append(f"ocr:…{snippet}…")
    return list(results.values())


async def expiring_contracts(
    db: AsyncSession, within_days: int = 30
) -> list[Contract]:
    today = datetime.now(timezone.utc).date()
    cutoff = today + timedelta(days=within_days)
    rows = (
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
    ).scalars().all()
    return list(rows)


def to_dict(cd: ContractDocument, d: Document) -> dict:
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
