from fastapi import APIRouter

from api.auth import router as auth_router
from api.opd import router as opd_router
from api.appointment import router as appointment_router
from api.doctor import router as doctor_router
from api.patient import router as patient_router

api_router = APIRouter(prefix="/api")

api_router.include_router(auth_router)
api_router.include_router(opd_router)
api_router.include_router(appointment_router)
api_router.include_router(doctor_router)
api_router.include_router(patient_router)
