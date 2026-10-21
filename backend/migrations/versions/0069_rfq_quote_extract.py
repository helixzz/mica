"""ai: route for reading supplier quotations, plus its raster settings

Revision ID: 0069
Revises: 0068
Create Date: 2026-10-21

Reading a stamped quotation is the least trustworthy thing the vision model is
asked to do, so it gets its own feature route (its own model, prompt budget and
temperature) rather than sharing invoice_extract's. The two parameters control
rasterisation: quotations are often two pages, and reading only the first loses
rows without saying so, but there has to be a ceiling.

Nothing here writes business data — the endpoint only previews.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0069"
down_revision = "0068"
branch_labels = None
depends_on = None

_INSERT_PARAMETER = """
INSERT INTO system_parameters (
    id, key, category, value, data_type, default_value, min_value, max_value,
    unit, description_zh, description_en, is_sensitive, updated_by_id,
    created_at, updated_at
) VALUES (
    gen_random_uuid(), :key, 'api', to_jsonb(:value), :data_type,
    to_jsonb(:value), NULL, NULL, :unit,
    :description_zh, :description_en, false, NULL, now(), now()
)
"""

_PARAMETERS = [
    {
        "key": "ai.rfq_quote_dpi",
        "data_type": "int",
        "value": 250,
        "unit": "dpi",
        "description_zh": "读取报价单扫描件时的页面栅格化分辨率（越高越准、越慢）",
        "description_en": "Raster resolution when reading a scanned quotation",
    },
    {
        "key": "ai.rfq_quote_max_pages",
        "data_type": "int",
        "value": 5,
        "unit": "页",
        "description_zh": "报价单最多读取的页数；超出部分会给出提示",
        "description_en": "Maximum pages read from a quotation; the rest is reported",
    },
]


def upgrade() -> None:
    # Reuse whatever model invoice extraction already points at: a fresh install
    # has exactly one vision route configured, and pointing the new route at a
    # seeded placeholder would make it dead on arrival.
    op.execute(
        """
        INSERT INTO ai_feature_routing (
            id, feature_code, primary_model_id, fallback_model_ids,
            temperature, max_tokens, enabled, created_at, updated_at
        )
        SELECT gen_random_uuid(), 'rfq_quote_extract', r.primary_model_id, '[]'::jsonb,
               r.temperature, r.max_tokens, true, now(), now()
        FROM ai_feature_routing r
        WHERE r.feature_code = 'invoice_extract'
        ON CONFLICT (feature_code) DO NOTHING
        """
    )

    for item in _PARAMETERS:
        op.execute(sa.text(_INSERT_PARAMETER).bindparams(**item))


def downgrade() -> None:
    op.execute("DELETE FROM ai_feature_routing WHERE feature_code = 'rfq_quote_extract'")
    op.execute(
        "DELETE FROM system_parameters WHERE key IN ('ai.rfq_quote_dpi', 'ai.rfq_quote_max_pages')"
    )
