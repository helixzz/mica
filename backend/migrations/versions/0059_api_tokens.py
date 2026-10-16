"""personal access tokens (PAT) for user-authenticated API access

Revision ID: 0059
Revises: 0058
Create Date: 2026-10-16

v1.56.0: Mica gains a second credential kind beside the login JWT. Scripts,
other internal systems and AI agents authenticate with a personal access token
(``mica_pat_...``) that acts **as its owner**, so every existing role check,
Cerbos field policy and row-level filter keeps applying unchanged.

Security posture of what is stored here:

* ``token_hash`` holds ``sha256(secret)`` only. The plaintext is returned once,
  in the creation response, and is unrecoverable afterwards. sha256 (not
  bcrypt) is deliberate: the secret is 32 bytes of CSPRNG output, so there is
  nothing to brute-force, and this digest is verified on *every* API request.
* ``token_prefix`` is non-secret, indexed, and only used to locate the row
  before the constant-time comparison.
* revocation is a soft delete so audit history survives.

This revision:
1. creates ``api_tokens``,
2. adds the ``api`` value to the ``system_parameters.category`` check constraint,
3. seeds the six ``api.*`` parameters that govern token issuance, rate limiting
   and optional request auditing.
"""

import json

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0059"
down_revision = "0058"
branch_labels = None
depends_on = None

_CATEGORIES_WITH_API = (
    "'approval','auth','sku','contract','upload','pagination','audit','payment',"
    "'feishu','email','currency','notification','system','fulfillment','export','api'"
)
_CATEGORIES_WITHOUT_API = (
    "'approval','auth','sku','contract','upload','pagination','audit','payment',"
    "'feishu','email','currency','notification','system','fulfillment','export'"
)

# (key, data_type, value, min, max, unit, description_zh, description_en)
_PARAMS: tuple[tuple[str, str, str, str | None, str | None, str | None, str, str], ...] = (
    (
        "api.token.max_per_user",
        "int",
        "10",
        "1",
        "100",
        "tokens",
        "每个用户允许同时持有的未撤销 API 令牌数量上限。",
        "Maximum number of non-revoked API tokens a single user may hold.",
    ),
    (
        "api.token.default_ttl_days",
        "int",
        "90",
        "1",
        "3650",
        "days",
        "创建 API 令牌时未指定有效期则使用的默认天数。",
        "Default lifetime, in days, applied when a new API token does not specify one.",
    ),
    (
        "api.token.max_ttl_days",
        "int",
        "365",
        "1",
        "3650",
        "days",
        "API 令牌可申请的最长有效期；超过该值将被拒绝。",
        "Longest lifetime an API token may request; longer values are rejected.",
    ),
    (
        "api.rate_limit_per_minute",
        "int",
        "600",
        "30",
        "100000",
        "requests/min",
        "单个 API 令牌每分钟允许的请求数；超限返回 429 与 Retry-After。",
        "Requests per minute allowed for a single API token; exceeding it returns 429"
        " with Retry-After.",
    ),
    (
        "api.audit_requests",
        "bool",
        "false",
        None,
        None,
        None,
        "是否为每次使用 API 令牌的请求写审计记录（默认关闭，开启后写入量较大）。",
        "Whether every API-token request is written to the audit log (off by default;"
        " enabling it produces a large number of rows).",
    ),
    (
        "api.read_only_post_allowlist",
        "string",
        "/search,/exports,/insights,/ai,/dashboard",
        None,
        None,
        None,
        "只读令牌仍可调用的写方法端点前缀（逗号分隔），用于放行查询语义的 POST。",
        "Comma-separated path prefixes whose non-GET methods stay allowed for read-only"
        " tokens, because those POSTs are query semantics.",
    ),
)


def _json_literal(raw: str, data_type: str) -> str:
    """Render a parameter default as JSON text for ``CAST(:x AS jsonb)``."""
    if data_type in {"int", "bool"}:
        return raw
    return json.dumps(raw, ensure_ascii=False)


_INSERT_PARAM = sa.text(
    "INSERT INTO system_parameters"
    " (id, key, category, value, data_type, default_value,"
    "  min_value, max_value, unit, description_zh, description_en,"
    "  is_sensitive, created_at, updated_at)"
    " VALUES (gen_random_uuid(), :key, 'api', CAST(:value AS jsonb), :data_type,"
    "  CAST(:value AS jsonb), CAST(:min_value AS jsonb), CAST(:max_value AS jsonb),"
    "  :unit, :zh, :en, false, now(), now())"
    " ON CONFLICT (key) DO NOTHING"
).bindparams(
    # Explicit types: ``text()`` carries no schema information, so asyncpg would
    # otherwise send these as character varying and fail on the jsonb columns.
    sa.bindparam("key", type_=sa.Text()),
    sa.bindparam("value", type_=sa.Text()),
    sa.bindparam("data_type", type_=sa.Text()),
    sa.bindparam("min_value", type_=sa.Text()),
    sa.bindparam("max_value", type_=sa.Text()),
    sa.bindparam("unit", type_=sa.Text()),
    sa.bindparam("zh", type_=sa.Text()),
    sa.bindparam("en", type_=sa.Text()),
)


def upgrade() -> None:
    op.create_table(
        "api_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("token_prefix", sa.String(length=32), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "scopes",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_ip", sa.String(length=64), nullable=True),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_api_tokens_user_id_users",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_id"],
            ["users.id"],
            name="fk_api_tokens_created_by_id_users",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_api_tokens"),
        sa.UniqueConstraint("token_hash", name="uq_api_tokens_token_hash"),
    )
    op.create_index("ix_api_tokens_user_id", "api_tokens", ["user_id"])
    op.create_index("ix_api_tokens_token_prefix", "api_tokens", ["token_prefix"])
    op.create_index("ix_api_tokens_user_revoked", "api_tokens", ["user_id", "revoked_at"])

    op.execute(
        sa.text(
            "ALTER TABLE system_parameters DROP CONSTRAINT IF EXISTS "
            "system_parameters_category_check"
        )
    )
    op.execute(
        sa.text(
            "ALTER TABLE system_parameters ADD CONSTRAINT system_parameters_category_check"
            f" CHECK (category IN ({_CATEGORIES_WITH_API}))"
        )
    )

    bind = op.get_bind()
    for key, data_type, value, min_value, max_value, unit, desc_zh, desc_en in _PARAMS:
        bind.execute(
            _INSERT_PARAM,
            {
                "key": key,
                "value": _json_literal(value, data_type),
                "data_type": data_type,
                "min_value": _json_literal(min_value, "int") if min_value is not None else None,
                "max_value": _json_literal(max_value, "int") if max_value is not None else None,
                "unit": unit,
                "zh": desc_zh,
                "en": desc_en,
            },
        )


def downgrade() -> None:
    op.execute("DELETE FROM system_parameters WHERE key LIKE 'api.%'")
    op.execute(
        sa.text(
            "ALTER TABLE system_parameters DROP CONSTRAINT IF EXISTS "
            "system_parameters_category_check"
        )
    )
    op.execute(
        sa.text(
            "ALTER TABLE system_parameters ADD CONSTRAINT system_parameters_category_check"
            f" CHECK (category IN ({_CATEGORIES_WITHOUT_API}))"
        )
    )
    op.drop_index("ix_api_tokens_user_revoked", table_name="api_tokens")
    op.drop_index("ix_api_tokens_token_prefix", table_name="api_tokens")
    op.drop_index("ix_api_tokens_user_id", table_name="api_tokens")
    op.drop_table("api_tokens")
