from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import Literal, cast
from uuid import UUID

from sqlalchemy import Text, desc, func, literal_column, or_, select
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.authz import check_permission
from app.core.cerbos_client import filter_dict_via_cerbos
from app.models import (
    Contract,
    ContractDocument,
    Document,
    Invoice,
    Item,
    PurchaseOrder,
    PurchaseRequisition,
    Supplier,
    User,
    UserRole,
)

EntityType = Literal["pr", "po", "contract", "contract_doc", "invoice", "supplier", "item"]
TSVECTOR_TYPE = postgresql.TSVECTOR()
SearchMeta = dict[str, object]
SearchHit = dict[str, object]
VALID_ENTITY_TYPES: tuple[EntityType, ...] = (
    "pr",
    "po",
    "contract",
    "contract_doc",
    "invoice",
    "supplier",
    "item",
)


def _search_columns(table_name: str):
    return (
        literal_column(f"{table_name}.search_text", type_=Text()),
        literal_column(f"{table_name}.search_vector", type_=TSVECTOR_TYPE),
    )


def _search_terms(table_name: str, query: str):
    search_text, search_vector = _search_columns(table_name)
    tsquery = func.websearch_to_tsquery("simple", query)
    score = func.greatest(
        func.ts_rank_cd(search_vector, tsquery),
        func.similarity(search_text, query),
    )
    snippet = func.ts_headline(
        "simple",
        search_text,
        tsquery,
        "MaxWords=30, MinWords=10, StartSel=<mark>, StopSel=</mark>",
    )
    condition = or_(search_vector.op("@@")(tsquery), search_text.ilike(f"%{query}%"))
    return score, snippet, condition


def _trim_snippet(text: str | None, query: str) -> str | None:
    if not text:
        return None
    lowered = text.lower()
    needle = query.lower()
    position = lowered.find(needle)
    if position < 0:
        return text[:180] or None
    start = max(position - 40, 0)
    end = min(position + len(query) + 140, len(text))
    return text[start:end]


def _as_str(value: Decimal | UUID | None) -> str | None:
    if value is None:
        return None
    return str(value)


def _can_view_pr(actor: User, pr: PurchaseRequisition) -> bool:
    if actor.role in {
        UserRole.ADMIN.value,
        UserRole.PROCUREMENT_MGR.value,
        UserRole.FINANCE_AUDITOR.value,
    }:
        return True
    if actor.role == UserRole.IT_BUYER.value:
        return pr.requester_id == actor.id
    if actor.role == UserRole.DEPT_MANAGER.value:
        if pr.requester_id == actor.id:
            return True
        return bool(actor.department_id and pr.department_id == actor.department_id)
    return False


async def _filter_meta(actor: User, resource: str, meta: SearchMeta) -> SearchMeta:
    return cast(
        SearchMeta,
        await filter_dict_via_cerbos(
            meta,
            principal_id=str(actor.id),
            principal_role=actor.role,
            resource_kind=resource,
            resource_id="search-meta",
        ),
    )


async def _search_prs(db: AsyncSession, actor: User, query: str, limit: int) -> list[SearchHit]:
    if not check_permission(actor, "purchase_requisition", "list"):
        return []
    score, snippet, condition = _search_terms("purchase_requisitions", query)
    rows = (
        await db.execute(
            select(PurchaseRequisition, score.label("score"), snippet.label("snippet"))
            .where(condition)
            .order_by(desc("score"), PurchaseRequisition.created_at.desc())
            .limit(max(limit * 4, 20))
        )
    ).all()

    typed_rows = cast(list[tuple[PurchaseRequisition, float | None, str | None]], rows)
    hits: list[SearchHit] = []
    for pr, rank_score, headline in typed_rows:
        if not _can_view_pr(actor, pr):
            continue
        hits.append(
            {
                "entity_type": "pr",
                "entity_id": str(pr.id),
                "title": pr.title,
                "snippet": _trim_snippet(headline or pr.business_reason or pr.title, query),
                "score": float(rank_score or 0),
                "link_url": f"/purchase-requisitions/{pr.id}",
                "meta": await _filter_meta(
                    actor,
                    "purchase_requisition",
                    {
                        "pr_number": pr.pr_number,
                        "status": pr.status,
                        "total_amount": _as_str(pr.total_amount),
                        "required_date": pr.required_date.isoformat() if pr.required_date else None,
                    },
                ),
            }
        )
        if len(hits) >= limit:
            break
    return hits


async def _search_pos(db: AsyncSession, actor: User, query: str, limit: int) -> list[SearchHit]:
    if not check_permission(actor, "purchase_order", "list"):
        return []
    score, snippet, condition = _search_terms("purchase_orders", query)
    rows = (
        await db.execute(
            select(PurchaseOrder, score.label("score"), snippet.label("snippet"))
            .where(condition)
            .order_by(desc("score"), PurchaseOrder.created_at.desc())
            .limit(limit)
        )
    ).all()
    typed_rows = cast(list[tuple[PurchaseOrder, float | None, str | None]], rows)
    return [
        {
            "entity_type": "po",
            "entity_id": str(po.id),
            "title": po.po_number,
            "snippet": _trim_snippet(headline or po.source_ref or po.po_number, query),
            "score": float(rank_score or 0),
            "link_url": f"/purchase-orders/{po.id}",
            "meta": await _filter_meta(
                actor,
                "purchase_order",
                {
                    "po_number": po.po_number,
                    "status": po.status,
                    "total_amount": _as_str(po.total_amount),
                    "amount_paid": _as_str(po.amount_paid),
                },
            ),
        }
        for po, rank_score, headline in typed_rows
    ]


async def _search_contracts(db: AsyncSession, query: str, limit: int) -> list[SearchHit]:
    score, snippet, condition = _search_terms("contracts", query)
    rows = (
        await db.execute(
            select(Contract, score.label("score"), snippet.label("snippet"))
            .where(condition)
            .order_by(desc("score"), Contract.created_at.desc())
            .limit(limit)
        )
    ).all()
    typed_rows = cast(list[tuple[Contract, float | None, str | None]], rows)
    return [
        {
            "entity_type": "contract",
            "entity_id": str(contract.id),
            "title": contract.title,
            "snippet": _trim_snippet(headline or contract.notes or contract.title, query),
            "score": float(rank_score or 0),
            "link_url": f"/contracts/{contract.id}",
            "meta": {
                "contract_number": contract.contract_number,
                "status": contract.status,
                "total_amount": _as_str(contract.total_amount),
                "expiry_date": contract.expiry_date.isoformat() if contract.expiry_date else None,
            },
        }
        for contract, rank_score, headline in typed_rows
    ]


async def _search_contract_documents(db: AsyncSession, query: str, limit: int) -> list[SearchHit]:
    score, snippet, condition = _search_terms("contract_documents", query)
    rows = (
        await db.execute(
            select(
                ContractDocument,
                Contract,
                Document,
                score.label("score"),
                snippet.label("snippet"),
            )
            .join(Contract, Contract.id == ContractDocument.contract_id)
            .join(Document, Document.id == ContractDocument.document_id)
            .where(condition)
            .order_by(desc("score"), ContractDocument.created_at.desc())
            .limit(limit)
        )
    ).all()
    typed_rows = cast(
        list[tuple[ContractDocument, Contract, Document, float | None, str | None]],
        rows,
    )
    return [
        {
            "entity_type": "contract_doc",
            "entity_id": str(link.document_id),
            "title": document.original_filename,
            "snippet": _trim_snippet(headline or link.ocr_text, query),
            "score": float(rank_score or 0),
            "link_url": f"/contracts/{contract.id}",
            "meta": {
                "contract_id": str(contract.id),
                "contract_number": contract.contract_number,
                "role": link.role,
            },
        }
        for link, contract, document, rank_score, headline in typed_rows
    ]


async def _search_invoices(
    db: AsyncSession, actor: User, query: str, limit: int
) -> list[SearchHit]:
    if not check_permission(actor, "invoice", "list"):
        return []
    score, snippet, condition = _search_terms("invoices", query)
    rows = (
        await db.execute(
            select(Invoice, score.label("score"), snippet.label("snippet"))
            .where(condition)
            .order_by(desc("score"), Invoice.created_at.desc())
            .limit(limit)
        )
    ).all()
    typed_rows = cast(list[tuple[Invoice, float | None, str | None]], rows)
    hits: list[SearchHit] = []
    for invoice, rank_score, headline in typed_rows:
        meta = await _filter_meta(
            actor,
            "invoice",
            {
                "internal_number": invoice.internal_number,
                "invoice_number": invoice.invoice_number,
                "invoice_date": invoice.invoice_date.isoformat(),
                "total_amount": _as_str(invoice.total_amount),
                "status": invoice.status,
            },
        )
        hits.append(
            {
                "entity_type": "invoice",
                "entity_id": str(invoice.id),
                "title": invoice.invoice_number,
                "snippet": _trim_snippet(
                    headline or invoice.notes or invoice.invoice_number, query
                ),
                "score": float(rank_score or 0),
                "link_url": f"/invoices/{invoice.id}",
                "meta": meta,
            }
        )
    return hits


async def _search_suppliers(db: AsyncSession, query: str, limit: int) -> list[SearchHit]:
    score, snippet, condition = _search_terms("suppliers", query)
    rows = (
        await db.execute(
            select(Supplier, score.label("score"), snippet.label("snippet"))
            .where(Supplier.is_deleted.is_(False), Supplier.is_enabled.is_(True))
            .where(condition)
            .order_by(desc("score"), Supplier.name)
            .limit(limit)
        )
    ).all()
    typed_rows = cast(list[tuple[Supplier, float | None, str | None]], rows)
    return [
        {
            "entity_type": "supplier",
            "entity_id": str(supplier.id),
            "title": supplier.name,
            "snippet": _trim_snippet(headline or supplier.contact_name or supplier.name, query),
            "score": float(rank_score or 0),
            "link_url": f"/suppliers/{supplier.id}",
            "meta": {
                "code": supplier.code,
                "contact_name": supplier.contact_name,
                "contact_phone": supplier.contact_phone,
            },
        }
        for supplier, rank_score, headline in typed_rows
    ]


async def _search_items(db: AsyncSession, query: str, limit: int) -> list[SearchHit]:
    score, snippet, condition = _search_terms("items", query)
    rows = (
        await db.execute(
            select(Item, score.label("score"), snippet.label("snippet"))
            .where(Item.is_deleted.is_(False), Item.is_enabled.is_(True))
            .where(condition)
            .order_by(desc("score"), Item.name)
            .limit(limit)
        )
    ).all()
    typed_rows = cast(list[tuple[Item, float | None, str | None]], rows)
    return [
        {
            "entity_type": "item",
            "entity_id": str(item.id),
            "title": item.name,
            "snippet": _trim_snippet(headline or item.specification or item.name, query),
            "score": float(rank_score or 0),
            "link_url": f"/items/{item.id}",
            "meta": {
                "code": item.code,
                "category": item.category,
                "uom": item.uom,
            },
        }
        for item, rank_score, headline in typed_rows
    ]


async def unified_search(
    session: AsyncSession,
    *,
    actor: User,
    query: str,
    entity_types: list[str] | None = None,
    limit_per_type: int = 5,
    overall_limit: int = 30,
) -> dict[str, object]:
    normalized_query = query.strip()
    if not normalized_query:
        return {"total": 0, "by_type": {}, "top_hits": []}

    requested_types = [
        entity_type
        for entity_type in (entity_types or list(VALID_ENTITY_TYPES))
        if entity_type in VALID_ENTITY_TYPES
    ]
    limit_per_type = max(1, min(limit_per_type, 20))
    overall_limit = max(1, min(overall_limit, 50))

    by_type: dict[str, list[SearchHit]] = {}
    for entity_type in requested_types:
        if entity_type == "pr":
            hits = await _search_prs(session, actor, normalized_query, limit_per_type)
        elif entity_type == "po":
            hits = await _search_pos(session, actor, normalized_query, limit_per_type)
        elif entity_type == "contract":
            hits = await _search_contracts(session, normalized_query, limit_per_type)
        elif entity_type == "contract_doc":
            hits = await _search_contract_documents(session, normalized_query, limit_per_type)
        elif entity_type == "invoice":
            hits = await _search_invoices(session, actor, normalized_query, limit_per_type)
        elif entity_type == "supplier":
            hits = await _search_suppliers(session, normalized_query, limit_per_type)
        else:
            hits = await _search_items(session, normalized_query, limit_per_type)
        by_type[entity_type] = hits

    unsorted_hits: list[SearchHit] = [hit for hits in by_type.values() for hit in hits]
    top_hits = sorted(
        unsorted_hits,
        key=lambda hit: cast(float, hit["score"]),
        reverse=True,
    )[:overall_limit]
    return {
        "total": sum(len(hits) for hits in by_type.values()),
        "by_type": by_type,
        "top_hits": top_hits,
    }


async def suggest_search(
    session: AsyncSession,
    *,
    actor: User,
    query: str,
    limit: int = 10,
) -> dict[str, object]:
    result = await unified_search(
        session,
        actor=actor,
        query=query,
        limit_per_type=max(1, min(limit, 5)),
        overall_limit=limit,
    )
    suggestions: dict[str, list[dict[str, object]]] = defaultdict(list)
    by_type = cast(dict[str, list[SearchHit]], result["by_type"])
    for entity_type, hits in by_type.items():
        suggestions[entity_type] = [
            {"entity_id": hit["entity_id"], "title": hit["title"], "link_url": hit["link_url"]}
            for hit in hits[:limit]
        ]
    return {"total": result["total"], "suggestions": dict(suggestions)}
