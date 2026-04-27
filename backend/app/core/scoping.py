from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import or_, select

from app.models import (
    PurchaseRequisition,
    User,
    UserRole,
    user_cost_centers,
    user_departments,
)

if TYPE_CHECKING:
    from sqlalchemy.sql.elements import ColumnElement


async def _load_user_cost_center_ids(session, user: User) -> list:
    rows = (
        (
            await session.execute(
                select(user_cost_centers.c.cost_center_id).where(
                    user_cost_centers.c.user_id == user.id
                )
            )
        )
        .scalars()
        .all()
    )
    return list(rows)


async def _load_user_department_ids(session, user: User) -> list:
    rows = (
        (
            await session.execute(
                select(user_departments.c.department_id).where(
                    user_departments.c.user_id == user.id
                )
            )
        )
        .scalars()
        .all()
    )
    ids = list(rows)
    if user.department_id is not None and user.department_id not in ids:
        ids.append(user.department_id)
    return ids


def is_requester_scoped(user: User) -> bool:
    return user.role == UserRole.REQUESTER.value


async def visible_pr_filter(session, user: User) -> ColumnElement[bool] | None:
    if not is_requester_scoped(user):
        return None

    cost_center_ids = await _load_user_cost_center_ids(session, user)
    department_ids = await _load_user_department_ids(session, user)

    or_clauses = [PurchaseRequisition.requester_id == user.id]
    if cost_center_ids:
        or_clauses.append(PurchaseRequisition.cost_center_id.in_(cost_center_ids))
    if department_ids:
        or_clauses.append(PurchaseRequisition.department_id.in_(department_ids))

    return or_(*or_clauses)


async def visible_pr_id_subquery(session, user: User):
    if not is_requester_scoped(user):
        return None
    flt = await visible_pr_filter(session, user)
    if flt is None:
        return None
    return select(PurchaseRequisition.id).where(flt)
