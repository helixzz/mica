from fastapi import APIRouter

from app.api.v1 import (
    admin,
    ai,
    approval,
    auth,
    authz,
    contracts,
    documents,
    flow,
    master_data,
    purchase,
    saml,
    sku,
)

api_router = APIRouter(prefix="/v1")
api_router.include_router(auth.router)
api_router.include_router(saml.router)
api_router.include_router(master_data.router)
api_router.include_router(purchase.router)
api_router.include_router(flow.router)
api_router.include_router(contracts.router)
api_router.include_router(sku.router)
api_router.include_router(approval.router)
api_router.include_router(authz.router)
api_router.include_router(ai.router)
api_router.include_router(documents.router)
api_router.include_router(admin.router)
