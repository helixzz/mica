"""Add hybrid search vectors and trigram indexes.

Revision ID: 0004
Revises: 0003
Create Date: 2026-04-21 18:00:00.000000

Pragmatic fallback: the current deploy stack uses postgres:16-alpine, which does
not ship zhparser. Instead of introducing a custom PostgreSQL image in this wave,
we use core pg_trgm plus simple-config tsvector columns. This keeps docker-compose
bootstrapping automatic while still accelerating Chinese substring search.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


SEARCH_SPECS: dict[str, list[str]] = {
    "purchase_requisitions": ["pr_number", "title", "business_reason"],
    "purchase_orders": ["po_number", "source_ref"],
    "contracts": ["contract_number", "title", "notes"],
    "contract_documents": ["ocr_text"],
    "invoices": ["internal_number", "invoice_number", "notes", "tax_number"],
    "suppliers": ["code", "name", "contact_name", "contact_phone", "contact_email", "tax_number"],
    "items": ["code", "name", "specification", "category"],
}


def _computed_text(columns: list[str]) -> str:
    return " || ' ' || ".join(f"coalesce({column}, '')" for column in columns)


def _add_search_columns(table_name: str, columns: list[str]) -> None:
    computed_text = _computed_text(columns)
    op.add_column(
        table_name,
        sa.Column(
            "search_text",
            sa.Text(),
            sa.Computed(computed_text, persisted=True),
            nullable=True,
        ),
    )
    op.add_column(
        table_name,
        sa.Column(
            "search_vector",
            postgresql.TSVECTOR(),
            sa.Computed(f"to_tsvector('simple', {computed_text})", persisted=True),
            nullable=True,
        ),
    )
    op.create_index(
        f"ix_{table_name}_search_vector",
        table_name,
        ["search_vector"],
        unique=False,
        postgresql_using="gin",
    )
    op.create_index(
        f"ix_{table_name}_search_text_trgm",
        table_name,
        ["search_text"],
        unique=False,
        postgresql_using="gin",
        postgresql_ops={"search_text": "gin_trgm_ops"},
    )


def _drop_search_columns(table_name: str) -> None:
    op.drop_index(f"ix_{table_name}_search_text_trgm", table_name=table_name)
    op.drop_index(f"ix_{table_name}_search_vector", table_name=table_name)
    op.drop_column(table_name, "search_vector")
    op.drop_column(table_name, "search_text")


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    for table_name, columns in SEARCH_SPECS.items():
        _add_search_columns(table_name, columns)


def downgrade() -> None:
    for table_name in reversed(list(SEARCH_SPECS.keys())):
        _drop_search_columns(table_name)
    op.execute("DROP EXTENSION IF EXISTS pg_trgm")
