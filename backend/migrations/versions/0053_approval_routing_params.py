"""seed approval routing parameters and preferred_first_approver_id column

Revision ID: 0053
Revises: 0052
Create Date: 2026-06-22

v1.36.0 — supports submitter approver hint + dept-tree fallback:
- add purchase_requisitions.preferred_first_approver_id (FK users, ON DELETE SET NULL)
- approval.allow_submitter_preferred_approver: whether requester can hint a
  preferred first-stage approver in PRCreateIn (default true; admin can
  disable globally to enforce strict rule-only routing)
- approval.dept_manager_chain_lookup: whether dept_manager resolution
  walks up Department.parent_id when sub-team has no manager
  (default true; reduces admin fallback noise in multi-team orgs)
"""

import sqlalchemy as sa
from alembic import op

revision = "0053"
down_revision = "0052"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "purchase_requisitions",
        sa.Column(
            "preferred_first_approver_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )

    op.execute(
        sa.text(
            "INSERT INTO system_parameters"
            " (id, key, category, value, data_type, default_value,"
            "  min_value, max_value, unit, description_zh, description_en,"
            "  is_sensitive, created_at, updated_at)"
            " VALUES (gen_random_uuid(), 'approval.allow_submitter_preferred_approver',"
            "  'approval', 'true'::jsonb, 'boolean', 'true'::jsonb,"
            "  NULL, NULL, NULL,"
            "  '是否允许申请人在提交 PR 时指定第一阶审批人偏好。指定的人必须在规则解析的候选集内，否则提交被拒绝',"
            "  'Whether the requester may hint a preferred first-stage approver when submitting a PR. The hinted user must be in the rule-resolved candidate set, otherwise the submission is rejected',"
            "  false, now(), now())"
            " ON CONFLICT (key) DO NOTHING"
        )
    )
    op.execute(
        sa.text(
            "INSERT INTO system_parameters"
            " (id, key, category, value, data_type, default_value,"
            "  min_value, max_value, unit, description_zh, description_en,"
            "  is_sensitive, created_at, updated_at)"
            " VALUES (gen_random_uuid(), 'approval.dept_manager_chain_lookup',"
            "  'approval', 'true'::jsonb, 'boolean', 'true'::jsonb,"
            "  NULL, NULL, NULL,"
            "  '部门负责人解析时是否沿部门树往上追溯（小团队无负责人时，找上级部门负责人）。关闭则直接落到全公司管理员兜底',"
            "  'Whether dept_manager resolution walks up the department tree (when a sub-team has no manager, look at parent department). When disabled, fall through directly to the global admin fallback',"
            "  false, now(), now())"
            " ON CONFLICT (key) DO NOTHING"
        )
    )


def downgrade() -> None:
    op.execute(
        "DELETE FROM system_parameters WHERE key = 'approval.allow_submitter_preferred_approver'"
    )
    op.execute(
        "DELETE FROM system_parameters WHERE key = 'approval.dept_manager_chain_lookup'"
    )
    op.drop_column("purchase_requisitions", "preferred_first_approver_id")
