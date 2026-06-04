"""Row-level permission scoping — see mica-internal/decisions/0020-row-level-permissions.md."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import or_, select

from app.models import (
    PurchaseOrder,
    PurchaseRequisition,
    User,
    UserRole,
    pr_collaborators,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.sql.elements import ColumnElement

_FULL_ACCESS_ROLES = frozenset(
    {
        UserRole.ADMIN.value,
        UserRole.PROCUREMENT_MGR.value,
        UserRole.IT_BUYER.value,
        UserRole.FINANCE_AUDITOR.value,
    }
)

_RFQ_HIDDEN_ROLES = frozenset(
    {
        UserRole.DEPT_MANAGER.value,
        UserRole.REQUESTER.value,
    }
)


def has_full_access(user: User) -> bool:
    """Return True if user's role grants unrestricted data access."""
    return user.role in _FULL_ACCESS_ROLES


def is_rfq_hidden(user: User) -> bool:
    """Return True if user should not see RFQ data."""
    return user.role in _RFQ_HIDDEN_ROLES


async def visible_pr_filter(session: AsyncSession, user: User) -> ColumnElement[bool] | None:
    """Return a WHERE clause restricting PR visibility, or None for full access.

    - Full-access roles: None (no filter)
    - dept_manager: PR.department_id == user.department_id
    - requester: OR(own PR, collaborator on PR)
    """
    if has_full_access(user):
        return None

    if user.role == UserRole.DEPT_MANAGER.value and user.department_id:
        return PurchaseRequisition.department_id == user.department_id

    collaborated_pr_ids = select(pr_collaborators.c.pr_id).where(
        pr_collaborators.c.user_id == user.id
    )
    return or_(
        PurchaseRequisition.requester_id == user.id,
        PurchaseRequisition.id.in_(collaborated_pr_ids),
    )


async def visible_pr_id_subquery(session: AsyncSession, user: User):
    """Return a subquery of PR IDs visible to user, or None for full access.

    Used by downstream entity filters to scope via PO.pr_id.
    """
    flt = await visible_pr_filter(session, user)
    if flt is None:
        return None
    return select(PurchaseRequisition.id).where(flt)


async def visible_po_id_subquery(session: AsyncSession, user: User):
    """Return a subquery of PO IDs visible to user, or None for full access.

    PO visibility is derived from PR visibility: PO.pr_id IN (visible PRs).
    """
    pr_sub = await visible_pr_id_subquery(session, user)
    if pr_sub is None:
        return None
    return select(PurchaseOrder.id).where(PurchaseOrder.pr_id.in_(pr_sub))


async def visible_contract_id_subquery(session: AsyncSession, user: User):
    """Return a subquery of Contract IDs visible to user, or None for full access.

    A contract is visible when its PO is visible (direct po_id link or via the
    po_contract_links M:N table).
    """
    from app.models import Contract, POContractLink

    po_sub = await visible_po_id_subquery(session, user)
    if po_sub is None:
        return None
    linked_contract_ids = select(POContractLink.contract_id).where(POContractLink.po_id.in_(po_sub))
    return select(Contract.id).where(
        (Contract.po_id.in_(po_sub)) | (Contract.id.in_(linked_contract_ids))
    )
