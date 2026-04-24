from __future__ import annotations

import re

# pyright: reportUnannotatedClassAttribute=false, reportAny=false, reportExplicitAny=false, reportUnknownMemberType=false, reportUnknownVariableType=false
from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models import JSONValue

_MASTER_DATA_CODE_RE = re.compile(r"^[A-Z0-9_-]+$")


def _normalize_master_data_code(value: str) -> str:
    normalized = value.strip().upper()
    if not normalized:
        raise ValueError("code is required")
    if not _MASTER_DATA_CODE_RE.fullmatch(normalized):
        raise ValueError(
            "code must contain only uppercase letters, numbers, hyphens, or underscores"
        )
    return normalized


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
    email: str
    display_name: str
    role: str
    company_id: UUID
    department_id: UUID | None = None
    preferred_locale: str
    is_active: bool


class CompanyCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=32)
    name_zh: str = Field(..., min_length=1, max_length=255)
    name_en: str | None = Field(default=None, max_length=255)
    default_locale: str = Field(default="zh-CN", min_length=2, max_length=10)
    default_currency: str = Field(default="CNY", min_length=3, max_length=3)

    @field_validator("code")
    @classmethod
    def validate_code(cls, value: str) -> str:
        return _normalize_master_data_code(value)


class CompanyUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=32)
    name_zh: str | None = Field(default=None, min_length=1, max_length=255)
    name_en: str | None = Field(default=None, max_length=255)
    default_locale: str | None = Field(default=None, min_length=2, max_length=10)
    default_currency: str | None = Field(default=None, min_length=3, max_length=3)
    is_enabled: bool | None = None

    @field_validator("code")
    @classmethod
    def validate_code(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return _normalize_master_data_code(value)


class CompanyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    code: str
    name_zh: str
    name_en: str | None = None
    default_locale: str
    default_currency: str
    is_enabled: bool
    is_deleted: bool
    created_at: datetime
    updated_at: datetime


class DepartmentCreate(BaseModel):
    company_id: UUID
    code: str = Field(..., min_length=1, max_length=32)
    name_zh: str = Field(..., min_length=1, max_length=128)
    name_en: str | None = Field(default=None, max_length=128)
    parent_id: UUID | None = None

    @field_validator("code")
    @classmethod
    def validate_code(cls, value: str) -> str:
        return _normalize_master_data_code(value)


class DepartmentUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=32)
    name_zh: str | None = Field(default=None, min_length=1, max_length=128)
    name_en: str | None = Field(default=None, max_length=128)
    parent_id: UUID | None = None

    @field_validator("code")
    @classmethod
    def validate_code(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return _normalize_master_data_code(value)


class DepartmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    company_id: UUID
    code: str
    name_zh: str
    name_en: str | None = None
    parent_id: UUID | None = None
    is_enabled: bool
    is_deleted: bool
    created_at: datetime
    updated_at: datetime


class SupplierCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=32)
    name: str = Field(..., min_length=1, max_length=255)
    tax_number: str | None = Field(default=None, max_length=64)
    contact_name: str | None = Field(default=None, max_length=128)
    contact_phone: str | None = Field(default=None, max_length=32)
    contact_email: str | None = Field(default=None, max_length=255)
    payee_name: str | None = Field(default=None, max_length=255)
    payee_bank: str | None = Field(default=None, max_length=255)
    payee_bank_account: str | None = Field(default=None, max_length=64)
    notes: str | None = None

    @field_validator("code")
    @classmethod
    def validate_code(cls, value: str) -> str:
        return _normalize_master_data_code(value)


class SupplierUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=32)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    tax_number: str | None = Field(default=None, max_length=64)
    contact_name: str | None = Field(default=None, max_length=128)
    contact_phone: str | None = Field(default=None, max_length=32)
    contact_email: str | None = Field(default=None, max_length=255)
    payee_name: str | None = Field(default=None, max_length=255)
    payee_bank: str | None = Field(default=None, max_length=255)
    payee_bank_account: str | None = Field(default=None, max_length=64)
    notes: str | None = None

    @field_validator("code")
    @classmethod
    def validate_code(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return _normalize_master_data_code(value)


class SupplierOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    code: str
    name: str
    tax_number: str | None = None
    contact_name: str | None = None
    contact_phone: str | None = None
    contact_email: str | None = None
    payee_name: str | None = None
    payee_bank: str | None = None
    payee_bank_account: str | None = None
    notes: str | None = None
    is_enabled: bool
    is_deleted: bool
    created_at: datetime
    updated_at: datetime


class ItemCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=64)
    name: str = Field(..., min_length=1, max_length=255)
    category: str | None = Field(default=None, max_length=64)
    category_id: UUID | None = None
    uom: str = Field(default="EA", min_length=1, max_length=16)
    specification: str | None = None
    requires_serial: bool = False

    @field_validator("code")
    @classmethod
    def validate_code(cls, value: str) -> str:
        return _normalize_master_data_code(value)


class ItemUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=64)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    category: str | None = Field(default=None, max_length=64)
    category_id: UUID | None = None
    uom: str | None = Field(default=None, min_length=1, max_length=16)
    specification: str | None = None
    requires_serial: bool | None = None
    is_enabled: bool | None = None

    @field_validator("code")
    @classmethod
    def validate_code(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return _normalize_master_data_code(value)


class ItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    code: str
    name: str
    category: str | None = None
    category_id: UUID | None = None
    uom: str
    specification: str | None = None
    requires_serial: bool = False
    is_enabled: bool
    is_deleted: bool
    created_at: datetime
    updated_at: datetime


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
    company_id: UUID | None = None
    cost_center_id: UUID | None = None
    expense_type_id: UUID | None = None
    procurement_category_id: UUID | None = None
    currency: str = "CNY"
    required_date: date | None = None
    items: list[PRItemIn] = Field(default_factory=list)


class PRUpdateIn(BaseModel):
    title: str | None = None
    business_reason: str | None = None
    department_id: UUID | None = None
    company_id: UUID | None = None
    cost_center_id: UUID | None = None
    expense_type_id: UUID | None = None
    procurement_category_id: UUID | None = None
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
    cost_center_id: UUID | None = None
    expense_type_id: UUID | None = None
    procurement_category_id: UUID | None = None
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


class ContractUpdateIn(BaseModel):
    title: str | None = None
    total_amount: Decimal | None = None
    signed_date: date | None = None
    effective_date: date | None = None
    expiry_date: date | None = None
    notes: str | None = None
    change_reason: str | None = None


class ContractStatusIn(BaseModel):
    status: str
    reason: str | None = None


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


class ContractVersionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    contract_id: UUID
    version_number: int
    change_type: str
    change_reason: str | None
    snapshot_json: dict[str, JSONValue]
    changed_by_id: UUID | None
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


class ShipmentUpdate(BaseModel):
    status: str | None = None
    carrier: str | None = None
    tracking_number: str | None = None
    expected_date: date | None = None
    actual_date: date | None = None
    notes: str | None = None


class ShipmentAttachIn(BaseModel):
    document_id: UUID
    role: str = "attachment"


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
    line_type: Literal["product", "freight", "adjustment", "tax_surcharge", "note"] = "product"
    item_name: str = Field(..., min_length=1)
    qty: Decimal = Field(..., gt=0)
    unit_price: Decimal = Field(..., ge=0)
    tax_amount: Decimal = Decimal("0")


class InvoiceCreateIn(BaseModel):
    invoice_number: str = Field(..., min_length=1, max_length=64)
    supplier_id: UUID
    invoice_date: date
    tax_number: str | None = None
    due_date: date | None = None
    notes: str | None = None
    lines: list[InvoiceLineIn] = Field(..., min_length=1)
    attachment_document_ids: list[UUID] = Field(..., min_length=1)


class InvoiceLineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    po_item_id: UUID | None
    line_type: str
    line_no: int
    item_name: str
    qty: Decimal
    unit_price: Decimal
    subtotal: Decimal
    tax_amount: Decimal


class InvoiceAttachmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    document_id: UUID
    role: str
    display_order: int
    original_filename: str
    content_type: str
    file_size: int


class InvoiceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    internal_number: str
    invoice_number: str
    supplier_id: UUID
    invoice_date: date
    due_date: date | None
    subtotal: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    currency: str
    tax_number: str | None
    status: str
    is_fully_matched: bool
    notes: str | None
    created_at: datetime
    lines: list[InvoiceLineOut]


class InvoiceListOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    internal_number: str
    invoice_number: str
    supplier_id: UUID
    invoice_date: date
    subtotal: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    currency: str
    status: str
    is_fully_matched: bool
    created_at: datetime


class InvoiceLineValidation(BaseModel):
    line_no: int
    po_item_id: UUID | None
    invoiced_subtotal: Decimal
    po_remaining: Decimal | None
    overage: Decimal
    severity: Literal["ok", "warn", "error"]
    message: str | None = None


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
    meta: dict[str, JSONValue] = Field(default_factory=dict)
    assigned_at: datetime
    acted_at: datetime | None
    # Flattened from instance relationship
    biz_id: UUID | None = None
    biz_number: str | None = None
    biz_title: str | None = None
    biz_amount: Decimal | None = None
    submitter_name: str | None = None


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


class ApprovalRuleStageIn(BaseModel):
    stage_name: str = Field(..., min_length=1, max_length=100)
    approver_role: Literal[
        "admin", "dept_manager", "procurement_mgr", "finance_auditor", "it_buyer"
    ]
    order: int = Field(..., ge=1)


class ApprovalRuleIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    biz_type: str = Field(..., min_length=1, max_length=64)
    amount_min: Decimal | None = None
    amount_max: Decimal | None = None
    stages: list[ApprovalRuleStageIn] = Field(..., min_length=1)
    is_active: bool = True
    priority: int = 100


class ApprovalRuleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    biz_type: str
    amount_min: Decimal | None
    amount_max: Decimal | None
    stages: list[ApprovalRuleStageIn]
    is_active: bool
    priority: int
    created_at: datetime
    updated_at: datetime


class ApproverDelegationIn(BaseModel):
    to_user_id: UUID
    starts_at: datetime
    ends_at: datetime
    reason: str | None = Field(default=None, max_length=255)


class ApproverDelegationAdminIn(ApproverDelegationIn):
    from_user_id: UUID
    is_active: bool = True


class ApproverDelegationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    from_user_id: UUID
    to_user_id: UUID
    reason: str | None
    starts_at: datetime
    ends_at: datetime
    is_active: bool
    revoked_at: datetime | None
    created_at: datetime
    updated_at: datetime


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


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    original_filename: str
    content_type: str
    file_size: int
    content_hash: str
    doc_category: str
    created_at: datetime


class DownloadTokenOut(BaseModel):
    download_url: str
    expires_in: int


class InvoiceExtractLine(BaseModel):
    item_name: str | None = None
    spec: str | None = None
    qty: str | None = None
    unit_price: str | None = None
    tax_rate: str | None = None
    tax_amount: str | None = None
    subtotal: str | None = None


class InvoiceExtractOut(BaseModel):
    invoice_number: str | None = None
    invoice_code: str | None = None
    invoice_date: str | None = None
    seller_name: str | None = None
    seller_tax_id: str | None = None
    buyer_name: str | None = None
    buyer_tax_id: str | None = None
    subtotal: str | None = None
    tax_amount: str | None = None
    total_amount: str | None = None
    currency: str = "CNY"
    lines: list[InvoiceExtractLine] = []
    raw_extract_source: str
    confidence: float
    error: str | None = None


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    category: str
    title: str
    body: str | None
    link_url: str | None
    biz_type: str | None
    biz_id: UUID | None
    meta: dict[str, object]
    read_at: datetime | None
    sent_via: list[str]
    created_at: datetime


class NotificationListResponse(BaseModel):
    items: list[NotificationOut]
    has_more: bool


class UnreadCountResponse(BaseModel):
    total: int
    by_category: dict[str, int]


class MarkReadRequest(BaseModel):
    ids: list[UUID] | None = None
    all: bool = False


class SubscriptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    category: str
    in_app_enabled: bool
    email_enabled: bool


class SubscriptionUpdate(BaseModel):
    in_app_enabled: bool
    email_enabled: bool


class SystemParameterOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    key: str
    category: str
    value: JSONValue
    data_type: str
    default_value: JSONValue
    min_value: JSONValue | None = None
    max_value: JSONValue | None = None
    unit: str | None = None
    description_zh: str
    description_en: str
    is_sensitive: bool
    updated_by_id: UUID | None = None
    created_at: datetime
    updated_at: datetime


class SystemParameterUpdate(BaseModel):
    value: JSONValue


class LoginOptionsResponse(BaseModel):
    saml_enabled: bool
    saml_login_url: str | None = None


class SearchHit(BaseModel):
    entity_type: Literal["pr", "po", "contract", "contract_doc", "invoice", "supplier", "item"]
    entity_id: str
    title: str
    snippet: str | None = None
    score: float
    link_url: str
    meta: dict[str, JSONValue] = Field(default_factory=dict)


class SearchResponse(BaseModel):
    total: int
    by_type: dict[str, list[SearchHit]]
    top_hits: list[SearchHit]


class PaymentScheduleItemIn(BaseModel):
    installment_no: int
    label: str = Field(max_length=128)
    planned_amount: Decimal
    planned_date: date | None = None
    trigger_type: str = "fixed_date"
    trigger_description: str | None = None
    notes: str | None = None


class PaymentScheduleIn(BaseModel):
    items: list[PaymentScheduleItemIn]


class PaymentScheduleItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    contract_id: UUID | None = None
    po_id: UUID | None = None
    installment_no: int
    label: str
    planned_amount: Decimal
    planned_date: date | None
    trigger_type: str
    trigger_description: str | None
    status: str
    actual_amount: Decimal | None
    actual_date: date | None
    payment_record_id: UUID | None
    invoice_id: UUID | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class PaymentScheduleItemUpdate(BaseModel):
    label: str | None = None
    planned_amount: Decimal | None = None
    planned_date: date | None = None
    trigger_type: str | None = None
    trigger_description: str | None = None
    notes: str | None = None


class PaymentScheduleExecuteIn(BaseModel):
    payment_method: str = "bank_transfer"
    transaction_ref: str | None = None
    invoice_id: UUID | None = None
    amount: Decimal | None = None


class PaymentScheduleLinkInvoiceIn(BaseModel):
    invoice_id: UUID


class PaymentScheduleSummaryOut(BaseModel):
    contract_total: Decimal
    planned_total: Decimal
    paid_total: Decimal
    remaining: Decimal
    total_mismatch: bool
    items: list[PaymentScheduleItemOut]


class PaymentForecastMonth(BaseModel):
    month: str
    planned: Decimal
    paid: Decimal
    remaining: Decimal


class PaymentForecastOut(BaseModel):
    months: list[PaymentForecastMonth]
    grand_planned: Decimal
    grand_paid: Decimal
