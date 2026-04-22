"""add requester role and nullable pr item price

Revision ID: 0011
Revises: 0010
Create Date: 2026-04-22
"""

from alembic import op
import sqlalchemy as sa

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(sa.text(
        "ALTER TABLE users DROP CONSTRAINT IF EXISTS ck_users_ck_users_valid_role"
    ))
    op.execute(sa.text("""
        ALTER TABLE users ADD CONSTRAINT ck_users_ck_users_valid_role
        CHECK (role IN ('admin','requester','it_buyer','dept_manager','finance_auditor','procurement_mgr'))
    """))

    op.alter_column("pr_items", "unit_price", nullable=True)
    op.alter_column("pr_items", "amount", nullable=True)

    op.execute(sa.text("""
        INSERT INTO users (id, username, email, display_name, password_hash, role,
                          company_id, department_id, preferred_locale, is_active,
                          created_at, updated_at)
        SELECT gen_random_uuid(), 'eve', 'eve@mica.local', 'Eve (需求方)',
               u.password_hash, 'requester',
               u.company_id, u.department_id, 'zh-CN', true, now(), now()
        FROM users u WHERE u.username = 'alice' LIMIT 1
        ON CONFLICT (username) DO NOTHING
    """))


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM users WHERE username = 'eve'"))
    op.execute(sa.text(
        "ALTER TABLE users DROP CONSTRAINT IF EXISTS ck_users_ck_users_valid_role"
    ))
    op.execute(sa.text("""
        ALTER TABLE users ADD CONSTRAINT ck_users_ck_users_valid_role
        CHECK (role IN ('admin','it_buyer','dept_manager','finance_auditor','procurement_mgr'))
    """))
    op.alter_column("pr_items", "unit_price", nullable=False)
    op.alter_column("pr_items", "amount", nullable=False)
