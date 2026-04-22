from fastapi import APIRouter

from app.api.v1 import (
    admin,
    ai,
    approval,
    approval_delegations,
    approval_rules,
    auth,
    authz,
    contracts,
    dashboard,
    documents,
    flow,
    master_data,
    notifications,
    payment_schedule,
    purchase,
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
