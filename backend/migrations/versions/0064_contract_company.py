"""contracts: record the contracting entity

Revision ID: 0064
Revises: 0063
Create Date: 2026-10-20

A contract is a legal document, so exactly one of our companies signs it. Until
now that was only implicit: ``link_po_contract`` already refused to attach an
order from a different company than the contract's primary order, but the
contract itself carried no entity, so the UI could not say which company it was
for.

* Adds ``contracts.company_id`` (nullable, indexed, FK to companies).
* Backfills from the primary order, and — when that is somehow empty — from any
  order linked through ``po_contract_links``.
* New contracts inherit ``company_id`` from the order they are raised from.

The "one entity only" rule is enforced where orders get attached, not by a
database constraint: a contract always starts from an order and inherits its
entity, so a mismatch can only appear through linking.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0064"
down_revision = "0063"
branch_labels = None
depends_on = None

_BACKFILL_PRIMARY = """
UPDATE contracts c
SET company_id = po.company_id
FROM purchase_orders po
WHERE po.id = c.po_id
  AND c.company_id IS NULL
"""

_BACKFILL_LINKED = """
UPDATE contracts c
SET company_id = picked.company_id
FROM (
    SELECT DISTINCT ON (l.contract_id) l.contract_id, po.company_id
    FROM po_contract_links l
    JOIN purchase_orders po ON po.id = l.po_id
    WHERE po.company_id IS NOT NULL
    ORDER BY l.contract_id, l.created_at
) AS picked
WHERE picked.contract_id = c.id
  AND c.company_id IS NULL
"""


def upgrade() -> None:
    op.add_column(
        "contracts",
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_contracts_company_id_companies",
        "contracts",
        "companies",
        ["company_id"],
        ["id"],
    )
    op.create_index("ix_contracts_company_id", "contracts", ["company_id"])

    op.execute(sa.text(_BACKFILL_PRIMARY))
    op.execute(sa.text(_BACKFILL_LINKED))


def downgrade() -> None:
    op.drop_index("ix_contracts_company_id", table_name="contracts")
    op.drop_constraint("fk_contracts_company_id_companies", "contracts", type_="foreignkey")
    op.drop_column("contracts", "company_id")
