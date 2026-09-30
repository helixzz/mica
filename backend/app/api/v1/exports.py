"""Generic dataset export endpoints.

``GET /exports`` describes what the caller may export (this drives the
frontend UI), ``GET /exports/{key}`` renders one dataset. Both are thin: all
scoping, gating, row caps and file generation live in
``app/services/export_registry.py``.
"""

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser
from app.db import get_db
from app.services import export_datasets  # noqa: F401  (import registers datasets)
from app.services.export_registry import ExportFilters, catalog, run_export
from app.services.system_params import system_params

router = APIRouter()


@router.get("/exports", tags=["exports"])
async def list_export_datasets(user: CurrentUser):
    """Datasets the caller's role may export, with their filters and columns."""
    return {"datasets": catalog(user.role)}


@router.get("/exports/{dataset_key}", tags=["exports"])
async def export_dataset(
    dataset_key: str,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    export_format: Annotated[str, Query(alias="format", pattern="^(xlsx|csv)$")] = "xlsx",
    date_from: date | None = None,
    date_to: date | None = None,
    export_status: Annotated[list[str] | None, Query(alias="status")] = None,
    supplier_id: UUID | None = None,
    company_id: UUID | None = None,
    department_id: UUID | None = None,
    cost_center_id: UUID | None = None,
    category_id: UUID | None = None,
    item_id: UUID | None = None,
    q: str | None = None,
):
    """Render one export dataset as XLSX (all sheets) or CSV (first sheet)."""
    if date_from is not None and date_to is not None and date_from > date_to:
        raise HTTPException(400, "export.invalid_date_range")

    max_rows = await system_params.get_int_or(db, "export.max_rows", 5000)
    filters = ExportFilters(
        date_from=date_from,
        date_to=date_to,
        statuses=tuple(export_status or ()),
        supplier_id=supplier_id,
        company_id=company_id,
        department_id=department_id,
        cost_center_id=cost_center_id,
        category_id=category_id,
        item_id=item_id,
        keyword=q,
    )
    payload, filename = await run_export(
        db,
        dataset_key=dataset_key,
        actor=user,
        filters=filters,
        export_format=export_format,
        max_rows=max_rows,
    )

    media_type = (
        "text/csv; charset=utf-8"
        if export_format == "csv"
        else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    return Response(
        content=payload,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(payload)),
        },
    )
