from fastapi import APIRouter

from api.auth import router as auth_router
from api.opd import router as opd_router

api_router = APIRouter(prefix="/api")

api_router.include_router(auth_router)
api_router.include_router(opd_router)
