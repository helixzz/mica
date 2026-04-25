"""seed AIFeatureRouting(document_generation) on existing deployments

Revision ID: 0025
Revises: 0024
Create Date: 2026-04-25
"""

import sqlalchemy as sa
from alembic import op

revision = "0025"
down_revision = "0024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            INSERT INTO ai_feature_routing
                (id, feature_code, primary_model_id, temperature, max_tokens, enabled,
                 created_at, updated_at)
            SELECT
                gen_random_uuid(),
                'document_generation',
                (SELECT id FROM ai_models ORDER BY created_at ASC LIMIT 1),
                0.00,
                1200,
                false,
                now(),
                now()
            WHERE NOT EXISTS (
                SELECT 1 FROM ai_feature_routing WHERE feature_code = 'document_generation'
            );
            """
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "DELETE FROM ai_feature_routing WHERE feature_code = 'document_generation';"
        )
    )
