"""approval rules dsl

Revision ID: 0005
Revises: 0004
Create Date: 2026-04-21 21:00:00.000000

"""
from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timezone, UTC
from uuid import uuid4

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    _ = op.create_table(
        "approval_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("biz_type", sa.String(length=64), nullable=False),
        sa.Column("amount_min", sa.Numeric(18, 4), nullable=True),
        sa.Column("amount_max", sa.Numeric(18, 4), nullable=True),
        sa.Column("stages", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_approval_rules_biz_type", "approval_rules", ["biz_type"])
    op.create_index(
        "ix_approval_rules_active_priority",
        "approval_rules",
        ["is_active", "priority"],
    )

    _ = op.create_table(
        "approver_delegations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("from_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("to_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reason", sa.String(length=255), nullable=True),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("from_user_id <> to_user_id", name="ck_approver_delegations_approver_delegations_distinct_users"),
        sa.CheckConstraint("ends_at > starts_at", name="ck_approver_delegations_approver_delegations_valid_window"),
        sa.ForeignKeyConstraint(["from_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["to_user_id"], ["users.id"]),
    )
    op.create_index(
        "ix_approver_delegations_from_user",
        "approver_delegations",
        ["from_user_id"],
    )
    op.create_index(
        "ix_approver_delegations_to_user",
        "approver_delegations",
        ["to_user_id"],
    )

    op.add_column(
        "approval_tasks",
        sa.Column(
            "meta",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )

    approval_rules = sa.table(
        "approval_rules",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("name", sa.String),
        sa.column("biz_type", sa.String),
        sa.column("amount_min", sa.Numeric(18, 4)),
        sa.column("amount_max", sa.Numeric(18, 4)),
        sa.column("stages", postgresql.JSONB(astext_type=sa.Text())),
        sa.column("is_active", sa.Boolean),
        sa.column("priority", sa.Integer),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )

    now = datetime.now(UTC)
    op.bulk_insert(
        approval_rules,
        [
            {
                "id": uuid4(),
                "name": "标准采购审批 (small)",
                "biz_type": "purchase_requisition",
                "amount_min": None,
                "amount_max": 100000,
                "stages": [
                    {
                        "stage_name": "部门审批",
                        "approver_role": "dept_manager",
                        "order": 1,
                    }
                ],
                "is_active": True,
                "priority": 10,
                "created_at": now,
                "updated_at": now,
            },
            {
                "id": uuid4(),
                "name": "大额采购审批 (large)",
                "biz_type": "purchase_requisition",
                "amount_min": 100000,
                "amount_max": None,
                "stages": [
                    {
                        "stage_name": "部门审批",
                        "approver_role": "dept_manager",
                        "order": 1,
                    },
                    {
                        "stage_name": "采购审批",
                        "approver_role": "procurement_mgr",
                        "order": 2,
                    },
                ],
                "is_active": True,
                "priority": 20,
                "created_at": now,
                "updated_at": now,
            },
        ],
    )

    op.alter_column("approval_tasks", "meta", server_default=None)


def downgrade() -> None:
    op.drop_column("approval_tasks", "meta")

    op.drop_index("ix_approver_delegations_to_user", table_name="approver_delegations")
    op.drop_index("ix_approver_delegations_from_user", table_name="approver_delegations")
    op.drop_table("approver_delegations")

    op.drop_index("ix_approval_rules_active_priority", table_name="approval_rules")
    op.drop_index("ix_approval_rules_biz_type", table_name="approval_rules")
    op.drop_table("approval_rules")
