"""add companies.short_name and stop filenames using a sliced 4-character abbreviation

Revision ID: 0058
Revises: 0057
Create Date: 2026-10-13

v1.55.0: generated payment forms were named with an abbreviation that was not
stored anywhere — ``build_context()`` simply took ``name_zh[:4]``. For
"上海佳期私募基金管理有限公司" and "上海佳期数据科技有限公司" that produced the
same token "上海佳期", so two different payers produced indistinguishable files
(and English names degraded to "JQ I" / "Seve"). The abbreviation is now an
explicitly maintained column and its consumer falls back to the full legal name.

This revision:
1. adds ``companies.short_name`` (nullable — no data is invented here), and
2. rewrites the only known legacy filename template that asked for the sliced
   abbreviation, replacing ``[采购公司名的四字简称]`` with ``[付款方公司全名]``.
   The rewrite is a no-op on rows the template owner already fixed, and it writes
   an ``audit_logs`` row so the change is not silent.
"""

from datetime import UTC, datetime
from uuid import uuid4

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0058"
down_revision = "0057"
branch_labels = None
depends_on = None

_LEGACY_ABBREV_TOKEN = "采购公司名的四字简称"
_FULL_NAME_TOKEN = "付款方公司全名"


def upgrade() -> None:
    op.add_column("companies", sa.Column("short_name", sa.String(length=64), nullable=True))

    bind = op.get_bind()
    rows = bind.execute(
        sa.text(
            "SELECT id, filename_template FROM document_templates"
            " WHERE filename_template LIKE :pattern"
        ).bindparams(pattern=f"%{_LEGACY_ABBREV_TOKEN}%")
    ).all()
    if not rows:
        return

    now = datetime.now(UTC)
    audit_logs = sa.table(
        "audit_logs",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("occurred_at", sa.DateTime(timezone=True)),
        sa.column("actor_id", postgresql.UUID(as_uuid=True)),
        sa.column("actor_name", sa.String),
        sa.column("event_type", sa.String),
        sa.column("resource_type", sa.String),
        sa.column("resource_id", sa.String),
        sa.column("metadata_json", postgresql.JSONB(astext_type=sa.Text())),
        sa.column("comment", sa.Text),
    )

    update_stmt = sa.text(
        "UPDATE document_templates SET filename_template = :new_template,"
        " updated_at = :updated_at WHERE id = :template_id"
    ).bindparams(
        # Explicit types: ``text()`` carries no schema information, so asyncpg would
        # otherwise send the UUID as character varying and fail with
        # "operator does not exist: uuid = character varying".
        sa.bindparam("new_template", type_=sa.Text()),
        sa.bindparam("updated_at", type_=sa.DateTime(timezone=True)),
        sa.bindparam("template_id", type_=postgresql.UUID(as_uuid=True)),
    )
    audit_rows = []
    for template_id, filename_template in rows:
        new_template = filename_template.replace(_LEGACY_ABBREV_TOKEN, _FULL_NAME_TOKEN)
        bind.execute(
            update_stmt,
            {
                "new_template": new_template,
                "updated_at": now,
                "template_id": template_id,
            },
        )
        audit_rows.append(
            {
                "id": uuid4(),
                "occurred_at": now,
                "actor_id": None,
                "actor_name": "system:migration-0058",
                "event_type": "document_template.updated",
                "resource_type": "document_template",
                "resource_id": str(template_id),
                "metadata_json": {
                    "changes": {
                        "filename_template": {
                            "from": filename_template,
                            "to": new_template,
                        }
                    },
                    "reason": (
                        "四字简称由 name_zh[:4] 推导，不同付款公司会得到同一简称"
                        "（例如 上海佳期私募基金管理有限公司 / 上海佳期数据科技有限公司），"
                        "导致付款表文件名无法区分；改用公司全称。"
                    ),
                },
                "comment": None,
            }
        )
    op.bulk_insert(audit_logs, audit_rows)


def downgrade() -> None:
    # The template rewrite is intentionally not reverted: restoring an ambiguous
    # filename format is not a safe automatic action.
    op.drop_column("companies", "short_name")
