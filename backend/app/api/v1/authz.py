from fastapi import APIRouter

from app.core.field_authz import build_field_manifest
from app.core.security import CurrentUser
from app.schemas import FieldManifestOut

router = APIRouter()

ALL_FIELDS: dict[str, list[str]] = {
    "purchase_requisition": [
        "id",
        "pr_number",
        "title",
        "business_reason",
        "status",
        "requester_id",
        "company_id",
        "department_id",
        "currency",
        "total_amount",
        "required_date",
        "submitted_at",
        "decided_at",
        "decided_by_id",
        "decision_comment",
        "created_at",
        "updated_at",
        "items",
    ],
    "purchase_order": [
        "id",
        "po_number",
        "pr_id",
        "supplier_id",
        "company_id",
        "status",
        "currency",
        "total_amount",
        "qty_received",
        "amount_paid",
        "amount_invoiced",
        "source_type",
        "source_ref",
        "created_by_id",
        "created_at",
        "updated_at",
        "items",
    ],
    "payment_record": [
        "id",
        "payment_number",
        "po_id",
        "installment_no",
        "amount",
        "currency",
        "due_date",
        "payment_date",
        "payment_method",
        "transaction_ref",
        "status",
        "notes",
        "created_at",
    ],
    "invoice": [
        "id",
        "internal_number",
        "invoice_number",
        "po_id",
        "supplier_id",
        "invoice_date",
        "due_date",
        "subtotal",
        "tax_amount",
        "total_amount",
        "currency",
        "tax_number",
        "status",
        "notes",
        "created_at",
    ],
}


router_v1 = APIRouter()


@router_v1.get("/authz/field-manifest/{resource}", response_model=FieldManifestOut, tags=["authz"])
async def field_manifest(resource: str, user: CurrentUser):
    fields = ALL_FIELDS.get(resource, [])
    manifest = build_field_manifest(resource, user.role, fields)
    return FieldManifestOut(resource=manifest.resource, role=manifest.role, fields=manifest.fields)


router = router_v1
