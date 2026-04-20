from fastapi import APIRouter

from app.api.v1 import auth, master_data, purchase

api_router = APIRouter(prefix="/v1")
api_router.include_router(auth.router)
api_router.include_router(master_data.router)
api_router.include_router(purchase.router)
