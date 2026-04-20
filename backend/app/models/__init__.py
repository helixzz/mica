"""Domain models for Walking Skeleton v0.0.1.

Intentionally minimal. Expansion happens in v0.1+.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base, TimestampMixin, new_uuid


# ============================================================================
# Enums
# ============================================================================


class UserRole(StrEnum):
    ADMIN = "admin"
    IT_BUYER = "it_buyer"
    DEPT_MANAGER = "dept_manager"
    FINANCE_AUDITOR = "finance_auditor"
    PROCUREMENT_MGR = "procurement_mgr"


class PRStatus(StrEnum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"
    RETURNED = "returned"
    CANCELLED = "cancelled"
    CONVERTED = "converted"


class POStatus(StrEnum):
    DRAFT = "draft"
    CONFIRMED = "confirmed"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class ApprovalAction(StrEnum):
    APPROVE = "approve"
    REJECT = "reject"
    RETURN = "return"


# ============================================================================
# Core tables
# ============================================================================


class Company(Base, TimestampMixin):
    """Legal entity / company subject. One Mica instance can host multiple."""

    __tablename__ = "companies"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=new_uuid)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    name_zh: Mapped[str] = mapped_column(String(255), nullable=False)
    name_en: Mapped[str | None] = mapped_column(String(255))
    default_locale: Mapped[str] = mapped_column(String(10), default="zh-CN", nullable=False)
    default_currency: Mapped[str] = mapped_column(String(3), default="CNY", nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    departments: Mapped[list[Department]] = relationship(back_populates="company")
    users: Mapped[list[User]] = relationship(back_populates="company")


class Department(Base, TimestampMixin):
    __tablename__ = "departments"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=new_uuid)
    company_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("companies.id"), nullable=False
    )
    code: Mapped[str] = mapped_column(String(32), nullable=False)
    name_zh: Mapped[str] = mapped_column(String(128), nullable=False)
    name_en: Mapped[str | None] = mapped_column(String(128))
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    company: Mapped[Company] = relationship(back_populates="departments")

    __table_args__ = (UniqueConstraint("company_id", "code"),)


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=new_uuid)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(255))  # NULL for SAML-only users
    role: Mapped[str] = mapped_column(String(32), nullable=False)  # UserRole enum value
    company_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("companies.id"), nullable=False
    )
    department_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("departments.id")
    )
    preferred_locale: Mapped[str] = mapped_column(String(10), default="zh-CN", nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    is_local_admin: Mapped[bool] = mapped_column(default=False, nullable=False)
    auth_provider: Mapped[str] = mapped_column(String(32), default="local", nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    company: Mapped[Company] = relationship(back_populates="users")
    department: Mapped[Department | None] = relationship()

    __table_args__ = (
        CheckConstraint(
            "role IN ('admin','it_buyer','dept_manager','finance_auditor','procurement_mgr')",
            name="valid_role",
        ),
    )


class Supplier(Base, TimestampMixin):
    __tablename__ = "suppliers"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=new_uuid)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_name: Mapped[str | None] = mapped_column(String(128))
    contact_phone: Mapped[str | None] = mapped_column(String(32))
    contact_email: Mapped[str | None] = mapped_column(String(255))
    tax_number: Mapped[str | None] = mapped_column(String(64))
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)


class Item(Base, TimestampMixin):
    """Catalog item / SKU. Skeleton: minimal fields."""

    __tablename__ = "items"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=new_uuid)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str | None] = mapped_column(String(64))
    uom: Mapped[str] = mapped_column(String(16), default="EA", nullable=False)
    specification: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)


# ============================================================================
# Purchase flow
# ============================================================================


class PurchaseRequisition(Base, TimestampMixin):
    __tablename__ = "purchase_requisitions"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=new_uuid)
    pr_number: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    business_reason: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default=PRStatus.DRAFT.value, nullable=False)
    requester_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    company_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("companies.id"), nullable=False
    )
    department_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("departments.id")
    )
    currency: Mapped[str] = mapped_column(String(3), default="CNY", nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    required_date: Mapped[date | None] = mapped_column(Date)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    decided_by_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    decision_comment: Mapped[str | None] = mapped_column(Text)

    requester: Mapped[User] = relationship(foreign_keys=[requester_id])
    decided_by: Mapped[User | None] = relationship(foreign_keys=[decided_by_id])
    company: Mapped[Company] = relationship()
    department: Mapped[Department | None] = relationship()
    items: Mapped[list[PRItem]] = relationship(
        back_populates="pr", cascade="all, delete-orphan", order_by="PRItem.line_no"
    )


class PRItem(Base, TimestampMixin):
    __tablename__ = "pr_items"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=new_uuid)
    pr_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("purchase_requisitions.id", ondelete="CASCADE"),
        nullable=False,
    )
    line_no: Mapped[int] = mapped_column(nullable=False)
    item_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("items.id"))
    item_name: Mapped[str] = mapped_column(String(255), nullable=False)
    specification: Mapped[str | None] = mapped_column(Text)
    supplier_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("suppliers.id"))
    qty: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    uom: Mapped[str] = mapped_column(String(16), default="EA", nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0"), nullable=False)

    pr: Mapped[PurchaseRequisition] = relationship(back_populates="items")
    item: Mapped[Item | None] = relationship()
    supplier: Mapped[Supplier | None] = relationship()

    __table_args__ = (UniqueConstraint("pr_id", "line_no"),)


class PurchaseOrder(Base, TimestampMixin):
    __tablename__ = "purchase_orders"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=new_uuid)
    po_number: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    pr_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("purchase_requisitions.id"), nullable=False
    )
    supplier_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("suppliers.id"), nullable=False
    )
    company_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("companies.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), default=POStatus.CONFIRMED.value, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="CNY", nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    # Future extensibility fields (ADR 0002 D6)
    source_type: Mapped[str] = mapped_column(String(32), default="manual", nullable=False)
    source_ref: Mapped[str | None] = mapped_column(String(128))
    created_by_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )

    pr: Mapped[PurchaseRequisition] = relationship()
    supplier: Mapped[Supplier] = relationship()
    company: Mapped[Company] = relationship()
    created_by: Mapped[User] = relationship()
    items: Mapped[list[POItem]] = relationship(
        back_populates="po", cascade="all, delete-orphan", order_by="POItem.line_no"
    )


class POItem(Base, TimestampMixin):
    __tablename__ = "po_items"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=new_uuid)
    po_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("purchase_orders.id", ondelete="CASCADE"),
        nullable=False,
    )
    pr_item_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("pr_items.id"))
    line_no: Mapped[int] = mapped_column(nullable=False)
    item_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("items.id"))
    item_name: Mapped[str] = mapped_column(String(255), nullable=False)
    specification: Mapped[str | None] = mapped_column(Text)
    qty: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    uom: Mapped[str] = mapped_column(String(16), default="EA", nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)

    po: Mapped[PurchaseOrder] = relationship(back_populates="items")

    __table_args__ = (UniqueConstraint("po_id", "line_no"),)


class AuditLog(Base):
    """Minimal audit log for key business events."""

    __tablename__ = "audit_logs"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=new_uuid)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.utcnow(), nullable=False
    )
    actor_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    actor_name: Mapped[str | None] = mapped_column(String(128))
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_type: Mapped[str | None] = mapped_column(String(64))
    resource_id: Mapped[str | None] = mapped_column(String(64))
    metadata_json: Mapped[dict | None] = mapped_column(JSONB)
    comment: Mapped[str | None] = mapped_column(Text)
