from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlmodel import Session, select

from dependencies.auth import require_roles
from models import get_session
from models.users import AuthRole, Doctor

router = APIRouter(prefix="/doctor", tags=["Doctor"])


class DoctorAvailabilityUpdateRequest(BaseModel):
    is_available: bool
    doctor_id: Optional[int] = None


@router.get("/profile")
def get_doctor_profile(
        session: Session = Depends(get_session),
        current_user: dict = Depends(
            require_roles(AuthRole.DOCTOR, AuthRole.ADMIN))
):
    doctor = session.exec(
        select(Doctor).where(Doctor.auth_id == current_user["user_id"])
    ).first()

    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor profile not found")

    return {
        "id": doctor.id,
        "name": doctor.name,
        "is_available": doctor.is_available,
        "created_at": doctor.created_at
    }


@router.patch("/availability")
def update_doctor_availability(
    request: DoctorAvailabilityUpdateRequest,
    session: Session = Depends(get_session),
    current_user: dict = Depends(
        require_roles(AuthRole.DOCTOR, AuthRole.ADMIN))
):
    if current_user.get("role") == AuthRole.ADMIN.value:
        if request.doctor_id is None:
            raise HTTPException(
                status_code=400,
                detail="doctor_id is required for admin"
            )
        doctor = session.exec(
            select(Doctor).where(Doctor.id == request.doctor_id)
        ).first()
    else:
        doctor = session.exec(
            select(Doctor).where(Doctor.auth_id == current_user["user_id"])
        ).first()

    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor profile not found")

    doctor.is_available = request.is_available
    session.add(doctor)
    session.commit()

    return {"message": "Availability updated successfully"}
