"""Delivery address book.

Two kinds of entry live in one table:

* **shared** — ``owner_id IS NULL``, company-wide, maintained by admins and
  procurement managers;
* **private** — ``owner_id`` set to its creator.

A reader sees the shared entries of their own company plus their own private
entries. Requisitions and orders never point at an entry for their *content*:
they copy the three text fields at save time and keep ``delivery_address_id``
only as provenance, so editing or deleting an entry cannot rewrite history.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DeliveryAddress, User, UserRole

if TYPE_CHECKING:
    from app.schemas import DeliveryAddressIn, DeliveryAddressUpdateIn

_SHARED_MAINTAINER_ROLES = frozenset(
    {
        UserRole.ADMIN.value,
        UserRole.PROCUREMENT_MGR.value,
    }
)


def can_maintain_shared(user: User) -> bool:
    """Whether this user may create, edit or delete company-wide entries."""
    return user.role in _SHARED_MAINTAINER_ROLES


def _visible_to(user: User):
    """Shared entries of my company, plus every entry I own."""
    own = DeliveryAddress.owner_id == user.id
    shared = DeliveryAddress.owner_id.is_(None)
    if user.company_id is not None:
        # A shared entry is stamped with its creator's company. The explicit
        # NULL arm keeps rows inserted outside the API (seeds, manual fixes)
        # visible rather than silently hidden.
        shared = and_(
            shared,
            or_(
                DeliveryAddress.company_id.is_(None),
                DeliveryAddress.company_id == user.company_id,
            ),
        )
    return or_(own, shared)


def _normalize(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


async def _reload(db: AsyncSession, address_id: UUID) -> DeliveryAddress:
    """Re-read after commit.

    ``expire_on_commit=True`` in production expires the instance, so returning
    the in-memory object would make Pydantic's attribute access trigger a lazy
    load outside the greenlet context (``MissingGreenlet``).
    """
    stmt = select(DeliveryAddress).where(DeliveryAddress.id == address_id)
    return (await db.execute(stmt)).scalar_one()


async def _get_visible_or_404(db: AsyncSession, user: User, address_id: UUID) -> DeliveryAddress:
    stmt = select(DeliveryAddress).where(
        DeliveryAddress.id == address_id,
        _visible_to(user),
    )
    address = (await db.execute(stmt)).scalar_one_or_none()
    if address is None:
        raise HTTPException(404, "address.not_found")
    return address


def _assert_can_edit(user: User, address: DeliveryAddress) -> None:
    if address.owner_id == user.id:
        return
    if address.owner_id is None and can_maintain_shared(user):
        return
    raise HTTPException(403, "address.not_owner")


async def list_addresses(
    db: AsyncSession,
    user: User,
    *,
    include_inactive: bool = False,
) -> list[DeliveryAddress]:
    """Visible entries, most-used first.

    ``NULLS LAST`` matters: Postgres sorts ``DESC`` with nulls first by default,
    which would float every never-used entry above the frequently used ones.
    """
    stmt = select(DeliveryAddress).where(_visible_to(user))
    if not include_inactive:
        stmt = stmt.where(DeliveryAddress.is_active.is_(True))
    stmt = stmt.order_by(
        DeliveryAddress.usage_count.desc(),
        DeliveryAddress.last_used_at.desc().nulls_last(),
        DeliveryAddress.created_at.desc(),
    )
    return list((await db.execute(stmt)).scalars().all())


async def create_address(
    db: AsyncSession,
    user: User,
    payload: DeliveryAddressIn,
) -> DeliveryAddress:
    if payload.is_shared and not can_maintain_shared(user):
        raise HTTPException(403, "address.shared_requires_role")

    address = DeliveryAddress(
        label=_normalize(payload.label),
        contact_name=payload.contact_name.strip(),
        contact_phone=payload.contact_phone.strip(),
        detail=payload.detail.strip(),
        owner_id=None if payload.is_shared else user.id,
        company_id=user.company_id,
    )
    db.add(address)
    await db.commit()
    return await _reload(db, address.id)


async def update_address(
    db: AsyncSession,
    user: User,
    address_id: UUID,
    payload: DeliveryAddressUpdateIn,
) -> DeliveryAddress:
    address = await _get_visible_or_404(db, user, address_id)
    _assert_can_edit(user, address)

    # ``model_fields_set`` distinguishes "field omitted" from "explicitly
    # cleared", which is what lets a caller blank out an optional label.
    provided = payload.model_fields_set
    if "label" in provided:
        address.label = _normalize(payload.label)
    if payload.contact_name is not None:
        address.contact_name = payload.contact_name.strip()
    if payload.contact_phone is not None:
        address.contact_phone = payload.contact_phone.strip()
    if payload.detail is not None:
        address.detail = payload.detail.strip()
    if payload.is_active is not None:
        address.is_active = payload.is_active

    await db.commit()
    return await _reload(db, address.id)


async def delete_address(db: AsyncSession, user: User, address_id: UUID) -> None:
    """Hard-delete an entry.

    Safe by construction: requisitions and orders hold copies of the text, and
    ``delivery_address_id`` is ``ON DELETE SET NULL``.
    """
    address = await _get_visible_or_404(db, user, address_id)
    _assert_can_edit(user, address)
    await db.delete(address)
    await db.commit()


async def touch_usage(db: AsyncSession, address_id: UUID | None) -> None:
    """Record that an entry was picked, so frequent ones sort first.

    Silently ignores an unknown id: a requisition must still save if the picked
    entry was deleted in another tab between load and submit. Does not commit —
    the caller owns the transaction.
    """
    if address_id is None:
        return
    address = await db.get(DeliveryAddress, address_id)
    if address is None:
        return
    address.usage_count += 1
    address.last_used_at = datetime.now(UTC)
