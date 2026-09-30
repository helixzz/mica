"""Dataset-driven export framework.

A dataset declares, statically:

* which optional filters it understands (this list drives the frontend UI),
* which roles may export it,
* the sheets and columns it produces, and for every column that maps to a
  field-level permission, the ``<cerbos_kind>.<field>`` pair that guards it,
* a loader that returns one list of rows per declared sheet.

Everything else — row scoping, field gating, the row cap, formula-injection
hardening, CSV encoding, sheet styling and the file name — is handled once,
here, so a new dataset cannot forget one of them.

See ``app/services/export_datasets.py`` for the concrete datasets.
"""

from __future__ import annotations

import asyncio
import csv
import logging
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from io import BytesIO, StringIO
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from openpyxl import Workbook
from sqlalchemy import ColumnElement, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.field_authz import FIELD_PERMISSIONS
from app.models import User
from app.services.export_excel import (
    _allowed_fields,
    _csv_safe,
    _neutralize_workbook,
    _write_sheet,
)

logger = logging.getLogger(__name__)

# Filter keys the framework understands. A dataset advertises the subset it
# supports via ``ExportDataset.filters``; requesting anything else is a 400 so
# a user never believes they filtered when they did not.
FILTER_KEYS = frozenset(
    {
        "date_range",
        "status",
        "supplier",
        "company",
        "department",
        "cost_center",
        "category",
        "item",
        "keyword",
    }
)

EXPORT_ROLES = frozenset({"admin", "it_buyer", "procurement_mgr", "finance_auditor"})


@dataclass(frozen=True)
class ExportFilters:
    """The optional filters a caller may supply."""

    date_from: date | None = None
    date_to: date | None = None
    statuses: tuple[str, ...] = ()
    supplier_id: UUID | None = None
    company_id: UUID | None = None
    department_id: UUID | None = None
    cost_center_id: UUID | None = None
    category_id: UUID | None = None
    item_id: UUID | None = None
    keyword: str | None = None

    def requested(self) -> set[str]:
        """Return the filter keys this instance actually populates."""
        found: set[str] = set()
        if self.date_from is not None or self.date_to is not None:
            found.add("date_range")
        if self.statuses:
            found.add("status")
        for key, value in (
            ("supplier", self.supplier_id),
            ("company", self.company_id),
            ("department", self.department_id),
            ("cost_center", self.cost_center_id),
            ("category", self.category_id),
            ("item", self.item_id),
        ):
            if value is not None:
                found.add(key)
        if self.keyword:
            found.add("keyword")
        return found


@dataclass(frozen=True)
class ExportColumn:
    """One column of one sheet.

    ``field`` is ``"<cerbos_kind>.<field_name>"`` when the column must pass a
    field-level permission check; ``None`` means the column is always exported
    for anyone allowed to run the dataset.
    """

    key: str
    header_zh: str
    header_en: str
    get: Callable[[Any], Any]
    field: str | None = None
    width: int = 18

    @property
    def header(self) -> str:
        return f"{self.header_zh} {self.header_en}"


@dataclass(frozen=True)
class ExportSheetSpec:
    title_zh: str
    title_en: str
    columns: Sequence[ExportColumn]
    # 0-based index of a numeric column that gets a 合计 row (label one column
    # to its left, matching the existing payments/ledger exports).
    total_column: int | None = None

    @property
    def title(self) -> str:
        return f"{self.title_zh} {self.title_en}"

    @property
    def headers(self) -> list[str]:
        return [column.header for column in self.columns]


@dataclass(frozen=True)
class ExportRequest:
    actor: User
    filters: ExportFilters
    # cerbos kind -> fields the actor may read for that kind
    allowed: dict[str, set[str]]


# A loader returns one row-list per declared sheet, in declaration order.
ExportLoader = Callable[[AsyncSession, ExportRequest], Awaitable[Sequence[list[list[Any]]]]]


@dataclass(frozen=True)
class ExportDataset:
    key: str
    label_zh: str
    label_en: str
    filters: frozenset[str]
    sheets: Sequence[ExportSheetSpec]
    loader: ExportLoader
    roles: frozenset[str] = EXPORT_ROLES
    # Allowed values for the ``status`` filter. Declared by the dataset so the
    # frontend never has to hardcode them (which had already drifted from the
    # enums once).
    status_values: tuple[str, ...] = ()

    @property
    def label(self) -> str:
        return f"{self.label_zh} {self.label_en}"

    def gated_fields(self) -> dict[str, set[str]]:
        """Map cerbos kind -> field names referenced by this dataset's columns."""
        wanted: dict[str, set[str]] = {}
        for sheet in self.sheets:
            for column in sheet.columns:
                if not column.field:
                    continue
                kind, _, field_name = column.field.partition(".")
                wanted.setdefault(kind, set()).add(field_name)
        return wanted


REGISTRY: dict[str, ExportDataset] = {}


def register(dataset: ExportDataset) -> ExportDataset:
    if dataset.key in REGISTRY:
        raise RuntimeError(f"duplicate export dataset key: {dataset.key}")
    unknown = dataset.filters - FILTER_KEYS
    if unknown:
        raise RuntimeError(f"{dataset.key}: unknown filter keys {sorted(unknown)}")
    if "status" in dataset.filters and not dataset.status_values:
        raise RuntimeError(
            f"{dataset.key}: declares the status filter but no status_values; "
            "the UI would have to guess the allowed values"
        )
    # Guard against the fail-open trap: the Cerbos client degrades to
    # FIELD_PERMISSIONS, which grants every field when the kind is missing.
    for kind in dataset.gated_fields():
        entries = FIELD_PERMISSIONS.get(kind)
        if entries is None:
            raise RuntimeError(
                f"{dataset.key}: cerbos kind '{kind}' has no FIELD_PERMISSIONS entry; "
                "field gating would fail open"
            )
        # ``filter_dict_by_role`` also grants every field when a *role* is
        # missing from the kind, so demand coverage for every role that may
        # export this dataset.
        uncovered = sorted(role for role in dataset.roles if role not in entries)
        if uncovered:
            raise RuntimeError(
                f"{dataset.key}: kind '{kind}' has no FIELD_PERMISSIONS entry for "
                f"role(s) {uncovered}; field gating would fail open for them"
            )
    REGISTRY[dataset.key] = dataset
    return dataset


def get_dataset(key: str) -> ExportDataset:
    dataset = REGISTRY.get(key)
    if dataset is None:
        raise HTTPException(404, "export.dataset_not_found")
    return dataset


def datasets_for(role: str) -> list[ExportDataset]:
    return [ds for ds in REGISTRY.values() if role in ds.roles]


def catalog(role: str) -> list[dict[str, Any]]:
    """Static description of every dataset the role may export."""
    return [
        {
            "key": ds.key,
            "label_zh": ds.label_zh,
            "label_en": ds.label_en,
            "filters": sorted(ds.filters),
            "status_values": list(ds.status_values),
            "sheets": [
                {
                    "title_zh": sheet.title_zh,
                    "title_en": sheet.title_en,
                    "columns": [
                        {"key": col.key, "label_zh": col.header_zh, "label_en": col.header_en}
                        for col in sheet.columns
                    ],
                }
                for sheet in ds.sheets
            ],
        }
        for ds in datasets_for(role)
    ]


# ---------------------------------------------------------------------------
# Shared filter helpers (used by dataset loaders)
# ---------------------------------------------------------------------------


def validate_requested_filters(dataset: ExportDataset, filters: ExportFilters) -> None:
    unsupported = filters.requested() - dataset.filters
    if unsupported:
        raise HTTPException(400, "export.unsupported_filter")


def apply_date_range(
    stmt, column: ColumnElement[Any], filters: ExportFilters, *, use_date: bool = False
):
    """Apply an inclusive day range.

    Uses ``time.max`` for the upper bound so ``date_to=9999-12-31`` cannot
    overflow into an HTTP 500.
    """
    if use_date:
        if filters.date_from is not None:
            stmt = stmt.where(column >= filters.date_from)
        if filters.date_to is not None:
            stmt = stmt.where(column <= filters.date_to)
        return stmt
    if filters.date_from is not None:
        stmt = stmt.where(column >= datetime.combine(filters.date_from, time.min, tzinfo=UTC))
    if filters.date_to is not None:
        stmt = stmt.where(column <= datetime.combine(filters.date_to, time.max, tzinfo=UTC))
    return stmt


def keyword_clause(columns: Sequence[ColumnElement[Any]], keyword: str | None):
    if not keyword:
        return None
    pattern = f"%{keyword.strip()}%"
    return or_(*[column.ilike(pattern) for column in columns])


# ---------------------------------------------------------------------------
# Field-level gating
# ---------------------------------------------------------------------------


async def allowed_fields_for(actor: User, dataset: ExportDataset) -> dict[str, set[str]]:
    """One Cerbos check per resource kind, never per row."""
    wanted = dataset.gated_fields()
    if not wanted:
        return {}
    kinds = list(wanted)
    results = await asyncio.gather(
        *(_allowed_fields(actor, kind, sorted(wanted[kind])) for kind in kinds)
    )
    return dict(zip(kinds, results, strict=True))


def _cell_value(column: ExportColumn, row: Any, allowed: dict[str, set[str]]) -> Any:
    value = column.get(row)
    if not column.field:
        return value
    kind, _, field_name = column.field.partition(".")
    if field_name in allowed.get(kind, set()):
        return value
    return ""


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def _render_xlsx(
    dataset: ExportDataset,
    tables: Sequence[Sequence[list[Any]]],
) -> bytes:
    workbook = Workbook()
    for index, (sheet_spec, rows) in enumerate(zip(dataset.sheets, tables, strict=True)):
        worksheet = workbook.active if index == 0 else workbook.create_sheet()
        worksheet.title = sheet_spec.title
        headers = sheet_spec.headers
        widths = [column.width for column in sheet_spec.columns]
        total_row = None
        if sheet_spec.total_column is not None:
            total_index = sheet_spec.total_column
            total = sum(
                float(row[total_index]) for row in rows if isinstance(row[total_index], int | float)
            )
            total_row = (["合计 Total", total], total_index)
        _write_sheet(
            worksheet, headers, [list(row) for row in rows], widths, total_label_row=total_row
        )
    _neutralize_workbook(workbook)
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def _render_csv(
    dataset: ExportDataset,
    tables: Sequence[Sequence[list[Any]]],
) -> bytes:
    """Render the first sheet as CSV (CSV cannot carry multiple sheets)."""
    sheet_spec = dataset.sheets[0]
    buffer = StringIO(newline="")
    writer = csv.writer(buffer)
    writer.writerow(sheet_spec.headers)
    for row in tables[0]:
        writer.writerow([_csv_safe(cell) for cell in row])
    if sheet_spec.total_column is not None:
        total_index = sheet_spec.total_column
        total = sum(
            float(row[total_index])
            for row in tables[0]
            if isinstance(row[total_index], int | float)
        )
        filler = [""] * len(sheet_spec.columns)
        filler[total_index - 1] = "合计 Total"
        filler[total_index] = total
        writer.writerow(filler)
    return buffer.getvalue().encode("utf-8-sig")


def export_filename(dataset_key: str, export_format: str) -> str:
    stamp = datetime.now(UTC).strftime("%Y%m%d")
    suffix = "csv" if export_format == "csv" else "xlsx"
    return f"mica-{dataset_key}-{stamp}.{suffix}"


async def run_export(
    db: AsyncSession,
    *,
    dataset_key: str,
    actor: User,
    filters: ExportFilters,
    export_format: str,
    max_rows: int,
) -> tuple[bytes, str]:
    # Check the role before the dataset so a caller outside the export roles
    # cannot use the 404/403 difference to enumerate dataset keys.
    if actor.role not in EXPORT_ROLES:
        raise HTTPException(403, "insufficient_role")
    dataset = get_dataset(dataset_key)
    if actor.role not in dataset.roles:
        raise HTTPException(403, "insufficient_role")
    validate_requested_filters(dataset, filters)
    if filters.statuses and dataset.status_values:
        invalid = [s for s in filters.statuses if s not in dataset.status_values]
        if invalid:
            raise HTTPException(400, "export.invalid_status")

    allowed = await allowed_fields_for(actor, dataset)
    raw_tables = await dataset.loader(
        db, ExportRequest(actor=actor, filters=filters, allowed=allowed)
    )
    if len(raw_tables) != len(dataset.sheets):
        raise RuntimeError(
            f"{dataset.key}: loader returned {len(raw_tables)} tables for "
            f"{len(dataset.sheets)} declared sheets"
        )

    tables: list[list[list[Any]]] = []
    for sheet_spec, rows in zip(dataset.sheets, raw_tables, strict=True):
        gated = [
            [_cell_value(column, row, allowed) for column in sheet_spec.columns] for row in rows
        ]
        if len(gated) > max_rows:
            raise HTTPException(400, "export.too_many_rows")
        tables.append(gated)

    payload = (
        _render_csv(dataset, tables) if export_format == "csv" else _render_xlsx(dataset, tables)
    )
    return payload, export_filename(dataset.key, export_format)
