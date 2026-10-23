from __future__ import annotations

import logging
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.dates import fmt_date
from app.core.money import fmt_amount
from app.i18n import t
from app.models import (
    AuditLog,
    Contract,
    Document,
    Invoice,
    InvoiceDocument,
    InvoiceLine,
    InvoiceStatus,
    PaymentRecord,
    PaymentSchedule,
    PaymentStatus,
    POContractLink,
    PODocument,
    POItem,
    POStatus,
    PurchaseOrder,
    PurchaseRequisition,
    Receipt,
    ScheduleItemStatus,
    SerialNumberEntry,
    Shipment,
    ShipmentDocument,
    ShipmentItem,
    ShipmentStatus,
    Supplier,
    User,
    UserRole,
)
from app.services import contracts as contract_svc

logger = logging.getLogger("mica.flow")

_PAYMENT_WRITE_ROLES = frozenset(
    {
        UserRole.ADMIN.value,
        UserRole.IT_BUYER.value,
        UserRole.PROCUREMENT_MGR.value,
        UserRole.FINANCE_AUDITOR.value,
    }
)


def _as_decimal(v) -> Decimal:
    return v if isinstance(v, Decimal) else Decimal(str(v))


async def _audit_write(
    db: AsyncSession, actor: User, event: str, rtype: str, rid: str, meta: dict | None = None
) -> None:
    db.add(
        AuditLog(
            actor_id=actor.id,
            actor_name=actor.display_name,
            event_type=event,
            resource_type=rtype,
            resource_id=rid,
            metadata_json=meta,
        )
    )


async def _load_po(db: AsyncSession, po_id: UUID) -> PurchaseOrder | None:
    return (
        await db.execute(
            select(PurchaseOrder)
            .where(PurchaseOrder.id == po_id)
            .options(selectinload(PurchaseOrder.items))
        )
    ).scalar_one_or_none()


async def suggest_contract_number(db: AsyncSession) -> str:
    from app.services.system_params import system_params

    raw_prefix = await system_params.get(db, "contract.number_prefix", "")
    if isinstance(raw_prefix, str) and raw_prefix.strip():
        prefix = raw_prefix.strip()
    else:
        prefix = "ACME"
    now = datetime.now(UTC)
    full_prefix = f"{prefix}{now.year:04d}{now.month:02d}{now.day:02d}"
    max_suffix = (
        await db.execute(
            select(func.max(Contract.contract_number)).where(
                Contract.contract_number.like(f"{full_prefix}%")
            )
        )
    ).scalar_one_or_none()
    next_seq = 1
    if max_suffix and len(max_suffix) == len(full_prefix) + 3:
        try:
            next_seq = int(max_suffix[-3:]) + 1
        except ValueError:
            next_seq = 1
    return f"{full_prefix}{next_seq:03d}"


def _contract_currency(requested: str | None, po: PurchaseOrder) -> str:
    """A contract is paid in its order's currency; say so if the caller disagrees.

    ContractCreateIn used to have no currency field at all, so Pydantic dropped the
    value without complaint and the contract silently stored the order's currency.
    """
    if requested and requested.strip().upper() != (po.currency or "CNY").upper():
        raise HTTPException(
            422,
            f"contract.currency_follows_order: order={po.currency} requested={requested}",
        )
    return po.currency or "CNY"


async def create_contract(
    db: AsyncSession,
    actor: User,
    po_id: UUID,
    title: str,
    total_amount: Decimal,
    signed_date=None,
    effective_date=None,
    expiry_date=None,
    notes: str | None = None,
    contract_number: str | None = None,
    currency: str | None = None,
) -> Contract:
    po = await _load_po(db, po_id)
    if po is None:
        raise HTTPException(404, "po.not_found")

    if contract_number:
        number = contract_number.strip()
        if not number:
            raise HTTPException(400, "contract.number_required")
        collision = (
            await db.execute(
                select(func.count(Contract.id)).where(Contract.contract_number == number)
            )
        ).scalar_one() or 0
        if collision > 0:
            raise HTTPException(409, "contract.number_duplicate")
    else:
        number = await suggest_contract_number(db)

    contract = Contract(
        contract_number=number,
        po_id=po.id,
        supplier_id=po.supplier_id,
        company_id=po.company_id,
        title=title,
        currency=_contract_currency(currency, po),
        total_amount=_as_decimal(total_amount),
        signed_date=signed_date,
        effective_date=effective_date,
        expiry_date=expiry_date,
        notes=notes,
    )
    db.add(contract)
    await db.flush()
    db.add(POContractLink(po_id=po.id, contract_id=contract.id))
    await db.flush()
    await contract_svc.create_contract_version(
        db,
        contract=contract,
        actor=actor,
        change_type="created",
    )
    await _audit_write(
        db,
        actor,
        "contract.created",
        "contract",
        str(contract.id) or "",
        meta={"contract_number": number, "po_id": str(po.id)},
    )
    await db.commit()

    try:
        from app.db import AsyncSessionLocal
        from app.models import User, UserRole
        from app.services.notifications import emit_event_notification, status_label, user_locale
        from app.services.system_params import notification_enabled, system_params

        async with AsyncSessionLocal() as notif_db:
            if await notification_enabled(notif_db, "contract_created"):
                recipients: set[UUID] = {actor.id}
                pr = await notif_db.get(PurchaseRequisition, po.pr_id)
                if pr and pr.requester_id:
                    recipients.add(pr.requester_id)

                if await system_params.get_bool_or(
                    notif_db, "notifications.broadcast_admin_events", False
                ):
                    admin_rows = (
                        (
                            await notif_db.execute(
                                select(User.id).where(
                                    User.role.in_(
                                        [UserRole.ADMIN.value, UserRole.PROCUREMENT_MGR.value]
                                    ),
                                    User.is_active.is_(True),
                                )
                            )
                        )
                        .scalars()
                        .all()
                    )
                    recipients.update(admin_rows)

                for uid in recipients:
                    user = await notif_db.get(User, uid)
                    if user is None:
                        continue
                    locale = user_locale(user)
                    await emit_event_notification(
                        notif_db,
                        user_id=user.id,
                        event="contract_created",
                        title=t(
                            "notification.event.contract_created",
                            locale,
                            contract_number=contract.contract_number,
                        ),
                        link_url=f"/contracts/{contract.id}",
                        biz_type="contract",
                        biz_id=contract.id,
                        fields=[
                            (
                                t("notification.label.contract", locale),
                                contract.contract_number,
                            ),
                            (t("notification.label.po", locale), po.po_number),
                            (t("notification.label.pr", locale), po.pr_title or "—"),
                            (
                                t("notification.label.amount", locale),
                                fmt_amount(contract.total_amount, contract.currency),
                            ),
                            (
                                t("notification.label.effective", locale),
                                fmt_date(contract.effective_date, locale),
                            ),
                            (
                                t("notification.label.expires", locale),
                                fmt_date(contract.expiry_date, locale),
                            ),
                            (
                                t("notification.label.status", locale),
                                status_label(contract.status or "active", locale),
                            ),
                            (t("notification.label.created_by", locale), actor.display_name),
                        ],
                        fingerprint_parts=("created", contract.contract_number),
                    )
                await notif_db.commit()
    except Exception:
        logger.warning(
            "Failed to send contract_created notification for contract=%s",
            contract.id,
            exc_info=True,
        )

    await db.refresh(contract)
    return contract


async def list_contracts(
    db: AsyncSession,
    po_id: UUID | None = None,
    actor: User | None = None,
) -> list[Contract]:
    stmt = (
        select(Contract)
        .order_by(Contract.created_at.desc())
        .options(
            selectinload(Contract.po),
            selectinload(Contract.supplier),
            selectinload(Contract.company),
        )
    )
    if po_id:
        linked_ids = (
            (
                await db.execute(
                    select(POContractLink.contract_id).where(POContractLink.po_id == po_id)
                )
            )
            .scalars()
            .all()
        )
        if linked_ids:
            stmt = stmt.where(or_(Contract.po_id == po_id, Contract.id.in_(linked_ids)))
        else:
            stmt = stmt.where(Contract.po_id == po_id)
    if actor is not None:
        from app.core.scoping import visible_po_id_subquery

        visible_po_ids = await visible_po_id_subquery(db, actor)
        if visible_po_ids is not None:
            stmt = stmt.where(Contract.po_id.in_(visible_po_ids))
    return list((await db.execute(stmt)).scalars().all())


async def list_linked_pos(db: AsyncSession, contract_id: UUID) -> list[PurchaseOrder]:
    contract = (
        await db.execute(select(Contract).where(Contract.id == contract_id))
    ).scalar_one_or_none()
    if contract is None:
        raise HTTPException(404, "contract.not_found")

    link_ids = (
        (
            await db.execute(
                select(POContractLink.po_id).where(POContractLink.contract_id == contract_id)
            )
        )
        .scalars()
        .all()
    )
    po_ids: set[UUID] = set(link_ids)
    if contract.po_id:
        po_ids.add(contract.po_id)
    if not po_ids:
        return []
    rows = (
        (
            await db.execute(
                select(PurchaseOrder)
                .where(PurchaseOrder.id.in_(po_ids))
                .order_by(PurchaseOrder.po_number)
            )
        )
        .scalars()
        .all()
    )
    return list(rows)


async def link_po_contract(
    db: AsyncSession,
    actor: User,
    po_id: UUID,
    contract_id: UUID,
) -> POContractLink:
    po = await _load_po(db, po_id)
    if po is None:
        raise HTTPException(404, "po.not_found")
    contract = await _load_contract(db, contract_id)

    existing = (
        await db.execute(
            select(POContractLink).where(
                POContractLink.po_id == po_id,
                POContractLink.contract_id == contract_id,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing

    primary_po = await _load_po(db, contract.po_id)
    if primary_po is None:
        raise HTTPException(404, "po.not_found")
    if po.supplier_id != contract.supplier_id:
        raise HTTPException(409, "po_contract_link.supplier_mismatch")
    if po.company_id != primary_po.company_id:
        raise HTTPException(409, "po_contract_link.company_mismatch")
    if po.currency != contract.currency:
        raise HTTPException(409, "po_contract_link.currency_mismatch")

    link = POContractLink(po_id=po_id, contract_id=contract_id)
    db.add(link)
    await _audit_write(
        db,
        actor,
        "po_contract.linked",
        "contract",
        str(contract.id),
        meta={"po_id": str(po_id), "po_number": po.po_number},
    )
    await db.commit()
    return link


async def unlink_po_contract(
    db: AsyncSession,
    actor: User,
    po_id: UUID,
    contract_id: UUID,
) -> None:
    po = await _load_po(db, po_id)
    if po is None:
        raise HTTPException(404, "po.not_found")
    contract = await _load_contract(db, contract_id)

    link = (
        await db.execute(
            select(POContractLink).where(
                POContractLink.po_id == po_id,
                POContractLink.contract_id == contract_id,
            )
        )
    ).scalar_one_or_none()
    if link is None:
        raise HTTPException(404, "po_contract_link.not_found")

    if contract.po_id == po_id:
        raise HTTPException(409, "po_contract_link.cannot_unlink_primary")

    other_links = (
        await db.execute(
            select(func.count(POContractLink.po_id)).where(
                POContractLink.contract_id == contract_id,
                POContractLink.po_id != po_id,
            )
        )
    ).scalar_one()
    is_primary_po = contract.po_id == po_id
    if other_links == 0 and is_primary_po:
        raise HTTPException(409, "po_contract_link.cannot_remove_last")

    has_payments = (
        await db.execute(
            select(func.count(PaymentRecord.id)).where(
                PaymentRecord.contract_id == contract_id,
                PaymentRecord.po_id == po_id,
            )
        )
    ).scalar_one()
    if has_payments > 0:
        raise HTTPException(409, "po_contract_link.has_payments")

    await db.delete(link)
    await _audit_write(
        db,
        actor,
        "po_contract.unlinked",
        "contract",
        str(contract.id),
        meta={"po_id": str(po_id), "po_number": po.po_number},
    )
    await db.commit()


async def get_contract(db: AsyncSession, contract_id: UUID, actor: User | None = None) -> Contract:
    stmt = (
        select(Contract)
        .where(Contract.id == contract_id)
        .options(
            selectinload(Contract.po),
            selectinload(Contract.supplier),
            selectinload(Contract.company),
        )
    )
    contract = (await db.execute(stmt)).scalar_one_or_none()
    if contract is None:
        raise HTTPException(404, "contract.not_found")
    if actor is not None:
        from app.core.scoping import has_full_access, visible_pr_filter

        if not has_full_access(actor) and contract.po is not None:
            scope_filter = await visible_pr_filter(db, actor)
            if scope_filter is not None:
                check = await db.execute(
                    select(PurchaseRequisition.id).where(
                        PurchaseRequisition.id == contract.po.pr_id, scope_filter
                    )
                )
                if check.scalar_one_or_none() is None:
                    raise HTTPException(403, "insufficient_role")
    return contract


_ALLOWED_CONTRACT_EDIT_FIELDS: frozenset[str] = frozenset(
    {"title", "total_amount", "signed_date", "effective_date", "expiry_date", "notes"}
)

#: Contract field → notification label key. Unknown fields fall back to the raw
#: column name, which is ugly but honest; adding a mapping is one line.
_CONTRACT_FIELD_LABELS: dict[str, str] = {
    "title": "title",
    "total_amount": "amount",
    "signed_date": "date",
    "effective_date": "effective",
    "expiry_date": "expires",
    "notes": "reason",
}


def _contract_field_label(field: str, locale: str) -> str:
    key = _CONTRACT_FIELD_LABELS.get(field)
    return t(f"notification.label.{key}", locale) if key else field


def _contract_field_text(field: str, value: object, contract: Contract, locale: str) -> str:
    if value is None or value == "":
        return "—"
    if field == "total_amount":
        return fmt_amount(value, getattr(contract, "currency", "CNY"))  # type: ignore[arg-type]
    if field in ("signed_date", "effective_date", "expiry_date"):
        return fmt_date(value, locale)  # type: ignore[arg-type]
    return str(value)


# Terminal statuses block further edits/transitions — once a contract is
# superseded/terminated/expired, its terms are frozen for the audit trail.
_CONTRACT_TERMINAL_STATUSES: frozenset[str] = frozenset({"superseded", "terminated", "expired"})

_CONTRACT_STATUS_TRANSITIONS: dict[str, frozenset[str]] = {
    "active": frozenset({"superseded", "terminated", "expired"}),
}


async def _load_contract(db: AsyncSession, contract_id: UUID) -> Contract:
    contract = (
        await db.execute(select(Contract).where(Contract.id == contract_id))
    ).scalar_one_or_none()
    if contract is None:
        raise HTTPException(404, "contract.not_found")
    return contract


async def update_contract(
    db: AsyncSession,
    actor: User,
    contract_id: UUID,
    updates: dict,
) -> Contract:
    contract = await _load_contract(db, contract_id)
    if contract.status in _CONTRACT_TERMINAL_STATUSES:
        raise HTTPException(409, "contract.not_editable_in_status")

    changed: dict[str, tuple[object, object]] = {}
    for field in _ALLOWED_CONTRACT_EDIT_FIELDS:
        if field not in updates:
            continue
        value = updates[field]
        if field == "total_amount" and value is not None:
            value = _as_decimal(value)
        previous = getattr(contract, field)
        if previous != value:
            setattr(contract, field, value)
            changed[field] = (previous, value)

    if not changed:
        return contract

    contract.current_version = (contract.current_version or 1) + 1
    await db.flush()
    await contract_svc.create_contract_version(
        db,
        contract=contract,
        actor=actor,
        change_type="updated",
        change_reason=updates.get("change_reason"),
        change_summary=updates.get("change_summary"),
    )
    await _audit_write(
        db,
        actor,
        "contract.updated",
        "contract",
        str(contract.id),
        meta={"fields": list(changed.keys())},
    )
    await db.commit()
    await db.refresh(contract)

    try:
        from app.db import AsyncSessionLocal
        from app.models import PurchaseOrder, User, UserRole
        from app.services.notifications import emit_event_notification, status_label, user_locale
        from app.services.system_params import notification_enabled, system_params

        async with AsyncSessionLocal() as notif_db:
            if await notification_enabled(notif_db, "contract_updated"):
                recipients: set[UUID] = set()
                po = await notif_db.get(PurchaseOrder, contract.po_id)
                if po and po.created_by_id:
                    recipients.add(po.created_by_id)
                if po and po.pr_id:
                    pr = await notif_db.get(PurchaseRequisition, po.pr_id)
                    if pr and pr.requester_id:
                        recipients.add(pr.requester_id)

                if await system_params.get_bool_or(
                    notif_db, "notifications.broadcast_admin_events", False
                ):
                    admin_rows = (
                        (
                            await notif_db.execute(
                                select(User.id).where(
                                    User.role.in_(
                                        [UserRole.ADMIN.value, UserRole.PROCUREMENT_MGR.value]
                                    ),
                                    User.is_active.is_(True),
                                )
                            )
                        )
                        .scalars()
                        .all()
                    )
                    recipients.update(admin_rows)

                for uid in recipients:
                    user = await notif_db.get(User, uid)
                    if user is None:
                        continue
                    locale = user_locale(user)
                    changes = [
                        (
                            _contract_field_label(field, locale),
                            f"{_contract_field_text(field, old, contract, locale)}"
                            f" → {_contract_field_text(field, new, contract, locale)}",
                        )
                        for field, (old, new) in changed.items()
                    ]
                    await emit_event_notification(
                        notif_db,
                        user_id=user.id,
                        event="contract_updated",
                        title=t(
                            "notification.event.contract_updated",
                            locale,
                            contract_number=contract.contract_number,
                        ),
                        link_url=f"/contracts/{contract.id}",
                        biz_type="contract",
                        biz_id=contract.id,
                        fields=[
                            (
                                t("notification.label.contract", locale),
                                contract.contract_number,
                            ),
                            (t("notification.label.title", locale), contract.title),
                            (
                                t("notification.label.amount", locale),
                                fmt_amount(contract.total_amount, contract.currency),
                            ),
                            (
                                t("notification.label.status", locale),
                                status_label(contract.status or "active", locale),
                            ),
                            (
                                t("notification.label.updated_by", locale),
                                actor.display_name,
                            ),
                        ],
                        changes=changes,
                        fingerprint_parts=(
                            "updated",
                            *[f"{key}={value[1]}" for key, value in sorted(changed.items())],
                        ),
                    )
                await notif_db.commit()
    except Exception:
        logger.warning(
            "Failed to send contract_updated notification for contract=%s",
            contract.id,
            exc_info=True,
        )

    return contract


async def transition_contract_status(
    db: AsyncSession,
    actor: User,
    contract_id: UUID,
    new_status: str,
    reason: str | None = None,
) -> Contract:
    contract = await _load_contract(db, contract_id)
    current = contract.status or "active"
    allowed = _CONTRACT_STATUS_TRANSITIONS.get(current, frozenset())
    if new_status not in allowed:
        raise HTTPException(409, "contract.invalid_status_transition")

    contract.status = new_status
    contract.current_version = (contract.current_version or 1) + 1
    await db.flush()
    await contract_svc.create_contract_version(
        db,
        contract=contract,
        actor=actor,
        change_type=new_status,
        change_reason=reason,
    )
    await _audit_write(
        db,
        actor,
        "contract.status_changed",
        "contract",
        str(contract.id),
        meta={"from": current, "to": new_status, "reason": reason},
    )
    await db.commit()

    if new_status in ("terminated", "superseded"):
        try:
            from app.db import AsyncSessionLocal
            from app.models import PurchaseOrder, User, UserRole
            from app.services.notifications import (
                emit_event_notification,
                status_label,
                user_locale,
            )
            from app.services.system_params import notification_enabled

            async with AsyncSessionLocal() as notif_db:
                if await notification_enabled(notif_db, "contract_status_changed"):
                    recipients: set[UUID] = set()
                    po = await notif_db.get(PurchaseOrder, contract.po_id)
                    if po and po.created_by_id:
                        recipients.add(po.created_by_id)
                    if po and po.pr_id:
                        pr = await notif_db.get(PurchaseRequisition, po.pr_id)
                        if pr and pr.requester_id:
                            recipients.add(pr.requester_id)
                    admin_rows = (
                        (
                            await notif_db.execute(
                                select(User.id).where(
                                    User.role.in_(
                                        [UserRole.ADMIN.value, UserRole.PROCUREMENT_MGR.value]
                                    ),
                                    User.is_active.is_(True),
                                )
                            )
                        )
                        .scalars()
                        .all()
                    )
                    recipients.update(admin_rows)

                    for uid in recipients:
                        user = await notif_db.get(User, uid)
                        if user is None:
                            continue
                        locale = user_locale(user)
                        await emit_event_notification(
                            notif_db,
                            user_id=user.id,
                            event="contract_status_changed",
                            title=t(
                                "notification.event.contract_status_changed",
                                locale,
                                contract_number=contract.contract_number,
                                status=status_label(new_status, locale),
                            ),
                            link_url=f"/contracts/{contract.id}",
                            biz_type="contract",
                            biz_id=contract.id,
                            fields=[
                                (
                                    t("notification.label.contract", locale),
                                    contract.contract_number,
                                ),
                                (t("notification.label.title", locale), contract.title),
                                (
                                    t("notification.label.status", locale),
                                    status_label(new_status, locale),
                                ),
                            ],
                            changes=[
                                (
                                    t("notification.label.status", locale),
                                    f"{status_label(current, locale)}"
                                    f" → {status_label(new_status, locale)}",
                                ),
                                (t("notification.label.reason", locale), reason or "—"),
                                (
                                    t("notification.label.updated_by", locale),
                                    actor.display_name,
                                ),
                            ],
                            status="warning",
                            fingerprint_parts=("status", new_status),
                        )
                    await notif_db.commit()
        except Exception:
            logger.warning(
                "Failed to send contract_status_changed notification for contract=%s",
                contract.id,
                exc_info=True,
            )

    await db.refresh(contract)
    return contract


async def delete_contract(
    db: AsyncSession,
    actor: User,
    contract_id: UUID,
) -> None:
    contract = await _load_contract(db, contract_id)
    paid = (
        await db.execute(
            select(func.count(PaymentRecord.id)).where(
                PaymentRecord.schedule_item_id.in_(
                    select(PaymentSchedule.id).where(PaymentSchedule.contract_id == contract.id)
                ),
                PaymentRecord.status == PaymentStatus.CONFIRMED.value,
            )
        )
    ).scalar_one() or 0
    if paid > 0:
        raise HTTPException(409, "contract.cannot_delete_with_paid_schedule")

    number = contract.contract_number
    await db.delete(contract)
    await _audit_write(
        db,
        actor,
        "contract.deleted",
        "contract",
        str(contract_id),
        meta={"contract_number": number},
    )
    await db.commit()


async def _receipt_tolerance(db: AsyncSession) -> Decimal:
    """Over-receipt allowance for one PO line, as a multiplier of ordered qty.

    ``1`` means "never accept more than ordered". The value lives in
    ``system_parameters`` so a business that tolerates a supplier over-shipping
    can raise it without a code change.
    """
    from app.services.system_params import system_params

    raw = await system_params.get(db, "fulfillment.over_receipt_tolerance", "1")
    try:
        tolerance = _as_decimal(raw)
    except (ArithmeticError, ValueError):
        return Decimal("1")
    return tolerance if tolerance >= Decimal("1") else Decimal("1")


def _assert_within_tolerance(po_item: POItem, projected: Decimal, tolerance: Decimal) -> None:
    """Reject a receipt that would push one PO line past ordered qty × tolerance."""
    ordered = _as_decimal(po_item.qty or 0)
    if ordered <= 0:
        return
    if projected > ordered * tolerance:
        raise HTTPException(
            409,
            f"shipment.over_receipt:{po_item.item_name}:ordered={ordered}:projected={projected}",
        )


async def recompute_po_receipt(db: AsyncSession, po_id: UUID) -> None:
    """Re-derive POItem.qty_received, PO.qty_received and PO.status from receipts.

    Receipt rows are the single source of truth for what a PO has received —
    a line can be received in several steps, and the goods arriving is a
    different event from the supplier shipping them. Every write that moves
    quantities (shipment create/update/delete, receipt create/delete)
    *recomputes* the aggregates instead of nudging them, so no path can leave a
    deleted quantity behind.

    ``ShipmentItem.qty_received`` is kept as a derived cache of what each batch
    contributed, so batch views stay meaningful without being the source.

    Status follows D2 of the receipt-decoupling design: received quantities win,
    then "a batch exists" means shipped, then back to confirmed. Terminal states
    (draft / cancelled / closed) are never overwritten.
    """
    po = await _load_po(db, po_id)
    if po is None:
        return

    rows = (
        await db.execute(
            select(Receipt.po_item_id, func.coalesce(func.sum(Receipt.qty), 0))
            .where(Receipt.po_id == po_id)
            .group_by(Receipt.po_item_id)
        )
    ).all()
    received_by_item = {row[0]: _as_decimal(row[1]) for row in rows}

    for item in po.items:
        item.qty_received = received_by_item.get(item.id, Decimal("0"))

    shipments = (
        (
            await db.execute(
                select(Shipment)
                .where(Shipment.po_id == po_id)
                .options(selectinload(Shipment.items))
            )
        )
        .scalars()
        .all()
    )
    batch_rows = (
        await db.execute(
            select(ShipmentItem.id, func.coalesce(func.sum(Receipt.qty), 0))
            .select_from(ShipmentItem)
            # A receipt points at the *batch*, not at a batch line, so it joins
            # on the batch id that the batch's lines share.
            .outerjoin(Receipt, Receipt.shipment_id == ShipmentItem.shipment_id)
            .join(Shipment, ShipmentItem.shipment_id == Shipment.id)
            .where(Shipment.po_id == po_id)
            .group_by(ShipmentItem.id)
        )
    ).all()
    received_by_batch = {row[0]: _as_decimal(row[1]) for row in batch_rows}
    for shipment in shipments:
        for shipment_item in shipment.items:
            shipment_item.qty_received = received_by_batch.get(shipment_item.id, Decimal("0"))

    total_received = sum((_as_decimal(i.qty_received or 0) for i in po.items), start=Decimal("0"))
    total_qty = sum((_as_decimal(i.qty or 0) for i in po.items), start=Decimal("0"))
    po.qty_received = total_received
    po.status = _receipt_status(po.status, total_received, total_qty, has_shipment=bool(shipments))


_RECEIPT_LOCKED_STATES = frozenset(
    {POStatus.DRAFT.value, POStatus.CANCELLED.value, POStatus.CLOSED.value}
)


def _receipt_status(
    current: str,
    total_received: Decimal,
    total_qty: Decimal,
    *,
    has_shipment: bool = False,
) -> str:
    """Map receipts (and the existence of a batch) onto POStatus.

    Order matters: receipts outrank "shipped", so a partially received order
    never falls back to the weaker shipped label. Terminal states are returned
    untouched — a cancelled order with a leftover batch must stay cancelled.
    """
    if current in _RECEIPT_LOCKED_STATES:
        return current
    if total_qty > 0 and total_received >= total_qty:
        return POStatus.FULLY_RECEIVED.value
    if total_received > 0:
        return POStatus.PARTIALLY_RECEIVED.value
    if has_shipment:
        return POStatus.SHIPPED.value
    if current in (
        POStatus.FULLY_RECEIVED.value,
        POStatus.PARTIALLY_RECEIVED.value,
        POStatus.SHIPPED.value,
    ):
        return POStatus.CONFIRMED.value
    return current


async def create_shipment(
    db: AsyncSession,
    actor: User,
    po_id: UUID,
    items_in: list[dict],
    carrier: str | None = None,
    tracking_number: str | None = None,
    expected_date=None,
    actual_date=None,
    notes: str | None = None,
    contract_id: UUID | None = None,
) -> Shipment:
    po = await _load_po(db, po_id)
    if po is None:
        raise HTTPException(404, "po.not_found")

    if contract_id is not None:
        contract = await db.get(Contract, contract_id)
        if contract is None:
            raise HTTPException(404, "contract.not_found")

    existing_count = (
        await db.execute(select(func.count(Shipment.id)).where(Shipment.po_id == po_id))
    ).scalar_one() or 0
    batch_no = existing_count + 1
    shipment_number = f"{po.po_number}-S{batch_no:02d}"

    shipment = Shipment(
        shipment_number=shipment_number,
        po_id=po_id,
        contract_id=contract_id,
        batch_no=batch_no,
        is_default=(batch_no == 1),
        status=ShipmentStatus.ARRIVED.value if actual_date else ShipmentStatus.IN_TRANSIT.value,
        carrier=carrier,
        tracking_number=tracking_number,
        expected_date=expected_date,
        actual_date=actual_date,
        notes=notes,
    )
    db.add(shipment)
    await db.flush()

    po_item_map = {str(i.id): i for i in po.items}
    for idx, item_in in enumerate(items_in, start=1):
        po_item_id = item_in["po_item_id"]
        po_item = po_item_map.get(str(po_item_id))
        if po_item is None:
            raise HTTPException(422, "shipment.invalid_po_item")
        qty_shipped = _as_decimal(item_in["qty_shipped"])
        # A batch records what the supplier shipped. What we *accepted* is a
        # separate act with its own rows (receipts), so a new batch starts at
        # zero received and the order moves to "shipped" rather than claiming
        # the goods already arrived.
        db.add(
            ShipmentItem(
                shipment_id=shipment.id,
                po_item_id=po_item.id,
                line_no=idx,
                item_name=po_item.item_name,
                qty_shipped=qty_shipped,
                qty_received=Decimal("0"),
                unit_price=po_item.unit_price,
            )
        )

    await db.flush()
    await recompute_po_receipt(db, po_id)

    await _audit_write(
        db,
        actor,
        "shipment.created",
        "shipment",
        str(shipment.id),
        meta={"po_id": str(po_id), "batch_no": batch_no},
    )
    await db.commit()

    try:
        from app.db import AsyncSessionLocal
        from app.services.notifications import emit_event_notification, user_locale
        from app.services.system_params import notification_enabled

        async with AsyncSessionLocal() as notif_db:
            if await notification_enabled(notif_db, "shipment_received"):
                fully_received = po.status == POStatus.FULLY_RECEIVED.value
                ordered_qty = sum((_as_decimal(i.qty or 0) for i in po.items), start=Decimal("0"))
                received_qty = _as_decimal(po.qty_received or 0)
                percent = (
                    f"{(float(received_qty) / float(ordered_qty) * 100):.0f}%"
                    if ordered_qty
                    else "0%"
                )

                recipients: set[UUID] = {actor.id}
                if po.created_by_id:
                    recipients.add(po.created_by_id)
                pr = await notif_db.get(PurchaseRequisition, po.pr_id)
                if pr and pr.requester_id:
                    recipients.add(pr.requester_id)

                for uid in recipients:
                    user = await notif_db.get(User, uid)
                    if user is None:
                        continue
                    locale = user_locale(user)
                    await emit_event_notification(
                        notif_db,
                        user_id=user.id,
                        event="po_receipt",
                        title=t(
                            "notification.event.po_receipt",
                            locale,
                            po_number=po.po_number,
                            state=t(
                                "feishu.card.receipt.state"
                                if fully_received
                                else "feishu.card.receipt.state_partial",
                                locale,
                            ),
                        ),
                        link_url=f"/purchase-orders/{po.id}",
                        biz_type="po",
                        biz_id=po.id,
                        status="success" if fully_received else "action",
                        fingerprint_parts=("receipt", received_qty, fully_received),
                        meta={
                            "kind": "po_receipt",
                            "po_number": po.po_number,
                            "pr_title": po.pr_title or "",
                            "received": str(received_qty),
                            "ordered": str(ordered_qty),
                            "percent": percent,
                            "shipment_number": (
                                f"{shipment.shipment_number} (Batch {shipment.batch_no})"
                            ),
                            "carrier": shipment.carrier or "",
                            "tracking": shipment.tracking_number or "",
                            "fully_received": fully_received,
                        },
                    )
                await notif_db.commit()
    except Exception:
        logger.warning(
            "Failed to send shipment_received notification for shipment=%s",
            shipment.id,
            exc_info=True,
        )

    result = await db.execute(
        select(Shipment).where(Shipment.id == shipment.id).options(selectinload(Shipment.items))
    )
    return result.scalar_one()


async def list_shipments(
    db: AsyncSession,
    po_id: UUID | None = None,
    contract_id: UUID | None = None,
    actor: User | None = None,
) -> list[Shipment]:
    stmt = (
        select(Shipment).options(selectinload(Shipment.items)).order_by(Shipment.created_at.desc())
    )
    if po_id:
        stmt = stmt.where(Shipment.po_id == po_id)
    elif contract_id:
        contract = await db.get(Contract, contract_id)
        if contract is None:
            raise HTTPException(404, "contract.not_found")
        legacy_po_ids = set(
            (await db.execute(select(Contract.po_id).where(Contract.id == contract_id)))
            .scalars()
            .all()
        )
        m2m_po_ids = set(
            (
                await db.execute(
                    select(POContractLink.po_id).where(POContractLink.contract_id == contract_id)
                )
            )
            .scalars()
            .all()
        )
        all_po_ids = legacy_po_ids | m2m_po_ids
        conditions = [Shipment.contract_id == contract_id]
        if all_po_ids:
            conditions.append(Shipment.po_id.in_(all_po_ids))
        stmt = stmt.where(or_(*conditions))
    if actor is not None:
        from app.core.scoping import (
            visible_contract_id_subquery,
            visible_po_id_subquery,
        )

        visible_po_ids = await visible_po_id_subquery(db, actor)
        if visible_po_ids is not None:
            visible_contract_ids = await visible_contract_id_subquery(db, actor)
            stmt = stmt.where(
                or_(
                    Shipment.po_id.in_(visible_po_ids),
                    Shipment.contract_id.in_(visible_contract_ids),
                )
            )
    return list((await db.execute(stmt)).scalars().all())


_RECEIPT_MANAGER_ROLES = frozenset(
    {
        UserRole.ADMIN.value,
        UserRole.IT_BUYER.value,
        UserRole.PROCUREMENT_MGR.value,
    }
)


async def _notify_receipt_event(
    db: AsyncSession, actor: User, po_id: UUID, *, action: str, summary: str
) -> None:
    """Tell the people who care that goods arrived (or that it was undone).

    Receiving is usually the requester's act, so the signal has to travel the
    other way: to whoever runs the order and to the procurement managers of the
    same company. Failures never block the receipt itself.
    """
    try:
        from app.db import AsyncSessionLocal
        from app.models import NotificationCategory
        from app.services.notifications import create_notification
        from app.services.system_params import notification_enabled

        async with AsyncSessionLocal() as notif_db:
            if not await notification_enabled(notif_db, "receipt_recorded"):
                return
            po = await notif_db.get(PurchaseOrder, po_id)
            if po is None:
                return

            recipients: set[UUID] = set()
            if po.created_by_id:
                recipients.add(po.created_by_id)
            pr = await notif_db.get(PurchaseRequisition, po.pr_id)
            if pr and pr.requester_id:
                recipients.add(pr.requester_id)
            manager_rows = await notif_db.execute(
                select(User.id).where(
                    User.role == UserRole.PROCUREMENT_MGR.value,
                    User.is_active.is_(True),
                    User.company_id == po.company_id,
                )
            )
            recipients.update(manager_rows.scalars().all())
            # Whoever just performed the action does not need telling.
            recipients.discard(actor.id)
            if not recipients:
                return

            title = f"PO {po.po_number} {action}"
            body = (
                f"**PO**: {po.po_number}\n"
                f"**PR**: {po.pr_title or '—'}\n"
                f"{summary}\n"
                f"**By**: {actor.display_name}"
            )
            for user_id in sorted(recipients):
                await create_notification(
                    notif_db,
                    user_id=user_id,
                    category=NotificationCategory.RECEIPT_RECORDED,
                    title=title,
                    body=body,
                    link_url=f"/purchase-orders/{po_id}",
                    biz_type="purchase_order",
                    biz_id=po_id,
                )
            await notif_db.commit()
    except Exception:
        logger.warning("Failed to send receipt notification for po=%s", po_id, exc_info=True)


async def list_receipts(db: AsyncSession, po_id: UUID) -> list[Receipt]:
    rows = await db.execute(
        select(Receipt)
        .where(Receipt.po_id == po_id)
        .options(selectinload(Receipt.received_by))
        .order_by(Receipt.received_at.desc(), Receipt.created_at.desc())
    )
    return list(rows.scalars().all())


async def attach_payment_invoice(
    db: AsyncSession, actor: User, payment_id: UUID, invoice_id: UUID
) -> PaymentRecord:
    """Record the invoice that a 后票 payment was waiting for."""
    payment = await db.get(PaymentRecord, payment_id)
    if payment is None:
        raise HTTPException(404, "payment.not_found")
    invoice = await db.get(Invoice, invoice_id)
    if invoice is None:
        raise HTTPException(404, "invoice.not_found")

    payment.invoice_id = invoice_id
    # The debt is settled; the deadline only exists while the invoice is missing.
    payment.invoice_due_date = None
    if payment.invoice_timing is None:
        payment.invoice_timing = "postpaid"
    await _audit_write(
        db,
        actor,
        "payment.invoice_attached",
        "payment",
        str(payment_id),
        meta={"invoice_id": str(invoice_id)},
    )
    await db.flush()
    refreshed = await db.execute(select(PaymentRecord).where(PaymentRecord.id == payment_id))
    return refreshed.scalar_one()


async def create_receipts(
    db: AsyncSession,
    actor: User,
    po_id: UUID,
    items_in: list[dict],
    received_at: datetime | None = None,
    notes: str | None = None,
) -> list[Receipt]:
    """Record goods arriving against one or more PO lines.

    Deliberately separate from shipments: a supplier can ship everything at
    once while the goods are accepted in several passes, and the person who
    accepts them is usually the requester rather than the buyer.
    """
    po = await _load_po(db, po_id)
    if po is None:
        raise HTTPException(404, "po.not_found")
    if po.status in _RECEIPT_LOCKED_STATES:
        raise HTTPException(409, "receipt.po_not_receivable")

    when = received_at or datetime.now(UTC)
    po_item_map = {str(i.id): i for i in po.items}
    tolerance = await _receipt_tolerance(db)
    created: list[Receipt] = []
    total_qty = Decimal("0")

    for item_in in items_in:
        po_item = po_item_map.get(str(item_in["po_item_id"]))
        if po_item is None:
            raise HTTPException(422, "receipt.invalid_po_item")
        qty = _as_decimal(item_in["qty"])
        if qty <= 0:
            raise HTTPException(422, "receipt.invalid_qty")

        shipment_id = item_in.get("shipment_id")
        if shipment_id is not None:
            shipment = await db.get(Shipment, shipment_id)
            if shipment is None or shipment.po_id != po_id:
                raise HTTPException(422, "receipt.invalid_shipment")

        # qty_received is the running sum of receipts, including the earlier
        # lines of this very call, so the projection is exact.
        _assert_within_tolerance(po_item, _as_decimal(po_item.qty_received or 0) + qty, tolerance)

        receipt = Receipt(
            po_id=po_id,
            po_item_id=po_item.id,
            shipment_id=shipment_id,
            qty=qty,
            received_by_id=actor.id,
            received_at=when,
            notes=notes,
        )
        db.add(receipt)
        created.append(receipt)
        po_item.qty_received = _as_decimal(po_item.qty_received or 0) + qty
        total_qty += qty

    await db.flush()
    await recompute_po_receipt(db, po_id)
    await _audit_write(
        db,
        actor,
        "receipt.created",
        "purchase_order",
        str(po_id),
        meta={"lines": len(created), "qty": str(total_qty)},
    )
    await db.commit()

    await _notify_receipt_event(
        db,
        actor,
        po_id,
        action="goods received",
        summary=(
            f"**Lines**: {len(created)} | **Qty**: {total_qty}\n"
            f"**Received at**: {when.strftime('%Y-%m-%d %H:%M')}"
        ),
    )

    # Re-read with the relation loaded: serialising the ORM objects created
    # above would trigger a lazy load outside the async greenlet context.
    receipt_ids = [receipt.id for receipt in created]
    rows = await db.execute(
        select(Receipt)
        .where(Receipt.id.in_(receipt_ids))
        .options(selectinload(Receipt.received_by))
        .order_by(Receipt.created_at)
    )
    return list(rows.scalars().all())


async def delete_receipt(db: AsyncSession, actor: User, receipt_id: UUID) -> None:
    """Undo a receipt; the PO aggregates and status follow it back down."""
    receipt = await db.get(Receipt, receipt_id)
    if receipt is None:
        raise HTTPException(404, "receipt.not_found")
    if receipt.received_by_id != actor.id and actor.role not in _RECEIPT_MANAGER_ROLES:
        raise HTTPException(403, "insufficient_role")

    po_id = receipt.po_id
    qty_text = str(receipt.qty)
    await _audit_write(
        db,
        actor,
        "receipt.deleted",
        "purchase_order",
        str(po_id),
        meta={"receipt_id": str(receipt_id), "qty": qty_text},
    )
    await db.delete(receipt)
    await db.flush()
    await recompute_po_receipt(db, po_id)
    await db.commit()

    await _notify_receipt_event(
        db,
        actor,
        po_id,
        action="receipt revoked",
        summary=f"**Qty**: {qty_text}",
    )


async def _apply_shipment_item_quantities(
    db: AsyncSession, shipment: Shipment, rows: list
) -> dict[str, object]:
    """Apply edited shipped quantities.

    Only ``qty_shipped`` is editable here. Received quantities belong to
    ``receipts`` and are created or removed through their own endpoints, so a
    batch edit can no longer silently move the received total.
    """
    by_id = {str(i.id): i for i in shipment.items}
    changes: dict[str, object] = {}
    for row in rows:
        si = by_id.get(str(row.shipment_item_id))
        if si is None:
            raise HTTPException(422, "shipment.invalid_item")
        if row.qty_shipped is None:
            continue
        new_shipped = _as_decimal(row.qty_shipped)
        if new_shipped != si.qty_shipped:
            changes[f"{si.id}.qty_shipped"] = {
                "old": str(si.qty_shipped),
                "new": str(new_shipped),
            }
            si.qty_shipped = new_shipped

    if changes:
        await db.flush()
        await recompute_po_receipt(db, shipment.po_id)
    return changes


async def update_shipment(
    db: AsyncSession, actor: User, shipment_id: UUID, payload: object
) -> Shipment:
    from app.schemas import ShipmentUpdate

    # ``items`` is eager-loaded: editing quantities reads the collection, and a
    # lazy load would fire outside the async greenlet context (MissingGreenlet).
    shipment = (
        await db.execute(
            select(Shipment).where(Shipment.id == shipment_id).options(selectinload(Shipment.items))
        )
    ).scalar_one_or_none()
    if shipment is None:
        raise HTTPException(404, "shipment.not_found")
    assert isinstance(payload, ShipmentUpdate)
    changes: dict[str, object] = {}
    # ``items`` carries per-line quantities and is applied separately below; it
    # is not a scalar attribute of Shipment, so touching it through setattr
    # would assign over the relationship.
    for field_name in payload.model_fields_set - {"items"}:
        new_val = getattr(payload, field_name)
        old_val = getattr(shipment, field_name)
        if old_val != new_val:
            changes[field_name] = {"old": str(old_val), "new": str(new_val)}
            setattr(shipment, field_name, new_val)

    if payload.items:
        item_changes = await _apply_shipment_item_quantities(db, shipment, payload.items)
        if item_changes:
            changes["items"] = item_changes

    if changes:
        await _audit_write(db, actor, "shipment.updated", "shipment", str(shipment_id), changes)
        await db.commit()

        try:
            from app.db import AsyncSessionLocal
            from app.models import PurchaseOrder, User, UserRole
            from app.services.notifications import emit_event_notification, user_locale
            from app.services.system_params import notification_enabled

            async with AsyncSessionLocal() as notif_db:
                if await notification_enabled(notif_db, "shipment_updated"):
                    po = await notif_db.get(PurchaseOrder, shipment.po_id)
                    if po:
                        recipients = {actor.id, po.created_by_id}
                        if po.pr_id:
                            pr = await notif_db.get(PurchaseRequisition, po.pr_id)
                            if pr and pr.requester_id:
                                recipients.add(pr.requester_id)
                        admin_rows = (
                            (
                                await notif_db.execute(
                                    select(User.id).where(
                                        User.role.in_(
                                            [UserRole.ADMIN.value, UserRole.PROCUREMENT_MGR.value]
                                        ),
                                        User.is_active.is_(True),
                                    )
                                )
                            )
                            .scalars()
                            .all()
                        )
                        recipients.update(admin_rows)
                        for uid in recipients:
                            user = await notif_db.get(User, uid)
                            if user is None:
                                continue
                            locale = user_locale(user)
                            await emit_event_notification(
                                notif_db,
                                user_id=user.id,
                                event="shipment_updated",
                                title=t(
                                    "notification.event.shipment_updated",
                                    locale,
                                    shipment_number=shipment.shipment_number,
                                ),
                                link_url=f"/purchase-orders/{shipment.po_id}",
                                biz_type="shipment",
                                biz_id=shipment.id,
                                fields=[
                                    (
                                        t("notification.label.shipment", locale),
                                        shipment.shipment_number,
                                    ),
                                    (t("notification.label.po", locale), po.po_number),
                                    (t("notification.label.pr", locale), po.pr_title or "—"),
                                    (
                                        t("notification.label.carrier", locale),
                                        shipment.carrier or "—",
                                    ),
                                    (
                                        t("notification.label.tracking", locale),
                                        shipment.tracking_number or "—",
                                    ),
                                ],
                                changes=[
                                    (str(key), f"{value['old']} → {value['new']}")
                                    for key, value in changes.items()
                                ],
                                fingerprint_parts=(
                                    "updated",
                                    *[
                                        f"{key}={value['new']}"
                                        for key, value in sorted(changes.items())
                                    ],
                                ),
                            )
                        await notif_db.commit()
        except Exception:
            logger.warning(
                "Failed to send shipment_updated notification for shipment=%s",
                shipment.id,
                exc_info=True,
            )

    result = await db.execute(
        select(Shipment).where(Shipment.id == shipment_id).options(selectinload(Shipment.items))
    )
    return result.scalar_one()


async def delete_shipment(db: AsyncSession, actor: User, shipment_id: UUID) -> None:
    shipment = await db.get(Shipment, shipment_id)
    if shipment is None:
        raise HTTPException(404, "shipment.not_found")
    po_id = shipment.po_id
    await _audit_write(
        db,
        actor,
        "shipment.deleted",
        "shipment",
        str(shipment_id),
        {"shipment_number": shipment.shipment_number},
    )
    await db.delete(shipment)
    await db.flush()
    # A deleted batch must also give back the quantities it contributed,
    # otherwise the PO keeps counting a shipment that no longer exists — the
    # delete-then-recreate flow used to end up at 200% received.
    await recompute_po_receipt(db, po_id)
    await db.commit()


async def attach_document_to_shipment(
    db: AsyncSession, actor: User, shipment_id: UUID, document_id: UUID, role: str = "attachment"
) -> ShipmentDocument:
    shipment = await db.get(Shipment, shipment_id)
    if shipment is None:
        raise HTTPException(404, "shipment.not_found")
    doc = await db.get(Document, document_id)
    if doc is None:
        raise HTTPException(404, "document.not_found")
    link = ShipmentDocument(
        shipment_id=shipment_id,
        document_id=document_id,
        role=role,
    )
    db.add(link)
    await _audit_write(
        db,
        actor,
        "shipment.document.attached",
        "shipment",
        str(shipment_id),
        {"document_id": str(document_id), "filename": doc.original_filename},
    )
    await db.commit()
    return link


async def list_shipment_documents(db: AsyncSession, shipment_id: UUID) -> list[dict]:
    stmt = (
        select(ShipmentDocument, Document)
        .join(Document, ShipmentDocument.document_id == Document.id)
        .where(ShipmentDocument.shipment_id == shipment_id)
        .order_by(ShipmentDocument.display_order)
    )
    rows = (await db.execute(stmt)).all()
    return [
        {
            "document_id": str(sd.document_id),
            "role": sd.role,
            "original_filename": d.original_filename,
            "content_type": d.content_type,
            "file_size": d.file_size,
            "created_at": sd.created_at.isoformat() if sd.created_at else None,
        }
        for sd, d in rows
    ]


async def remove_shipment_document(db: AsyncSession, shipment_id: UUID, document_id: UUID) -> None:
    link = await db.get(ShipmentDocument, (shipment_id, document_id))
    if link is None:
        raise HTTPException(404, "shipment_document.not_found")
    await db.delete(link)
    await db.commit()


async def attach_po_document(
    db: AsyncSession, actor: User, po_id: UUID, document_id: UUID, role: str = "attachment"
) -> PODocument:
    po = await db.get(PurchaseOrder, po_id)
    if po is None:
        raise HTTPException(404, "purchase_order.not_found")
    doc = await db.get(Document, document_id)
    if doc is None:
        raise HTTPException(404, "document.not_found")
    link = PODocument(
        po_id=po_id,
        document_id=document_id,
        role=role,
    )
    db.add(link)
    await _audit_write(
        db,
        actor,
        "po.document.attached",
        "purchase_order",
        str(po_id),
        {"document_id": str(document_id), "filename": doc.original_filename},
    )
    await db.commit()
    return link


async def list_po_documents(db: AsyncSession, po_id: UUID) -> list[dict]:
    stmt = (
        select(PODocument, Document)
        .join(Document, PODocument.document_id == Document.id)
        .where(PODocument.po_id == po_id)
        .order_by(PODocument.display_order)
    )
    rows = (await db.execute(stmt)).all()
    return [
        {
            "document_id": str(pd.document_id),
            "role": pd.role,
            "original_filename": d.original_filename,
            "content_type": d.content_type,
            "file_size": d.file_size,
            "created_at": pd.created_at.isoformat() if pd.created_at else None,
        }
        for pd, d in rows
    ]


async def remove_po_document(db: AsyncSession, po_id: UUID, document_id: UUID) -> None:
    link = await db.get(PODocument, (po_id, document_id))
    if link is None:
        raise HTTPException(404, "po_document.not_found")
    await db.delete(link)
    await db.commit()


async def record_serial_numbers(
    db: AsyncSession,
    actor: User,
    shipment_item_id: UUID,
    serials: list[dict],
) -> list[SerialNumberEntry]:
    entries = []
    for s in serials:
        entry = SerialNumberEntry(
            shipment_item_id=shipment_item_id,
            serial_number=s["serial_number"],
            manufacturer=s.get("manufacturer"),
            model_number=s.get("model_number"),
            warranty_expiry=s.get("warranty_expiry"),
        )
        db.add(entry)
        entries.append(entry)
    await _audit_write(
        db,
        actor,
        "serials.recorded",
        "shipment_item",
        str(shipment_item_id),
        meta={"count": len(entries)},
    )
    await db.commit()
    for e in entries:
        await db.refresh(e)
    return entries


async def create_payment(
    db: AsyncSession,
    actor: User,
    po_id: UUID,
    amount: Decimal,
    contract_id: UUID,
    schedule_item_id: UUID | None = None,
    due_date=None,
    payment_date=None,
    payment_method: str = "bank_transfer",
    transaction_ref: str | None = None,
    notes: str | None = None,
) -> PaymentRecord:
    po = await _load_po(db, po_id)
    if po is None:
        raise HTTPException(404, "po.not_found")

    contract = (
        await db.execute(select(Contract).where(Contract.id == contract_id))
    ).scalar_one_or_none()
    if contract is None:
        raise HTTPException(404, "contract.not_found")
    if contract.po_id != po_id:
        link_exists = (
            await db.execute(
                select(func.count(POContractLink.po_id)).where(
                    POContractLink.po_id == po_id,
                    POContractLink.contract_id == contract_id,
                )
            )
        ).scalar_one()
        if not link_exists:
            raise HTTPException(409, "payment.contract_po_mismatch")

    if schedule_item_id is not None:
        schedule_item = (
            await db.execute(select(PaymentSchedule).where(PaymentSchedule.id == schedule_item_id))
        ).scalar_one_or_none()
        if schedule_item is None:
            raise HTTPException(404, "schedule_item.not_found")
        if schedule_item.contract_id is not None and contract.po_id != po_id:
            raise HTTPException(409, "payment.schedule_requires_primary_po")
        if schedule_item.contract_id != contract_id and schedule_item.po_id != po_id:
            raise HTTPException(409, "payment.schedule_parent_mismatch")

    existing_count = (
        await db.execute(select(func.count(PaymentRecord.id)).where(PaymentRecord.po_id == po_id))
    ).scalar_one() or 0
    installment_no = existing_count + 1
    payment_number = f"{po.po_number}-P{installment_no:02d}"

    status = PaymentStatus.CONFIRMED.value if payment_date else PaymentStatus.PENDING.value
    record = PaymentRecord(
        payment_number=payment_number,
        po_id=po_id,
        contract_id=contract_id,
        schedule_item_id=schedule_item_id,
        installment_no=installment_no,
        amount=_as_decimal(amount),
        currency=po.currency,
        due_date=due_date,
        payment_date=payment_date,
        payment_method=payment_method,
        transaction_ref=transaction_ref,
        status=status,
        notes=notes,
    )
    db.add(record)
    await db.flush()

    if status == PaymentStatus.CONFIRMED.value:
        po.amount_paid = (po.amount_paid or Decimal("0")) + _as_decimal(amount)

    if schedule_item_id is not None and status == PaymentStatus.CONFIRMED.value:
        schedule_item = await db.get(PaymentSchedule, schedule_item_id)
        if schedule_item is not None and schedule_item.status != ScheduleItemStatus.PAID.value:
            schedule_item.actual_amount = _as_decimal(amount)
            schedule_item.actual_date = payment_date
            schedule_item.payment_record_id = record.id
            schedule_item.status = ScheduleItemStatus.PAID.value

    await _audit_write(
        db,
        actor,
        "payment.created",
        "payment_record",
        str(record.id) or "",
        meta={
            "po_id": str(po_id),
            "contract_id": str(contract_id),
            "schedule_item_id": str(schedule_item_id) if schedule_item_id else None,
            "amount": str(amount),
            "status": status,
        },
    )
    await db.commit()

    try:
        from app.db import AsyncSessionLocal
        from app.models import User, UserRole
        from app.services.notifications import emit_event_notification, status_label, user_locale
        from app.services.system_params import notification_enabled

        async with AsyncSessionLocal() as notif_db:
            if await notification_enabled(notif_db, "payment_created"):
                recipients: set[UUID] = {actor.id}
                pr = await notif_db.get(PurchaseRequisition, po.pr_id)
                if pr and pr.requester_id:
                    recipients.add(pr.requester_id)
                admin_rows = (
                    (
                        await notif_db.execute(
                            select(User.id).where(
                                User.role.in_(
                                    [UserRole.ADMIN.value, UserRole.FINANCE_AUDITOR.value]
                                ),
                                User.is_active.is_(True),
                            )
                        )
                    )
                    .scalars()
                    .all()
                )
                recipients.update(admin_rows)
                for uid in recipients:
                    user = await notif_db.get(User, uid)
                    if user is None:
                        continue
                    locale = user_locale(user)
                    await emit_event_notification(
                        notif_db,
                        user_id=user.id,
                        event="payment_created",
                        title=t(
                            "notification.event.payment_created",
                            locale,
                            payment_number=record.payment_number,
                        ),
                        link_url=f"/purchase-orders/{record.po_id}",
                        biz_type="payment",
                        biz_id=record.id,
                        fields=[
                            (
                                t("notification.label.payment", locale),
                                record.payment_number,
                            ),
                            (
                                t("notification.label.installment", locale),
                                f"#{record.installment_no}",
                            ),
                            (t("notification.label.po", locale), po.po_number),
                            (t("notification.label.pr", locale), po.pr_title or "—"),
                            (
                                t("notification.label.amount", locale),
                                fmt_amount(record.amount, record.currency),
                            ),
                            (
                                t("notification.label.due_date", locale),
                                fmt_date(record.due_date, locale),
                            ),
                            (
                                t("notification.label.status", locale),
                                status_label(record.status, locale),
                            ),
                            (
                                t("notification.label.method", locale),
                                str(record.payment_method or "—"),
                            ),
                            (
                                t("notification.label.created_by", locale),
                                actor.display_name,
                            ),
                        ],
                        fingerprint_parts=("created", record.payment_number),
                    )
                await notif_db.commit()
    except Exception:
        logger.warning(
            "Failed to send payment_created notification for payment=%s", record.id, exc_info=True
        )

    await db.refresh(record)
    return record


async def update_payment(
    db: AsyncSession,
    actor: User,
    payment_id: UUID,
    updates: dict,
) -> PaymentRecord:
    record = (
        await db.execute(select(PaymentRecord).where(PaymentRecord.id == payment_id))
    ).scalar_one_or_none()
    if record is None:
        raise HTTPException(404, "payment.not_found")

    changes: dict[str, object] = {}

    new_contract_id = record.contract_id
    if "contract_id" in updates:
        candidate = updates["contract_id"]
        if candidate is None:
            raise HTTPException(400, "payment.contract_required")
        if candidate != record.contract_id:
            contract = (
                await db.execute(select(Contract).where(Contract.id == candidate))
            ).scalar_one_or_none()
            if contract is None:
                raise HTTPException(404, "contract.not_found")
            if contract.po_id != record.po_id:
                link_exists = (
                    await db.execute(
                        select(func.count(POContractLink.po_id)).where(
                            POContractLink.po_id == record.po_id,
                            POContractLink.contract_id == candidate,
                        )
                    )
                ).scalar_one()
                if not link_exists:
                    raise HTTPException(409, "payment.contract_po_mismatch")
            changes["contract_id"] = {
                "from": str(record.contract_id) if record.contract_id else None,
                "to": str(candidate),
            }
            record.contract_id = candidate
            new_contract_id = candidate

    if "schedule_item_id" in updates:
        candidate = updates["schedule_item_id"]
        if candidate != record.schedule_item_id:
            if record.schedule_item_id is not None:
                old_item = await db.get(PaymentSchedule, record.schedule_item_id)
                if old_item is not None and old_item.payment_record_id == record.id:
                    old_item.payment_record_id = None
                    old_item.actual_amount = None
                    old_item.actual_date = None
                    old_item.status = ScheduleItemStatus.PLANNED.value

            if candidate is not None:
                new_item = (
                    await db.execute(select(PaymentSchedule).where(PaymentSchedule.id == candidate))
                ).scalar_one_or_none()
                if new_item is None:
                    raise HTTPException(404, "schedule_item.not_found")
                if new_item.contract_id is not None:
                    contract = (
                        await db.execute(select(Contract).where(Contract.id == new_contract_id))
                    ).scalar_one_or_none()
                    if contract is None:
                        raise HTTPException(404, "contract.not_found")
                    if contract.po_id != record.po_id:
                        raise HTTPException(409, "payment.schedule_requires_primary_po")
                if new_item.contract_id != new_contract_id and new_item.po_id != record.po_id:
                    raise HTTPException(409, "payment.schedule_parent_mismatch")
                if record.status == PaymentStatus.CONFIRMED.value:
                    new_item.actual_amount = record.amount
                    new_item.actual_date = record.payment_date
                    new_item.payment_record_id = record.id
                    new_item.status = ScheduleItemStatus.PAID.value

            changes["schedule_item_id"] = {
                "from": str(record.schedule_item_id) if record.schedule_item_id else None,
                "to": str(candidate) if candidate else None,
            }
            record.schedule_item_id = candidate

    if "amount" in updates and updates["amount"] is not None:
        new = _as_decimal(updates["amount"])
        if new != record.amount:
            old = record.amount
            if record.status == PaymentStatus.CONFIRMED.value:
                po = await _load_po(db, record.po_id)
                if po is not None:
                    po.amount_paid = (po.amount_paid or Decimal("0")) - old + new
                if record.schedule_item_id is not None:
                    schedule_item = await db.get(PaymentSchedule, record.schedule_item_id)
                    if schedule_item is not None:
                        schedule_item.actual_amount = new
            record.amount = new
            changes["amount"] = {"from": str(old), "to": str(new)}

    if "due_date" in updates and updates["due_date"] != record.due_date:
        changes["due_date"] = {"from": str(record.due_date), "to": str(updates["due_date"])}
        record.due_date = updates["due_date"]

    if "payment_date" in updates and updates["payment_date"] != record.payment_date:
        new_payment_date = updates["payment_date"]
        changes["payment_date"] = {
            "from": str(record.payment_date),
            "to": str(new_payment_date),
        }
        record.payment_date = new_payment_date
        if record.schedule_item_id is not None:
            schedule_item = await db.get(PaymentSchedule, record.schedule_item_id)
            if schedule_item is not None:
                schedule_item.actual_date = new_payment_date

    if "payment_method" in updates and updates["payment_method"] != record.payment_method:
        changes["payment_method"] = {
            "from": record.payment_method,
            "to": updates["payment_method"],
        }
        record.payment_method = updates["payment_method"]

    if "transaction_ref" in updates and updates["transaction_ref"] != record.transaction_ref:
        changes["transaction_ref"] = {
            "from": record.transaction_ref,
            "to": updates["transaction_ref"],
        }
        record.transaction_ref = updates["transaction_ref"]

    if "notes" in updates and updates["notes"] != record.notes:
        changes["notes"] = {"from": record.notes, "to": updates["notes"]}
        record.notes = updates["notes"]

    if not changes:
        return record

    await _audit_write(
        db,
        actor,
        "payment.updated",
        "payment_record",
        str(record.id),
        meta={"changes": changes},
    )
    await db.commit()
    await db.refresh(record)

    try:
        from app.db import AsyncSessionLocal
        from app.models import PurchaseOrder, User, UserRole
        from app.services.notifications import emit_event_notification, user_locale
        from app.services.system_params import notification_enabled

        async with AsyncSessionLocal() as notif_db:
            if await notification_enabled(notif_db, "payment_updated"):
                po = await notif_db.get(PurchaseOrder, record.po_id)
                if po:
                    recipients = {actor.id, po.created_by_id}
                    if po.pr_id:
                        pr = await notif_db.get(PurchaseRequisition, po.pr_id)
                        if pr and pr.requester_id:
                            recipients.add(pr.requester_id)
                    admin_rows = (
                        (
                            await notif_db.execute(
                                select(User.id).where(
                                    User.role.in_(
                                        [UserRole.ADMIN.value, UserRole.FINANCE_AUDITOR.value]
                                    ),
                                    User.is_active.is_(True),
                                )
                            )
                        )
                        .scalars()
                        .all()
                    )
                    recipients.update(admin_rows)
                    for uid in recipients:
                        user = await notif_db.get(User, uid)
                        if user is None:
                            continue
                        locale = user_locale(user)
                        await emit_event_notification(
                            notif_db,
                            user_id=user.id,
                            event="payment_updated",
                            title=t(
                                "notification.event.payment_updated",
                                locale,
                                payment_number=record.payment_number,
                            ),
                            link_url=f"/purchase-orders/{record.po_id}",
                            biz_type="payment",
                            biz_id=record.id,
                            fields=[
                                (
                                    t("notification.label.payment", locale),
                                    record.payment_number,
                                ),
                                (t("notification.label.po", locale), po.po_number),
                                (t("notification.label.pr", locale), po.pr_title or "—"),
                                (
                                    t("notification.label.amount", locale),
                                    fmt_amount(record.amount, record.currency),
                                ),
                            ],
                            changes=[
                                (str(key), f"{value['from']} → {value['to']}")
                                for key, value in changes.items()
                            ],
                            fingerprint_parts=(
                                "updated",
                                *[f"{key}={value['to']}" for key, value in sorted(changes.items())],
                            ),
                        )
                    await notif_db.commit()
    except Exception:
        logger.warning(
            "Failed to send payment_updated notification for payment=%s", record.id, exc_info=True
        )

    return record


async def delete_payment(db: AsyncSession, actor: User, payment_id: UUID) -> None:
    record = (
        await db.execute(select(PaymentRecord).where(PaymentRecord.id == payment_id))
    ).scalar_one_or_none()
    if record is None:
        raise HTTPException(404, "payment.not_found")

    was_confirmed = record.status == PaymentStatus.CONFIRMED.value
    if was_confirmed and actor.role not in _PAYMENT_WRITE_ROLES:
        raise HTTPException(409, "payment.cannot_delete_confirmed")

    if record.schedule_item_id is not None:
        schedule_item = await db.get(PaymentSchedule, record.schedule_item_id)
        if schedule_item is not None and schedule_item.payment_record_id == record.id:
            schedule_item.payment_record_id = None
            schedule_item.actual_amount = None
            schedule_item.actual_date = None
            schedule_item.status = ScheduleItemStatus.PLANNED.value

    payment_number = record.payment_number
    po_id = record.po_id
    await db.delete(record)
    await db.flush()

    if was_confirmed:
        amount_paid = (
            await db.execute(
                select(func.coalesce(func.sum(PaymentRecord.amount), 0)).where(
                    PaymentRecord.po_id == po_id,
                    PaymentRecord.status == PaymentStatus.CONFIRMED.value,
                )
            )
        ).scalar_one()
        po = await _load_po(db, po_id)
        if po:
            po.amount_paid = Decimal(str(amount_paid))

    await _audit_write(
        db,
        actor,
        "payment.deleted",
        "payment_record",
        str(payment_id),
        meta={"payment_number": payment_number, "was_confirmed": was_confirmed},
    )
    await db.commit()


async def confirm_payment(
    db: AsyncSession,
    actor: User,
    payment_id: UUID,
    payment_date=None,
    transaction_ref: str | None = None,
) -> PaymentRecord:
    record = (
        await db.execute(select(PaymentRecord).where(PaymentRecord.id == payment_id))
    ).scalar_one_or_none()
    if record is None:
        raise HTTPException(404, "payment.not_found")
    if record.status == PaymentStatus.CONFIRMED.value:
        return record
    record.status = PaymentStatus.CONFIRMED.value
    record.payment_date = payment_date or datetime.now(UTC).date()
    if transaction_ref:
        record.transaction_ref = transaction_ref
    po = await _load_po(db, record.po_id)
    if po:
        po.amount_paid = (po.amount_paid or Decimal("0")) + record.amount
    await _audit_write(db, actor, "payment.confirmed", "payment_record", str(record.id))
    await db.commit()
    await db.refresh(record)
    return record


async def list_payments(
    db: AsyncSession,
    po_id: UUID | None = None,
    actor: User | None = None,
) -> list[PaymentRecord]:
    stmt = select(PaymentRecord).order_by(PaymentRecord.created_at.desc())
    if po_id:
        stmt = stmt.where(PaymentRecord.po_id == po_id)
    if actor is not None:
        from app.core.scoping import visible_po_id_subquery

        visible_po_ids = await visible_po_id_subquery(db, actor)
        if visible_po_ids is not None:
            stmt = stmt.where(PaymentRecord.po_id.in_(visible_po_ids))
    return list((await db.execute(stmt)).scalars().all())


async def create_invoice(
    db: AsyncSession,
    actor: User,
    supplier_id: UUID,
    invoice_number: str,
    invoice_date,
    lines_in: list[dict],
    tax_number: str | None = None,
    due_date=None,
    notes: str | None = None,
    attachment_document_ids: list[UUID] | None = None,
) -> tuple[Invoice, list[dict]]:
    if not attachment_document_ids:
        raise HTTPException(422, "invoice.attachments_required")

    attach_rows = (
        (await db.execute(select(Document).where(Document.id.in_(attachment_document_ids))))
        .scalars()
        .all()
    )
    if len(attach_rows) != len(set(attachment_document_ids)):
        raise HTTPException(404, "invoice.attachment_document_not_found")

    supplier = (
        await db.execute(select(Supplier).where(Supplier.id == supplier_id))
    ).scalar_one_or_none()
    if supplier is None:
        raise HTTPException(404, "supplier.not_found")

    existing = (
        await db.execute(
            select(Invoice.id).where(
                Invoice.supplier_id == supplier_id,
                Invoice.invoice_number == invoice_number.strip(),
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(409, "invoice.number_duplicate")

    from app.services.system_params import system_params

    now = datetime.now(UTC)
    raw_prefix = await system_params.get(db, "bill.number_prefix", "")
    if isinstance(raw_prefix, str) and raw_prefix.strip():
        prefix = raw_prefix.strip()
    else:
        prefix = "INV"
    date_str = f"{now.year:04d}{now.month:02d}{now.day:02d}"
    full_prefix = f"{prefix}{date_str}"
    max_suffix = (
        await db.execute(
            select(func.max(Invoice.internal_number)).where(
                Invoice.internal_number.like(f"{full_prefix}%")
            )
        )
    ).scalar_one_or_none()
    next_seq = 1
    if max_suffix and len(max_suffix) == len(full_prefix) + 3:
        try:
            next_seq = int(max_suffix[-3:]) + 1
        except ValueError:
            next_seq = 1
    internal_number = f"{full_prefix}{next_seq:03d}"

    po_item_ids = {line.get("po_item_id") for line in lines_in if line.get("po_item_id")}
    po_items_map: dict[str, POItem] = {}
    currency = "CNY"
    if po_item_ids:
        po_items = (
            (await db.execute(select(POItem).where(POItem.id.in_(po_item_ids)))).scalars().all()
        )
        po_items_map = {str(i.id): i for i in po_items}
        if po_items:
            first_po = (
                await db.execute(select(PurchaseOrder).where(PurchaseOrder.id == po_items[0].po_id))
            ).scalar_one_or_none()
            if first_po:
                currency = first_po.currency

    subtotal = Decimal("0")
    total_tax = Decimal("0")
    validations: list[dict] = []
    touched_po_ids: set[UUID] = set()

    for idx, line_in in enumerate(lines_in, start=1):
        qty = _as_decimal(line_in["qty"])
        unit_price = _as_decimal(line_in["unit_price"])
        line_subtotal = (qty * unit_price).quantize(Decimal("0.0001"))
        line_tax = _as_decimal(line_in.get("tax_amount", 0)).quantize(Decimal("0.0001"))
        subtotal += line_subtotal
        total_tax += line_tax
        line_type = line_in.get("line_type", "product")

        po_item_id = line_in.get("po_item_id")
        po_item = po_items_map.get(str(po_item_id)) if po_item_id else None

        validation = {
            "line_no": idx,
            "po_item_id": po_item_id,
            "invoiced_subtotal": line_subtotal,
            "po_remaining": None,
            "overage": Decimal("0"),
            "severity": "ok",
            "message": None,
        }
        if line_type == "product" and po_item:
            po_line_subtotal = (po_item.qty * po_item.unit_price).quantize(Decimal("0.0001"))
            already_invoiced = (po_item.qty_invoiced or Decimal("0")) * po_item.unit_price
            po_remaining = po_line_subtotal - already_invoiced
            validation["po_remaining"] = po_remaining
            overage = line_subtotal - po_remaining
            if overage > Decimal("0.01"):
                validation["overage"] = overage
                validation["severity"] = "warn"
                validation["message"] = "exceeds_po_remaining"
        elif line_type == "product" and po_item_id is None:
            validation["severity"] = "warn"
            validation["message"] = "product_line_without_po_item"
        validations.append(validation)

    total = subtotal + total_tax

    is_matched = all(
        v["severity"] == "ok"
        for v in validations
        if v.get("po_item_id")
        or lines_in[v["line_no"] - 1].get("line_type", "product") == "product"
    )
    initial_status = (
        InvoiceStatus.MATCHED.value if is_matched else InvoiceStatus.PENDING_MATCH.value
    )

    invoice = Invoice(
        internal_number=internal_number,
        invoice_number=invoice_number,
        supplier_id=supplier_id,
        invoice_date=invoice_date,
        due_date=due_date,
        subtotal=subtotal,
        tax_amount=total_tax,
        total_amount=total,
        currency=currency,
        tax_number=tax_number,
        status=initial_status,
        notes=notes,
        is_fully_matched=is_matched,
    )
    db.add(invoice)
    await db.flush()

    for idx, line_in in enumerate(lines_in, start=1):
        qty = _as_decimal(line_in["qty"])
        unit_price = _as_decimal(line_in["unit_price"])
        line_subtotal = (qty * unit_price).quantize(Decimal("0.0001"))
        line_tax = _as_decimal(line_in.get("tax_amount", 0)).quantize(Decimal("0.0001"))
        po_item_id = line_in.get("po_item_id")
        po_item = po_items_map.get(str(po_item_id)) if po_item_id else None
        line_type = line_in.get("line_type", "product")

        db.add(
            InvoiceLine(
                invoice_id=invoice.id,
                po_item_id=po_item.id if po_item else None,
                line_type=line_type,
                line_no=idx,
                item_name=line_in["item_name"],
                qty=qty,
                unit_price=unit_price,
                subtotal=line_subtotal,
                tax_amount=line_tax,
            )
        )

        if po_item and line_type == "product":
            po_item.qty_invoiced = (po_item.qty_invoiced or Decimal("0")) + qty
            touched_po_ids.add(po_item.po_id)

    for idx, doc_id in enumerate(attachment_document_ids):
        db.add(
            InvoiceDocument(
                invoice_id=invoice.id,
                document_id=doc_id,
                role="original" if idx == 0 else "attachment",
                display_order=idx,
            )
        )

    for po_id in touched_po_ids:
        po = (
            await db.execute(
                select(PurchaseOrder)
                .where(PurchaseOrder.id == po_id)
                .options(selectinload(PurchaseOrder.items))
            )
        ).scalar_one()
        po.amount_invoiced = sum(
            ((i.qty_invoiced or Decimal("0")) * i.unit_price for i in po.items),
            start=Decimal("0"),
        ).quantize(Decimal("0.0001"))

    await _audit_write(
        db,
        actor,
        "invoice.created",
        "invoice",
        str(invoice.id),
        meta={
            "internal_number": internal_number,
            "subtotal": str(subtotal),
            "tax": str(total_tax),
            "total": str(total),
            "po_ids": [str(p) for p in touched_po_ids],
        },
    )
    await db.commit()

    try:
        from app.models import User, UserRole
        from app.services.notifications import emit_event_notification, user_locale
        from app.services.system_params import notification_enabled

        if await notification_enabled(db, "invoice_created"):
            recipients = {actor.id}
            # Add PR requesters from all touched POs
            if touched_po_ids:
                po_rows = (
                    (
                        await db.execute(
                            select(PurchaseOrder.pr_id).where(PurchaseOrder.id.in_(touched_po_ids))
                        )
                    )
                    .scalars()
                    .all()
                )
                pr_ids = {pid for pid in po_rows if pid}
                if pr_ids:
                    pr_rows = (
                        await db.execute(
                            select(PurchaseRequisition.id, PurchaseRequisition.requester_id).where(
                                PurchaseRequisition.id.in_(pr_ids)
                            )
                        )
                    ).all()
                    for _pr_id, req_id in pr_rows:
                        if req_id:
                            recipients.add(req_id)
            admin_rows = (
                (
                    await db.execute(
                        select(User.id).where(
                            User.role.in_([UserRole.ADMIN.value, UserRole.FINANCE_AUDITOR.value]),
                            User.is_active.is_(True),
                        )
                    )
                )
                .scalars()
                .all()
            )
            recipients.update(admin_rows)
            po_hint = ""
            if touched_po_ids:
                po_hint = (
                    await db.execute(
                        select(PurchaseOrder.po_number)
                        .where(PurchaseOrder.id.in_(touched_po_ids))
                        .limit(1)
                    )
                ).scalar_one_or_none() or ""

            for uid in recipients:
                user = await db.get(User, uid)
                if user is None:
                    continue
                locale = user_locale(user)
                tax_note = (
                    t(
                        "feishu.card.invoice.tax",
                        locale,
                        amount=fmt_amount(invoice.tax_amount, invoice.currency),
                    )
                    if invoice.tax_amount
                    else ""
                )
                await emit_event_notification(
                    db,
                    user_id=user.id,
                    event="invoice_created",
                    title=t(
                        "feishu.card.headline.invoice_created"
                        if is_matched
                        else "feishu.card.headline.invoice_needs_review",
                        locale,
                        number=invoice.internal_number,
                    ),
                    link_url="/invoices",
                    biz_type="invoice",
                    biz_id=invoice.id,
                    status="success" if is_matched else "warning",
                    fingerprint_parts=("created", invoice.internal_number, is_matched),
                    meta={
                        "kind": "invoice",
                        "invoice_number": invoice.internal_number,
                        "vendor_number": invoice.invoice_number or "",
                        "supplier": supplier.name,
                        "total_amount": str(invoice.total_amount),
                        "currency": invoice.currency,
                        "invoice_date": invoice.invoice_date.isoformat()
                        if invoice.invoice_date
                        else None,
                        "tax_note": tax_note,
                        "matched": is_matched,
                        "po_hint": po_hint,
                        "created_by": actor.display_name,
                    },
                )
            await db.commit()
    except Exception:
        logger.warning(
            "Failed to send invoice_created notification for invoice=%s", invoice.id, exc_info=True
        )

    # Creation already carries the 3-way match result, so there is no separate
    # "invoice matched" card: two cards for one invoice was the noise.

    loaded = (
        await db.execute(
            select(Invoice)
            .where(Invoice.id == invoice.id)
            .options(
                selectinload(Invoice.lines),
                selectinload(Invoice.attachments).selectinload(InvoiceDocument.document),
            )
        )
    ).scalar_one()
    return loaded, validations


async def list_invoices(
    db: AsyncSession,
    po_item_ids: list[UUID] | None = None,
    actor: User | None = None,
) -> list[Invoice]:
    stmt = select(Invoice).order_by(Invoice.created_at.desc())
    if po_item_ids:
        sub = select(InvoiceLine.invoice_id).where(InvoiceLine.po_item_id.in_(po_item_ids))
        stmt = stmt.where(Invoice.id.in_(sub))
    if actor is not None:
        from app.core.scoping import visible_po_id_subquery

        visible_po_ids = await visible_po_id_subquery(db, actor)
        if visible_po_ids is not None:
            visible_po_item_ids = select(POItem.id).where(POItem.po_id.in_(visible_po_ids))
            sub = select(InvoiceLine.invoice_id).where(
                InvoiceLine.po_item_id.in_(visible_po_item_ids)
            )
            stmt = stmt.where(Invoice.id.in_(sub))
    return list((await db.execute(stmt)).scalars().all())


async def update_invoice(
    db: AsyncSession,
    actor: User,
    invoice_id: UUID,
    updates: dict,
) -> Invoice:
    """Correct the identifying fields of a recorded invoice.

    Amounts and lines are not in scope: they drive the PO matching a payment already
    relied on. What people actually get wrong is the date — the form used to default to
    today and nothing could change it afterwards.
    """
    invoice = await db.get(Invoice, invoice_id)
    if invoice is None:
        raise HTTPException(404, "invoice.not_found")

    allowed = {"invoice_date", "invoice_number", "tax_number", "due_date", "notes"}
    unknown = set(updates) - allowed
    if unknown:
        raise HTTPException(422, f"invoice.field_not_editable: {sorted(unknown)}")

    new_number = updates.get("invoice_number")
    if new_number and new_number != invoice.invoice_number:
        taken = (
            await db.execute(
                select(func.count(Invoice.id)).where(
                    Invoice.supplier_id == invoice.supplier_id,
                    Invoice.invoice_number == new_number,
                    Invoice.id != invoice.id,
                )
            )
        ).scalar_one() or 0
        if taken:
            raise HTTPException(409, "invoice.number_duplicate")

    changed: dict[str, object] = {}
    for field, value in updates.items():
        if value is None:
            continue
        if getattr(invoice, field) != value:
            changed[field] = str(getattr(invoice, field))
            setattr(invoice, field, value)

    if not changed:
        return invoice

    await _audit_write(
        db,
        actor,
        "invoice.updated",
        "invoice",
        str(invoice.id),
        meta={"before": changed, "after": {k: str(updates[k]) for k in changed}},
    )
    await db.commit()
    await db.refresh(invoice)
    return invoice


async def list_invoices_for_po(db: AsyncSession, po_id: UUID) -> list[Invoice]:
    po = await _load_po(db, po_id)
    if po is None:
        return []
    item_ids = [i.id for i in po.items]
    if not item_ids:
        return []
    return await list_invoices(db, item_ids)


async def po_progress(db: AsyncSession, po_id: UUID) -> dict:
    po = await _load_po(db, po_id)
    if po is None:
        raise HTTPException(404, "po.not_found")
    total_qty = sum((i.qty for i in po.items), start=Decimal("0"))
    qty_received = sum((i.qty_received or Decimal("0") for i in po.items), start=Decimal("0"))
    qty_invoiced = sum((i.qty_invoiced or Decimal("0") for i in po.items), start=Decimal("0"))
    amount_invoiced_subtotal = sum(
        ((i.qty_invoiced or Decimal("0")) * i.unit_price for i in po.items),
        start=Decimal("0"),
    )

    def pct(n: Decimal, d: Decimal) -> float:
        return float((n / d * Decimal("100")).quantize(Decimal("0.01"))) if d > 0 else 0.0

    return {
        "po_id": str(po.id),
        "po_number": po.po_number,
        "total_amount": str(po.total_amount),
        "amount_paid": str(po.amount_paid),
        "amount_invoiced": str(amount_invoiced_subtotal),
        "total_qty": str(total_qty),
        "qty_received": str(qty_received),
        "qty_invoiced": str(qty_invoiced),
        "pct_received": pct(qty_received, total_qty),
        "pct_invoiced": pct(amount_invoiced_subtotal, po.total_amount),
        "pct_paid": pct(po.amount_paid, po.total_amount),
    }


async def delete_invoice(db: AsyncSession, actor: User, invoice_id: UUID) -> None:
    inv = await db.get(Invoice, invoice_id)
    if inv is None:
        raise HTTPException(404, "invoice.not_found")
    await _audit_write(
        db,
        actor,
        "invoice.deleted",
        "invoice",
        str(invoice_id),
        {
            "invoice_number": inv.invoice_number,
            "total_amount": str(inv.total_amount),
        },
    )
    await db.delete(inv)
    await db.commit()


async def match_invoice_line(
    db: AsyncSession,
    actor: User,
    invoice_id: UUID,
    line_id: UUID,
    po_item_id: UUID | None,
) -> InvoiceLine:
    from sqlalchemy.orm import selectinload

    inv = (
        await db.execute(
            select(Invoice).where(Invoice.id == invoice_id).options(selectinload(Invoice.lines))
        )
    ).scalar_one_or_none()
    if inv is None:
        raise HTTPException(404, "invoice.not_found")

    line = next((ln for ln in inv.lines if ln.id == line_id), None)
    if line is None:
        raise HTTPException(404, "invoice.line_not_found")

    old_po_item_id = line.po_item_id

    if po_item_id is not None:
        new_po_item = await db.get(POItem, po_item_id)
        if new_po_item is None:
            raise HTTPException(404, "po_item.not_found")

    if old_po_item_id and old_po_item_id != po_item_id:
        old_po_item = await db.get(POItem, old_po_item_id)
        if old_po_item:
            old_po_item.qty_invoiced = max(
                Decimal("0"), (old_po_item.qty_invoiced or Decimal("0")) - line.qty
            )

    if po_item_id and po_item_id != old_po_item_id:
        new_po_item = await db.get(POItem, po_item_id)
        if new_po_item:
            new_po_item.qty_invoiced = (new_po_item.qty_invoiced or Decimal("0")) + line.qty

    line.po_item_id = po_item_id
    await db.flush()

    touched_po_ids: set[UUID] = set()
    if old_po_item_id:
        old_item = await db.get(POItem, old_po_item_id)
        if old_item:
            touched_po_ids.add(old_item.po_id)
    if po_item_id:
        new_item = await db.get(POItem, po_item_id)
        if new_item:
            touched_po_ids.add(new_item.po_id)

    for po_id in touched_po_ids:
        po = (
            await db.execute(
                select(PurchaseOrder)
                .where(PurchaseOrder.id == po_id)
                .options(selectinload(PurchaseOrder.items))
            )
        ).scalar_one()
        po.amount_invoiced = sum(
            ((i.qty_invoiced or Decimal("0")) * i.unit_price for i in po.items),
            start=Decimal("0"),
        )

    all_matched = all(ln.po_item_id is not None for ln in inv.lines)
    if all_matched and not inv.is_fully_matched:
        inv.is_fully_matched = True
        inv.status = "matched"
    elif not all_matched and inv.is_fully_matched:
        inv.is_fully_matched = False
        inv.status = "pending_match"

    await db.commit()
    await db.refresh(line)
    return line
