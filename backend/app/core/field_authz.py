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
    # ── Export-only kinds (v1.53.0) ──────────────────────────────────────
    # Added so the export framework can gate columns field-by-field. Their
    # absence used to be dangerous: ``filter_dict_by_role`` grants every field
    # when a kind is missing, and ``export_registry.register`` now refuses to
    # load a dataset whose gated kind is not listed here.
    "contract": {
        "admin": {"*"},
        "procurement_mgr": {"*"},
        "finance_auditor": {"*"},
        "it_buyer": {
            "id",
            "contract_number",
            "po_id",
            "supplier_id",
            "title",
            "current_version",
            "status",
            "currency",
            "total_amount",
            "signed_date",
            "effective_date",
            "expiry_date",
            "notes",
            "created_at",
            "updated_at",
        },
        "dept_manager": {
            "id",
            "contract_number",
            "po_id",
            "supplier_id",
            "title",
            "current_version",
            "status",
            "currency",
            "total_amount",
            "signed_date",
            "effective_date",
            "expiry_date",
            "created_at",
            "updated_at",
        },
    },
    "supplier": {
        "admin": {"*"},
        "procurement_mgr": {"*"},
        "finance_auditor": {"*"},
        # Payee bank details and the tax number are settlement data: IT buyers
        # and department managers do not need them.
        "it_buyer": {
            "id",
            "code",
            "name",
            "contact_name",
            "contact_phone",
            "contact_email",
            "notes",
            "is_enabled",
            "is_deleted",
            "created_at",
            "updated_at",
        },
        "dept_manager": {
            "id",
            "code",
            "name",
            "contact_name",
            "contact_phone",
            "contact_email",
            "is_enabled",
            "created_at",
            "updated_at",
        },
    },
    "item": {
        "admin": {"*"},
        "procurement_mgr": {"*"},
        "it_buyer": {"*"},
        "finance_auditor": {"*"},
        "dept_manager": {
            "id",
            "code",
            "name",
            "category",
            "category_id",
            "uom",
            "specification",
            "requires_serial",
            "is_enabled",
            "created_at",
            "updated_at",
        },
    },
    "sku_price_record": {
        "admin": {"*"},
        "procurement_mgr": {"*"},
        "finance_auditor": {"*"},
        "it_buyer": {
            "id",
            "item_id",
            "supplier_id",
            "price",
            "currency",
            "quotation_date",
            "source_type",
            "source_ref",
            "entered_by_id",
            "notes",
            "created_at",
            "updated_at",
            "avg_price",
            "median_price",
            "stddev",
            "min_price",
            "max_price",
            "sample_size",
            "last_refreshed_at",
            "baseline_avg_price",
            "observed_price",
            "deviation_pct",
            "severity",
            "status",
        },
        "dept_manager": {
            "id",
            "item_id",
            "supplier_id",
            "price",
            "currency",
            "quotation_date",
            "source_type",
            "created_at",
            "avg_price",
            "median_price",
            "min_price",
            "max_price",
            "sample_size",
        },
    },
    "shipment": {
        "admin": {"*"},
        "procurement_mgr": {"*"},
        "finance_auditor": {"*"},
        "it_buyer": {
            "id",
            "shipment_number",
            "po_id",
            "contract_id",
            "batch_no",
            "is_default",
            "status",
            "carrier",
            "tracking_number",
            "expected_date",
            "actual_date",
            "received_by_id",
            "notes",
            "created_at",
            "updated_at",
            "item_name",
            "line_no",
            "qty_shipped",
            "qty_received",
            "unit_price",
        },
        "dept_manager": {
            "id",
            "shipment_number",
            "po_id",
            "contract_id",
            "batch_no",
            "status",
            "carrier",
            "tracking_number",
            "expected_date",
            "actual_date",
            "notes",
            "created_at",
            "updated_at",
            "item_name",
            "line_no",
            "qty_shipped",
            "qty_received",
        },
    },
    "delivery_plan": {
        "admin": {"*"},
        "procurement_mgr": {"*"},
        "it_buyer": {"*"},
        "finance_auditor": {"*"},
        "dept_manager": {
            "id",
            "po_id",
            "contract_id",
            "item_id",
            "plan_name",
            "planned_qty",
            "planned_date",
            "actual_qty",
            "actual_date",
            "status",
            "created_at",
            "updated_at",
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
