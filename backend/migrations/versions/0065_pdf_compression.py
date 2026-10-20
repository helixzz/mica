"""uploads: raise the ceiling to 50 MiB and compress scanned PDFs

Revision ID: 0065
Revises: 0064
Create Date: 2026-10-20

Contracts arrive as scans and routinely exceed the old 10 MiB limit. Raising the
limit alone would just store tens of megabytes of page images per contract, so
the upload path now re-encodes PDF page images with ghostscript (see
``services/pdf_compress.py``).

* ``upload.max_file_size_bytes`` → 50 MiB (nginx already allows 50M).
* ``pdf_compress.*`` parameters: switch, image resolution, JPEG quality, a
  grayscale toggle and an optional target size. Measured on a synthetic 3-page
  300 dpi scan: 200 dpi/q75 coloured 7.7x, 150 dpi/q65 10.4x (the default, which
  is the ~90% the procurement team expects), 120 dpi/q55 21.6x, and grayscale
  adds roughly 15% on top of any of them. Tune against real documents here
  rather than in code.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0065"
down_revision = "0064"
branch_labels = None
depends_on = None

_FIFTY_MIB = 50 * 1024 * 1024

# system_parameters.value / default_value are jsonb; to_jsonb() keeps the
# inserted scalar a JSON number/boolean rather than failing on a type mismatch.
_INSERT_PARAMETER = """
INSERT INTO system_parameters (
    id, key, category, value, data_type, default_value, min_value, max_value,
    unit, description_zh, description_en, is_sensitive, updated_by_id,
    created_at, updated_at
) VALUES (
    gen_random_uuid(), :key, 'upload', to_jsonb(:value), :data_type,
    to_jsonb(:value), NULL, NULL, :unit,
    :description_zh, :description_en, false, NULL, now(), now()
)
"""


_PARAMETERS = [
    {
        "key": "pdf_compress.enabled",
        "data_type": "bool",
        "value": True,
        "unit": None,
        "description_zh": "上传 PDF 时自动压缩（扫描件）",
        "description_en": "Compress scanned PDFs on upload",
    },
    {
        "key": "pdf_compress.image_dpi",
        "data_type": "int",
        "value": 150,
        "unit": "dpi",
        "description_zh": "压缩后页面图像分辨率（越低体积越小、文字越糊）",
        "description_en": "Page image resolution after compression",
    },
    {
        "key": "pdf_compress.jpeg_quality",
        "data_type": "int",
        "value": 65,
        "unit": "q",
        "description_zh": "压缩后页面图像的 JPEG 质量",
        "description_en": "JPEG quality of the page images after compression",
    },
    {
        "key": "pdf_compress.grayscale",
        "data_type": "bool",
        "value": False,
        "unit": None,
        "description_zh": "压缩时转灰度（更小，但会丢掉红章等颜色）",
        "description_en": "Convert to grayscale when compressing (smaller, loses red seals)",
    },
    {
        "key": "pdf_compress.target_size_mb",
        "data_type": "int",
        "value": 0,
        "unit": "MB",
        "description_zh": "目标体积（MB），0 表示不限制；设了就迭代压到接近该体积",
        "description_en": "Target size in MB (0 = no limit); refines harder until close",
    },
]


def upgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE system_parameters "
            "SET value = to_jsonb(:size), default_value = to_jsonb(:size) "
            "WHERE key = 'upload.max_file_size_bytes'"
        ).bindparams(sa.bindparam("size", _FIFTY_MIB))
    )

    for parameter in _PARAMETERS:
        op.execute(
            sa.text(_INSERT_PARAMETER).bindparams(
                key=parameter["key"],
                data_type=parameter["data_type"],
                unit=parameter["unit"],
                description_zh=parameter["description_zh"],
                description_en=parameter["description_en"],
                value=parameter["value"],
            )
        )


def downgrade() -> None:
    op.execute(
        sa.text(
            "DELETE FROM system_parameters WHERE key LIKE 'pdf_compress.%'"
        )
    )
    op.execute(
        sa.text(
            "UPDATE system_parameters "
            "SET value = to_jsonb(10485760), default_value = to_jsonb(10485760) "
            "WHERE key = 'upload.max_file_size_bytes'"
        )
    )
