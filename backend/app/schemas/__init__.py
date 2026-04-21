from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    username: str
    email: EmailStr
    display_name: str
    role: str
    company_id: UUID
    department_id: UUID | None = None
    preferred_locale: str
    is_active: bool


class CompanyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    code: str
    name_zh: str
    name_en: str | None = None
    default_locale: str
    default_currency: str


class DepartmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    company_id: UUID
    code: str
    name_zh: str
    name_en: str | None = None


class SupplierOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    code: str
    name: str
    contact_name: str | None = None
    contact_phone: str | None = None
    contact_email: str | None = None


class ItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    code: str
    name: str
    category: str | None = None
    uom: str
    specification: str | None = None
    requires_serial: bool = False


class PRItemIn(BaseModel):
    line_no: int = Field(..., ge=1)
    item_id: UUID | None = None
    item_name: str = Field(..., min_length=1, max_length=255)
    specification: str | None = None
    supplier_id: UUID | None = None
    qty: Decimal = Field(..., gt=0)
    uom: str = "EA"
    unit_price: Decimal = Field(..., ge=0)


class PRItemOut(PRItemIn):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    amount: Decimal


class PRCreateIn(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    business_reason: str | None = None
    department_id: UUID | None = None
    currency: str = "CNY"
    required_date: date | None = None
    items: list[PRItemIn] = Field(default_factory=list)


class PRUpdateIn(BaseModel):
    title: str | None = None
    business_reason: str | None = None
    department_id: UUID | None = None
    currency: str | None = None
    required_date: date | None = None
    items: list[PRItemIn] | None = None


class PRDecisionIn(BaseModel):
    action: Literal["approve", "reject", "return"]
    comment: str | None = None


class PROut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    pr_number: str
    title: str
    business_reason: str | None
    status: str
    requester_id: UUID
    company_id: UUID
    department_id: UUID | None
    currency: str
    total_amount: Decimal
    required_date: date | None
    submitted_at: datetime | None
    decided_at: datetime | None
    decided_by_id: UUID | None
    decision_comment: str | None
    created_at: datetime
    updated_at: datetime
    items: list[PRItemOut]


class PRListOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    pr_number: str
    title: str
    status: str
    requester_id: UUID
    currency: str
    total_amount: Decimal
    submitted_at: datetime | None
    created_at: datetime


class POItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    line_no: int
    item_id: UUID | None
    item_name: str
    specification: str | None
    qty: Decimal
    qty_received: Decimal
    qty_invoiced: Decimal
    uom: str
    unit_price: Decimal
    amount: Decimal


class POOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    po_number: str
    pr_id: UUID
    supplier_id: UUID
    company_id: UUID
    status: str
    currency: str
    total_amount: Decimal
    qty_received: Decimal
    amount_paid: Decimal
    amount_invoiced: Decimal
    source_type: str
    source_ref: str | None
    created_by_id: UUID
    created_at: datetime
    updated_at: datetime
    items: list[POItemOut]


class POListOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    po_number: str
    pr_id: UUID
    supplier_id: UUID
    status: str
    currency: str
    total_amount: Decimal
    amount_paid: Decimal
    amount_invoiced: Decimal
    created_at: datetime


class ContractCreateIn(BaseModel):
    po_id: UUID
    title: str
    total_amount: Decimal
    signed_date: date | None = None
    effective_date: date | None = None
    expiry_date: date | None = None
    notes: str | None = None


class ContractOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    contract_number: str
    po_id: UUID
    supplier_id: UUID
    title: str
    current_version: int
    status: str
    currency: str
    total_amount: Decimal
    signed_date: date | None
    effective_date: date | None
    expiry_date: date | None
    notes: str | None
    created_at: datetime


class ShipmentItemIn(BaseModel):
    po_item_id: UUID
    qty_shipped: Decimal = Field(..., gt=0)
    qty_received: Decimal | None = None


class ShipmentCreateIn(BaseModel):
    po_id: UUID
    items: list[ShipmentItemIn] = Field(..., min_length=1)
    carrier: str | None = None
    tracking_number: str | None = None
    expected_date: date | None = None
    actual_date: date | None = None
    notes: str | None = None


class ShipmentItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    po_item_id: UUID
    line_no: int
    item_name: str
    qty_shipped: Decimal
    qty_received: Decimal
    unit_price: Decimal


class ShipmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    shipment_number: str
    po_id: UUID
    batch_no: int
    is_default: bool
    status: str
    carrier: str | None
    tracking_number: str | None
    expected_date: date | None
    actual_date: date | None
    notes: str | None
    created_at: datetime
    items: list[ShipmentItemOut]


class SerialNumberIn(BaseModel):
    serial_number: str = Field(..., min_length=1, max_length=128)
    manufacturer: str | None = None
    model_number: str | None = None
    warranty_expiry: date | None = None


class PaymentCreateIn(BaseModel):
    po_id: UUID
    amount: Decimal = Field(..., gt=0)
    due_date: date | None = None
    payment_date: date | None = None
    payment_method: str = "bank_transfer"
    transaction_ref: str | None = None
    notes: str | None = None


class PaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    payment_number: str
    po_id: UUID
    installment_no: int
    amount: Decimal
    currency: str
    due_date: date | None
    payment_date: date | None
    payment_method: str
    transaction_ref: str | None
    status: str
    notes: str | None
    created_at: datetime


class PaymentConfirmIn(BaseModel):
    payment_date: date | None = None
    transaction_ref: str | None = None


class InvoiceLineIn(BaseModel):
    po_item_id: UUID | None = None
    item_name: str = Field(..., min_length=1)
    qty: Decimal = Field(..., gt=0)
    unit_price: Decimal = Field(..., ge=0)


class InvoiceCreateIn(BaseModel):
    po_id: UUID
    invoice_number: str = Field(..., min_length=1, max_length=64)
    invoice_date: date
    tax_amount: Decimal = Decimal("0")
    tax_number: str | None = None
    due_date: date | None = None
    notes: str | None = None
    lines: list[InvoiceLineIn] = Field(..., min_length=1)


class InvoiceLineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    po_item_id: UUID | None
    line_no: int
    item_name: str
    qty: Decimal
    unit_price: Decimal
    amount: Decimal


class InvoiceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    internal_number: str
    invoice_number: str
    po_id: UUID
    supplier_id: UUID
    invoice_date: date
    due_date: date | None
    subtotal: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    currency: str
    tax_number: str | None
    status: str
    notes: str | None
    created_at: datetime
    lines: list[InvoiceLineOut]


class POProgressOut(BaseModel):
    po_id: str
    po_number: str
    total_amount: str
    amount_paid: str
    amount_invoiced: str
    total_qty: str
    qty_received: str
    qty_invoiced: str
    pct_received: float
    pct_invoiced: float
    pct_paid: float


class ApprovalTaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    instance_id: UUID
    stage_order: int
    stage_name: str
    assignee_id: UUID
    assignee_role: str | None
    status: str
    action: str | None
    comment: str | None
    assigned_at: datetime
    acted_at: datetime | None


class ApprovalInstanceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    biz_type: str
    biz_id: UUID
    biz_number: str | None
    title: str
    status: str
    current_stage: int
    total_stages: int
    submitter_id: UUID
    amount: Decimal | None
    submitted_at: datetime | None
    completed_at: datetime | None
    tasks: list[ApprovalTaskOut]


class AIFeaturePromptIn(BaseModel):
    feature_code: Literal["pr_description_polish", "sku_suggest"]
    draft: str | None = None
    query: str | None = None


class AIModelOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    provider: str
    model_string: str
    modality: str
    api_base: str | None
    is_active: bool
    priority: int


class AIFeatureRoutingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    feature_code: str
    primary_model_id: UUID | None
    temperature: Decimal
    max_tokens: int
    enabled: bool


class FieldManifestOut(BaseModel):
    resource: str
    role: str
    fields: dict[str, bool]
