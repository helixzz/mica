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
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base, TimestampMixin, new_uuid


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
    PARTIALLY_RECEIVED = "partially_received"
    FULLY_RECEIVED = "fully_received"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class ContractStatus(StrEnum):
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    TERMINATED = "terminated"
    EXPIRED = "expired"


class ShipmentStatus(StrEnum):
    PENDING = "pending"
    IN_TRANSIT = "in_transit"
    ARRIVED = "arrived"
    ACCEPTED = "accepted"
    PARTIALLY_ACCEPTED = "partially_accepted"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class PaymentStatus(StrEnum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"


class InvoiceStatus(StrEnum):
    DRAFT = "draft"
    VERIFIED = "verified"
    APPROVED = "approved"
    PAID = "paid"
    CANCELLED = "cancelled"


class InvoiceLineType(StrEnum):
    PRODUCT = "product"
    FREIGHT = "freight"
    ADJUSTMENT = "adjustment"
    TAX_SURCHARGE = "tax_surcharge"
    NOTE = "note"


class ApprovalAction(StrEnum):
    APPROVE = "approve"
    REJECT = "reject"
    RETURN = "return"


class Company(Base, TimestampMixin):
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
    password_hash: Mapped[str | None] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(32), nullable=False)
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
    sso_external_id: Mapped[str | None] = mapped_column(String(255), unique=True)
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
    __tablename__ = "items"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=new_uuid)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str | None] = mapped_column(String(64))
    uom: Mapped[str] = mapped_column(String(16), default="EA", nullable=False)
    specification: Mapped[str | None] = mapped_column(Text)
    requires_serial: Mapped[bool] = mapped_column(default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)


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
    qty_received: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    amount_paid: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    amount_invoiced: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0"), nullable=False)
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
    qty_received: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    qty_invoiced: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    uom: Mapped[str] = mapped_column(String(16), default="EA", nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)

    po: Mapped[PurchaseOrder] = relationship(back_populates="items")

    __table_args__ = (UniqueConstraint("po_id", "line_no"),)


class Contract(Base, TimestampMixin):
    __tablename__ = "contracts"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=new_uuid)
    contract_number: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    po_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("purchase_orders.id"), nullable=False
    )
    supplier_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("suppliers.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    current_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default=ContractStatus.ACTIVE.value, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="CNY", nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    signed_date: Mapped[date | None] = mapped_column(Date)
    effective_date: Mapped[date | None] = mapped_column(Date)
    expiry_date: Mapped[date | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text)

    po: Mapped[PurchaseOrder] = relationship()
    supplier: Mapped[Supplier] = relationship()


class Shipment(Base, TimestampMixin):
    __tablename__ = "shipments"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=new_uuid)
    shipment_number: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    po_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("purchase_orders.id"), nullable=False
    )
    batch_no: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_default: Mapped[bool] = mapped_column(default=False, nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), default=ShipmentStatus.PENDING.value, nullable=False
    )
    carrier: Mapped[str | None] = mapped_column(String(128))
    tracking_number: Mapped[str | None] = mapped_column(String(128))
    expected_date: Mapped[date | None] = mapped_column(Date)
    actual_date: Mapped[date | None] = mapped_column(Date)
    received_by_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    notes: Mapped[str | None] = mapped_column(Text)

    po: Mapped[PurchaseOrder] = relationship()
    received_by: Mapped[User | None] = relationship()
    items: Mapped[list[ShipmentItem]] = relationship(
        back_populates="shipment", cascade="all, delete-orphan", order_by="ShipmentItem.line_no"
    )

    __table_args__ = (UniqueConstraint("po_id", "batch_no"),)


class ShipmentItem(Base, TimestampMixin):
    __tablename__ = "shipment_items"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=new_uuid)
    shipment_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("shipments.id", ondelete="CASCADE"),
        nullable=False,
    )
    po_item_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("po_items.id"), nullable=False
    )
    line_no: Mapped[int] = mapped_column(Integer, nullable=False)
    item_name: Mapped[str] = mapped_column(String(255), nullable=False)
    qty_shipped: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    qty_received: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)

    shipment: Mapped[Shipment] = relationship(back_populates="items")
    po_item: Mapped[POItem] = relationship()


class SerialNumberEntry(Base, TimestampMixin):
    __tablename__ = "serial_number_entries"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=new_uuid)
    shipment_item_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("shipment_items.id", ondelete="CASCADE"),
        nullable=False,
    )
    serial_number: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    manufacturer: Mapped[str | None] = mapped_column(String(128))
    model_number: Mapped[str | None] = mapped_column(String(128))
    warranty_expiry: Mapped[date | None] = mapped_column(Date)
    asset_id: Mapped[str | None] = mapped_column(String(64))
    asset_system: Mapped[str | None] = mapped_column(String(32))


class PaymentRecord(Base, TimestampMixin):
    __tablename__ = "payment_records"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=new_uuid)
    payment_number: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    po_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("purchase_orders.id"), nullable=False
    )
    installment_no: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="CNY", nullable=False)
    due_date: Mapped[date | None] = mapped_column(Date)
    payment_date: Mapped[date | None] = mapped_column(Date)
    payment_method: Mapped[str] = mapped_column(String(32), default="bank_transfer", nullable=False)
    transaction_ref: Mapped[str | None] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(
        String(32), default=PaymentStatus.PENDING.value, nullable=False
    )
    notes: Mapped[str | None] = mapped_column(Text)

    po: Mapped[PurchaseOrder] = relationship()


class Invoice(Base, TimestampMixin):
    __tablename__ = "invoices"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=new_uuid)
    internal_number: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    invoice_number: Mapped[str] = mapped_column(String(64), nullable=False)
    supplier_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("suppliers.id"), nullable=False
    )
    invoice_date: Mapped[date] = mapped_column(Date, nullable=False)
    received_date: Mapped[date | None] = mapped_column(Date)
    due_date: Mapped[date | None] = mapped_column(Date)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="CNY", nullable=False)
    tax_number: Mapped[str | None] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(
        String(32), default=InvoiceStatus.DRAFT.value, nullable=False
    )
    is_fully_matched: Mapped[bool] = mapped_column(default=False, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)

    supplier: Mapped[Supplier] = relationship()
    lines: Mapped[list[InvoiceLine]] = relationship(
        back_populates="invoice", cascade="all, delete-orphan", order_by="InvoiceLine.line_no"
    )


class InvoiceLine(Base, TimestampMixin):
    __tablename__ = "invoice_lines"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=new_uuid)
    invoice_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False
    )
    po_item_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("po_items.id", ondelete="SET NULL")
    )
    line_type: Mapped[str] = mapped_column(
        String(32), default=InvoiceLineType.PRODUCT.value, nullable=False
    )
    line_no: Mapped[int] = mapped_column(Integer, nullable=False)
    item_name: Mapped[str] = mapped_column(String(255), nullable=False)
    qty: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0"), nullable=False)

    invoice: Mapped[Invoice] = relationship(back_populates="lines")


class ApprovalInstance(Base, TimestampMixin):
    __tablename__ = "approval_instances"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=new_uuid)
    biz_type: Mapped[str] = mapped_column(String(50), nullable=False)
    biz_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    biz_number: Mapped[str | None] = mapped_column(String(100))
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    current_stage: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    total_stages: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    submitter_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    company_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("companies.id"), nullable=False
    )
    amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    submitter: Mapped[User] = relationship()
    tasks: Mapped[list[ApprovalTask]] = relationship(
        back_populates="instance", cascade="all, delete-orphan", order_by="ApprovalTask.stage_order"
    )

    __table_args__ = (
        Index("ix_approval_instances_biz", "biz_type", "biz_id"),
        Index("ix_approval_instances_status", "status"),
    )


class ApprovalTask(Base, TimestampMixin):
    __tablename__ = "approval_tasks"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=new_uuid)
    instance_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("approval_instances.id", ondelete="CASCADE"),
        nullable=False,
    )
    stage_order: Mapped[int] = mapped_column(Integer, nullable=False)
    stage_name: Mapped[str] = mapped_column(String(100), nullable=False)
    assignee_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    assignee_role: Mapped[str | None] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    action: Mapped[str | None] = mapped_column(String(20))
    comment: Mapped[str | None] = mapped_column(Text)
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.utcnow(), nullable=False
    )
    acted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    instance: Mapped[ApprovalInstance] = relationship(back_populates="tasks")
    assignee: Mapped[User] = relationship()


class AIModel(Base, TimestampMixin):
    __tablename__ = "ai_models"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    model_string: Mapped[str] = mapped_column(String(128), nullable=False)
    modality: Mapped[str] = mapped_column(String(16), default="text", nullable=False)
    api_key_encrypted: Mapped[str | None] = mapped_column(Text)
    api_base: Mapped[str | None] = mapped_column(String(255))
    timeout_s: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    capabilities: Mapped[dict | None] = mapped_column(JSONB)


class AIFeatureRouting(Base, TimestampMixin):
    __tablename__ = "ai_feature_routing"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=new_uuid)
    feature_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    primary_model_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("ai_models.id")
    )
    fallback_model_ids: Mapped[list | None] = mapped_column(JSONB)
    prompt_template: Mapped[str | None] = mapped_column(Text)
    temperature: Mapped[Decimal] = mapped_column(Numeric(3, 2), default=Decimal("0.3"), nullable=False)
    max_tokens: Mapped[int] = mapped_column(Integer, default=1024, nullable=False)
    enabled: Mapped[bool] = mapped_column(default=True, nullable=False)


class AICallLog(Base):
    __tablename__ = "ai_call_logs"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=new_uuid)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.utcnow(), nullable=False
    )
    feature_code: Mapped[str] = mapped_column(String(64), nullable=False)
    user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    model_name: Mapped[str | None] = mapped_column(String(64))
    provider: Mapped[str | None] = mapped_column(String(32))
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="success", nullable=False)
    error: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        Index("ix_ai_call_logs_feature_time", "feature_code", "occurred_at"),
    )


class AuditLog(Base):
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
