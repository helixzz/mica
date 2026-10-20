"""feishu: require the webhook signature

Revision ID: 0068
Revises: 0067
Create Date: 2026-10-20

The webhook used to verify the signature only *if* the three x-lark-* headers were
present, so a caller could skip verification by simply omitting them — and the
endpoint can flip payment state. Requests without the headers are now refused.

A switch is seeded alongside it so an unexpected callback shape can be tolerated
in production without shipping a release: set
``feishu.webhook_require_signature`` to false and the previous behaviour returns.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0068"
down_revision = "0067"
branch_labels = None
depends_on = None

_PARAMETER = """
INSERT INTO system_parameters (
    id, key, category, value, data_type, default_value, min_value, max_value,
    unit, description_zh, description_en, is_sensitive, updated_by_id,
    created_at, updated_at
) VALUES (
    gen_random_uuid(), 'feishu.webhook_require_signature', 'feishu',
    to_jsonb(true), 'bool', to_jsonb(true), NULL, NULL, NULL,
    '飞书回调必须带签名头（关闭后恢复旧行为，仅供救急）',
    'Require the Feishu callback signature; disable only as an escape hatch',
    false, NULL, now(), now()
)
"""


def upgrade() -> None:
    op.execute(sa.text(_PARAMETER))


def downgrade() -> None:
    op.execute(
        sa.text("DELETE FROM system_parameters WHERE key = 'feishu.webhook_require_signature'")
    )
