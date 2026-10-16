from fastapi import APIRouter

from app.api.v1 import (
    activity_logs,
    admin,
    ai,
    api_tokens,
    approval,
    approval_delegations,
    approval_rules,
    auth,
    authz,
    classification,
    contracts,
    dashboard,
    delivery_addresses,
    delivery_plans,
    document_templates,
    documents,
    exports,
    feishu_webhook,
    flow,
    import_excel,
    insights,
    master_data,
    notifications,
    payment_schedule,
    purchase,
    recycle_bin,
    rfq,
    saml,
    search,
    sku,
    supplier_portal,
    system_params_admin,
    ui_config,
    websocket,
)

# One prefix, one router list. A `/v2` mirror used to be included here as a second
# copy of this list; it had no consumer, no recorded rationale, and had already
# drifted (the insights router was never added to it). See ADR 0005 — if a real
# breaking change ever needs a new prefix, create it then, with the decision
# written down.
api_router = APIRouter(prefix="/v1")
api_router.include_router(ui_config.router)
api_router.include_router(admin.router)
api_router.include_router(activity_logs.router)
api_router.include_router(auth.router)
api_router.include_router(api_tokens.router)
api_router.include_router(api_tokens.admin_router)
api_router.include_router(saml.router)
api_router.include_router(master_data.router)
api_router.include_router(purchase.router)
api_router.include_router(delivery_addresses.router)
api_router.include_router(flow.router)
api_router.include_router(contracts.router)
api_router.include_router(search.router)
api_router.include_router(sku.router)
api_router.include_router(approval.router)
api_router.include_router(approval_rules.router)
api_router.include_router(approval_delegations.router)
api_router.include_router(approval_delegations.admin_router)
api_router.include_router(authz.router)
api_router.include_router(ai.router)
api_router.include_router(documents.router)
api_router.include_router(notifications.router)
api_router.include_router(system_params_admin.router)
api_router.include_router(dashboard.router)
api_router.include_router(delivery_plans.router)
api_router.include_router(payment_schedule.router)
api_router.include_router(classification.router)
api_router.include_router(import_excel.router)
api_router.include_router(rfq.router)
api_router.include_router(recycle_bin.router)
api_router.include_router(document_templates.router)
api_router.include_router(feishu_webhook.router)
api_router.include_router(websocket.router)
api_router.include_router(supplier_portal.router)
api_router.include_router(insights.router)
api_router.include_router(exports.router)
