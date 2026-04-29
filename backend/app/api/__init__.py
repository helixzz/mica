from fastapi import APIRouter

from app.api.v1 import (
    admin,
    ai,
    approval,
    approval_delegations,
    approval_rules,
    auth,
    authz,
    classification,
    contracts,
    dashboard,
    document_templates,
    documents,
    feishu_webhook,
    flow,
    import_excel,
    master_data,
    notifications,
    payment_schedule,
    purchase,
    recycle_bin,
    rfq,
    saml,
    search,
    sku,
    system_params_admin,
)

api_router = APIRouter(prefix="/v1")
api_router.include_router(auth.router)
api_router.include_router(saml.router)
api_router.include_router(master_data.router)
api_router.include_router(purchase.router)
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
api_router.include_router(admin.router)
api_router.include_router(system_params_admin.router)
api_router.include_router(dashboard.router)
api_router.include_router(payment_schedule.router)
api_router.include_router(classification.router)
api_router.include_router(import_excel.router)
api_router.include_router(rfq.router)
api_router.include_router(recycle_bin.router)
api_router.include_router(document_templates.router)
api_router.include_router(feishu_webhook.router)
