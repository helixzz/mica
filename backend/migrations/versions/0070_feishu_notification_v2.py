"""notifications: dedupe keys, a delivery ledger, and a Feishu channel preference

Revision ID: 0070
Revises: 0069
Create Date: 2026-10-23

Three gaps made the Feishu cards noisy and hard to trust:

* Every event notification was fan-out to every admin and manager, and saving the
  same PR twice created the same card twice — nothing recorded what had already
  been announced. ``dedupe_key`` lets the sender collapse identical events in a
  short window while still allowing a genuinely different edit through.
* Delivery state was invisible. A card that failed, or that two processes sharing
  one Feishu app both sent, left nothing to inspect afterwards.
  ``notification_deliveries`` is that ledger (and holds the Feishu ``message_id``,
  which a later release can PATCH in place instead of sending a new card).
* The admin's per-event Feishu switches were stored but never read on send, and a
  user could not mute one category on Feishu without muting it in-app too. The
  global switches are now read, and ``notification_subscriptions.feishu_enabled``
  gives each user their own Feishu switch per category.

Nothing here rewrites business data.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0070"
down_revision = "0069"
branch_labels = None
depends_on = None

_PARAMETER_TEMPLATE = """
INSERT INTO system_parameters (
    id, key, category, value, data_type, default_value, min_value, max_value,
    unit, description_zh, description_en, is_sensitive, updated_by_id,
    created_at, updated_at
) VALUES (
    gen_random_uuid(), '{key}', '{category}',
    {value}, '{data_type}', {default_value}, {min_value}, {max_value}, NULL,
    '{description_zh}', '{description_en}', false, NULL, now(), now()
)
"""

_PARAMETERS: list[dict[str, str]] = [
    {
        "key": "auth.feishu.notify_on_system",
        "category": "feishu",
        "value": "to_jsonb(true)",
        "data_type": "bool",
        "default_value": "to_jsonb(true)",
        "min_value": "NULL",
        "max_value": "NULL",
        "description_zh": "飞书推送通用事件（PR/合同/发货变更等），默认开启",
        "description_en": "Push generic events (PR/contract/shipment changes) to Feishu",
    },
    {
        "key": "notifications.broadcast_admin_events",
        "category": "feishu",
        "value": "to_jsonb(false)",
        "data_type": "bool",
        "default_value": "to_jsonb(false)",
        "min_value": "NULL",
        "max_value": "NULL",
        "description_zh": "PR/合同变更是否广播给全部管理员（关闭后只通知相关人）",
        "description_en": "Broadcast PR/contract changes to every admin instead of only the people involved",
    },
    {
        "key": "notifications.event_dedupe_hours",
        "category": "feishu",
        "value": "to_jsonb(24)",
        "data_type": "int",
        "default_value": "to_jsonb(24)",
        "min_value": "1",
        "max_value": "168",
        "description_zh": "同一事件（同对象、同内容指纹）去重窗口（小时）",
        "description_en": "Dedupe window in hours for an identical event on the same object",
    },
    {
        "key": "notifications.delivery_max_attempts",
        "category": "feishu",
        "value": "to_jsonb(3)",
        "data_type": "int",
        "default_value": "to_jsonb(3)",
        "min_value": "1",
        "max_value": "10",
        "description_zh": "飞书/邮件投递失败后的最大重试次数",
        "description_en": "Maximum delivery retries for Feishu/email after a failure",
    },
    {
        "key": "notifications.digest_top_n",
        "category": "feishu",
        "value": "to_jsonb(3)",
        "data_type": "int",
        "default_value": "to_jsonb(3)",
        "min_value": "1",
        "max_value": "10",
        "description_zh": "每日摘要每类最多列出的明细条数",
        "description_en": "Maximum detail rows per section in the daily digest",
    },
]


def upgrade() -> None:
    op.add_column(
        "notifications",
        sa.Column("dedupe_key", sa.String(160), nullable=True),
    )
    op.create_index(
        "ix_notifications_user_dedupe",
        "notifications",
        ["user_id", "dedupe_key"],
    )

    op.add_column(
        "notification_subscriptions",
        sa.Column(
            "feishu_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )

    op.create_table(
        "notification_deliveries",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "notification_id",
            sa.Uuid(),
            sa.ForeignKey("notifications.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("channel", sa.String(16), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("message_id", sa.String(128), nullable=True),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
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
    op.create_index(
        "ix_notification_deliveries_notification",
        "notification_deliveries",
        ["notification_id"],
    )
    op.create_index(
        "ix_notification_deliveries_retry",
        "notification_deliveries",
        ["status", "next_retry_at"],
    )

    for param in _PARAMETERS:
        rendered = dict(param)
        for field in ("min_value", "max_value"):
            if rendered[field] != "NULL":
                rendered[field] = f"to_jsonb({rendered[field]})"
        op.execute(sa.text(_PARAMETER_TEMPLATE.format(**rendered)))


def downgrade() -> None:
    for param in _PARAMETERS:
        op.execute(
            sa.text("DELETE FROM system_parameters WHERE key = :key").bindparams(
                key=param["key"]
            )
        )

    op.drop_index("ix_notification_deliveries_retry", table_name="notification_deliveries")
    op.drop_index(
        "ix_notification_deliveries_notification", table_name="notification_deliveries"
    )
    op.drop_table("notification_deliveries")

    op.drop_column("notification_subscriptions", "feishu_enabled")

    op.drop_index("ix_notifications_user_dedupe", table_name="notifications")
    op.drop_column("notifications", "dedupe_key")
