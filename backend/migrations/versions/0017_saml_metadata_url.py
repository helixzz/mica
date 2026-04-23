"""add saml idp metadata_url system parameter

Revision ID: 0017
Revises: 0016
Create Date: 2026-04-23
"""

from datetime import UTC, datetime
from uuid import uuid4

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    system_parameters = sa.table(
        "system_parameters",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("key", sa.String),
        sa.column("category", sa.String),
        sa.column("value", postgresql.JSONB),
        sa.column("data_type", sa.String),
        sa.column("default_value", postgresql.JSONB),
        sa.column("min_value", postgresql.JSONB),
        sa.column("max_value", postgresql.JSONB),
        sa.column("unit", sa.String),
        sa.column("description_zh", sa.String),
        sa.column("description_en", sa.String),
        sa.column("is_sensitive", sa.Boolean),
        sa.column("updated_by_id", postgresql.UUID(as_uuid=True)),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    now = datetime.now(UTC)
    op.bulk_insert(
        system_parameters,
        [
            {
                "id": uuid4(),
                "key": "auth.saml.idp.metadata_url",
                "category": "auth",
                "value": "",
                "data_type": "string",
                "default_value": "",
                "min_value": None,
                "max_value": None,
                "unit": None,
                "description_zh": "ADFS / IdP 联合元数据 URL，填写后系统可自动获取和更新 IdP 签名证书。例如 https://adfs.example.com/FederationMetadata/2007-06/FederationMetadata.xml",
                "description_en": "ADFS / IdP federation metadata URL. When set, the system can auto-fetch and update the IdP signing certificate. e.g. https://adfs.example.com/FederationMetadata/2007-06/FederationMetadata.xml",
                "is_sensitive": False,
                "updated_by_id": None,
                "created_at": now,
                "updated_at": now,
            },
        ],
    )


def downgrade() -> None:
    op.execute("DELETE FROM system_parameters WHERE key = 'auth.saml.idp.metadata_url'")
