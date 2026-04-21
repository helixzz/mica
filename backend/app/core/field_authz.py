from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class FieldVisibility(BaseModel):
    readable: bool = True
    writable: bool = False


FIELD_PERMISSIONS: dict[str, dict[str, set[str]]] = {
    "purchase_requisition": {
        "admin": {"*"},
        "it_buyer": {"*"},
        "dept_manager": {"*"},
        "procurement_mgr": {"*"},
        "finance_auditor": {
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
        },
    },
    "purchase_order": {
        "admin": {"*"},
        "procurement_mgr": {"*"},
        "it_buyer": {
            "id",
            "po_number",
            "pr_id",
            "supplier_id",
            "company_id",
            "status",
            "currency",
            "total_amount",
            "qty_received",
            "source_type",
            "source_ref",
            "created_by_id",
            "created_at",
            "updated_at",
            "items",
        },
        "dept_manager": {
            "id",
            "po_number",
            "pr_id",
            "supplier_id",
            "company_id",
            "status",
            "currency",
            "total_amount",
            "qty_received",
            "created_at",
            "updated_at",
            "items",
        },
        "finance_auditor": {"*"},
    },
    "payment_record": {
        "admin": {"*"},
        "finance_auditor": {"*"},
        "procurement_mgr": {"*"},
        "it_buyer": {
            "id",
            "payment_number",
            "po_id",
            "installment_no",
            "amount",
            "currency",
            "due_date",
            "payment_date",
            "status",
            "created_at",
            "updated_at",
        },
        "dept_manager": {
            "id",
            "payment_number",
            "po_id",
            "installment_no",
            "amount",
            "currency",
            "status",
            "created_at",
        },
    },
    "invoice": {
        "admin": {"*"},
        "finance_auditor": {"*"},
        "procurement_mgr": {"*"},
        "it_buyer": {
            "id",
            "internal_number",
            "invoice_number",
            "po_id",
            "supplier_id",
            "invoice_date",
            "total_amount",
            "currency",
            "status",
            "created_at",
        },
        "dept_manager": {
            "id",
            "internal_number",
            "invoice_number",
            "po_id",
            "invoice_date",
            "total_amount",
            "currency",
            "status",
        },
    },
}


def filter_dict_by_role(data: dict, resource: str, role: str) -> dict:
    perms = FIELD_PERMISSIONS.get(resource, {}).get(role)
    if perms is None or "*" in perms:
        return data
    return {k: v for k, v in data.items() if k in perms}


def filter_model_by_role(model: BaseModel, resource: str, role: str) -> dict:
    return filter_dict_by_role(model.model_dump(mode="json"), resource, role)


class FieldManifest(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    resource: str
    role: str
    fields: dict[str, bool]


def build_field_manifest(resource: str, role: str, all_fields: list[str]) -> FieldManifest:
    perms = FIELD_PERMISSIONS.get(resource, {}).get(role, set())
    if "*" in perms or not perms:
        vis = dict.fromkeys(all_fields, True)
    else:
        vis = {f: (f in perms) for f in all_fields}
    return FieldManifest(resource=resource, role=role, fields=vis)
