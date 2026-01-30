from datetime import date, datetime, time, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from sqlmodel import Session, select

from dependencies.auth import require_roles
from models import get_session
from models.users import AuthRole, Doctor, Patient
from models.appointment import Appointment, AppointmentStatus, AppointmentType, OPD

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


@router.get("/appointments")
def list_appointments_by_date(
    date: date = Query(..., description="Date (YYYY-MM-DD)"),
    session: Session = Depends(get_session),
    current_user: dict = Depends(require_roles(AuthRole.DOCTOR))
):
    doctor = session.exec(
        select(Doctor).where(Doctor.auth_id == current_user["user_id"])
    ).first()

    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor profile not found")

    start_dt = datetime.combine(date, time.min)
    end_dt = datetime.combine(date + timedelta(days=1), time.min)

    query = (
        select(Appointment, Patient, AppointmentStatus)
        .join(OPD)
        .join(Patient)
        .join(AppointmentStatus)
        .where(
            OPD.doctor_id == doctor.id,
            Appointment.appointment_datetime >= start_dt,
            Appointment.appointment_datetime < end_dt,
        )
    )
    appointments = session.exec(query).all()

    result = []
    for appointment, patient, status in appointments:
        result.append({
            "appointment_id": appointment.id,
            "datetime": appointment.appointment_datetime.isoformat(),
            "patient_name": patient.name,
            "status": status.status_name,
            "checked_in": appointment.checked_in
        })

    return result


@router.get("/appointments/{appointment_id}")
def get_appointment_detail(
    appointment_id: int,
    session: Session = Depends(get_session),
    current_user: dict = Depends(require_roles(AuthRole.DOCTOR))
):
    doctor = session.exec(
        select(Doctor).where(Doctor.auth_id == current_user["user_id"])
    ).first()

    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor profile not found")

    appointment_data = session.exec(
        select(Appointment, Patient, AppointmentType, AppointmentStatus)
        .join(OPD)
        .join(Patient)
        .join(AppointmentType)
        .join(AppointmentStatus)
        .where(
            Appointment.id == appointment_id,
            OPD.doctor_id == doctor.id,
        )
    ).first()

    if not appointment_data:
        raise HTTPException(status_code=404, detail="Appointment not found")

    appointment, patient, appointment_type, status = appointment_data

    return {
        "appointment_id": appointment.id,
        "patient": patient.name,
        "type": appointment_type.type_name,
        "notes": appointment.notes,
        "status": status.status_name,
        "checked_in": appointment.checked_in
    }


@router.post("/appointments/{appointment_id}/check-in")
def check_in_patient(
    appointment_id: int,
    session: Session = Depends(get_session),
    current_user: dict = Depends(require_roles(AuthRole.DOCTOR))
):
    doctor = session.exec(
        select(Doctor).where(Doctor.auth_id == current_user["user_id"])
    ).first()

    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor profile not found")

    appointment = session.exec(
        select(Appointment)
        .join(OPD)
        .where(
            Appointment.id == appointment_id,
            OPD.doctor_id == doctor.id,
        )
    ).first()

    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    appointment.checked_in = True
    session.add(appointment)
    session.commit()

    return {"message": "Patient checked in"}


@router.post("/appointments/{appointment_id}/status")
def update_appointment_status(
    appointment_id: int,
    session: Session = Depends(get_session),
    current_user: dict = Depends(require_roles(AuthRole.DOCTOR))
):
    doctor = session.exec(
        select(Doctor).where(Doctor.auth_id == current_user["user_id"])
    ).first()

    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor profile not found")

    status = session.exec(
        select(AppointmentStatus).where(
            AppointmentStatus.status_name == "COMPLETED"
        )
    ).first()

    if not status:
        raise HTTPException(status_code=400, detail="Invalid status")

    appointment = session.exec(
        select(Appointment)
        .join(OPD)
        .where(
            Appointment.id == appointment_id,
            OPD.doctor_id == doctor.id,
        )
    ).first()

    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    appointment.appointment_status_id = status.id  # type: ignore
    session.add(appointment)
    session.commit()

    return {"message": f"Appointment marked as {status.status_name}"}
