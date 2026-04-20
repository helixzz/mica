"""Pydantic schemas for API request/response."""
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
    created_at: datetime
