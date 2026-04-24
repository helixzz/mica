"""create document_templates table and seed finance_payment_form

Revision ID: 0024
Revises: 0023
Create Date: 2026-04-25
"""

from uuid import uuid4

import sqlalchemy as sa
from alembic import op

revision = "0024"
down_revision = "0023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "document_templates",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            primary_key=True,
        ),
        sa.Column("code", sa.String(length=64), nullable=False, unique=True),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "template_document_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("documents.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("filename_template", sa.Text(), nullable=False),
        sa.Column(
            "is_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.execute(
        sa.text(
            """
            INSERT INTO document_templates
                (id, code, name, description, template_document_id,
                 filename_template, is_enabled, created_at, updated_at)
            VALUES
                (:id, 'finance_payment_form', '财务付款表',
                 '财务部门对外付款时使用的申请表。占位符用 [] 标注，内部描述将由 AI 根据 PO / 合同 / 付款计划填写。',
                 NULL,
                 '财务付款表_[PO编号]_[付款期次]_[付款日期YYYYMMDD]',
                 true, now(), now())
            ON CONFLICT (code) DO NOTHING;
            """
        ).bindparams(id=uuid4())
    )


def downgrade() -> None:
    op.drop_table("document_templates")
