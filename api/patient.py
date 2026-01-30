from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlmodel import Session, select

from dependencies.auth import require_roles
from models import get_session
from models.users import AuthRole, Patient, Auth, Doctor
from models.appointment import Appointment, AppointmentStatus, AppointmentType, OPD

router = APIRouter(prefix="/patient", tags=["Patient"])


class PatientProfileUpdateRequest(BaseModel):
    patient_id: Optional[int] = None
    name: Optional[str] = None
    phone_number: Optional[str] = None


@router.get("/profile")
def get_patient_profile(
        session: Session = Depends(get_session),
        current_user: dict = Depends(require_roles(
            AuthRole.PATIENT, AuthRole.ADMIN, AuthRole.DOCTOR))
):
    patient = session.exec(
        select(Patient).where(Patient.auth_id == current_user["user_id"])
    ).first()

    if not patient:
        raise HTTPException(
            status_code=404, detail="Patient profile not found")

    return {
        "id": patient.id,
        "name": patient.name,
        "is_active": patient.is_active,
        "created_at": patient.created_at
    }


@router.patch("/profile")
def update_patient_profile(
    request: PatientProfileUpdateRequest,
    session: Session = Depends(get_session),
    current_user: dict = Depends(require_roles(
        AuthRole.PATIENT, AuthRole.ADMIN, AuthRole.DOCTOR))
):
    patient_id = None

    if current_user.get("role") != AuthRole.PATIENT.value:
        if request.patient_id is None:
            raise HTTPException(
                status_code=400,
                detail="patient_id is required for admin"
            )
        patient_id = request.patient_id
    else:
        patient_id = current_user["user_id"]

    patient = session.exec(
        select(Patient).where(Patient.auth_id == patient_id)
    ).first()

    if not patient:
        raise HTTPException(
            status_code=404, detail="Patient profile not found")

    updated = False

    if request.name is not None:
        patient.name = request.name
        updated = True

    if request.phone_number is not None:
        auth = session.exec(
            select(Auth).where(Auth.id == patient_id)
        ).first()

        if not auth:
            raise HTTPException(
                status_code=404, detail="Auth record not found")

        # Check if phone number already exists for another user
        existing_auth = session.exec(
            select(Auth).where(
                Auth.phone_number == request.phone_number,
                Auth.id != patient_id
            )
        ).first()

        if existing_auth:
            raise HTTPException(
                status_code=400, detail="Phone number already in use")

        auth.phone_number = request.phone_number
        session.add(auth)
        updated = True

    if not updated:
        raise HTTPException(
            status_code=400, detail="No fields provided to update")

    session.add(patient)
    session.commit()

    return {"message": "Profile updated successfully"}


@router.get("/appointments/{appointment_id}")
def get_appointment_detail(
    appointment_id: int,
    session: Session = Depends(get_session),
    current_user: dict = Depends(require_roles(AuthRole.PATIENT))
):
    patient = session.exec(
        select(Patient).where(Patient.auth_id == current_user["user_id"])
    ).first()

    if not patient:
        raise HTTPException(
            status_code=404, detail="Patient profile not found")

    appointment = session.exec(
        select(Appointment)
        .join(OPD)
        .join(Doctor)
        .join(AppointmentType)
        .join(AppointmentStatus)
        .where(
            Appointment.id == appointment_id,
            Appointment.patient_id == patient.id,
        )
    ).first()

    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    return {
        "appointment_id": appointment.id,
        "doctor": appointment.opd.doctor.name,
        "opd": appointment.opd.name,
        "type": appointment.appointment_type.type_name,
        "notes": appointment.notes,
        "status": appointment.appointment_status.status_name
    }


@router.post("/appointments/{appointment_id}/cancel")
def cancel_appointment(
    appointment_id: int,
    session: Session = Depends(get_session),
    current_user: dict = Depends(require_roles(AuthRole.PATIENT))
):
    patient = session.exec(
        select(Patient).where(Patient.auth_id == current_user["user_id"])
    ).first()

    if not patient:
        raise HTTPException(
            status_code=404, detail="Patient profile not found")

    # Get CANCELLED status
    cancelled_status = session.exec(
        select(AppointmentStatus).where(
            AppointmentStatus.status_name == "CANCELLED"
        )
    ).first()

    if not cancelled_status:
        raise HTTPException(
            status_code=500, detail="CANCELLED status not found")

    # Get appointment and verify ownership
    appointment = session.exec(
        select(Appointment).where(
            Appointment.id == appointment_id,
            Appointment.patient_id == patient.id
        )
    ).first()

    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    appointment.appointment_status_id = cancelled_status.id  # type: ignore
    session.add(appointment)
    session.commit()

    return {"message": "Appointment cancelled successfully"}


@router.get("/appointments/upcoming")
def get_upcoming_appointments(
    session: Session = Depends(get_session),
    current_user: dict = Depends(require_roles(AuthRole.PATIENT))
):
    patient = session.exec(
        select(Patient).where(Patient.auth_id == current_user["user_id"])
    ).first()

    if not patient:
        raise HTTPException(
            status_code=404, detail="Patient profile not found")

    # Get cancelled status to filter it out
    cancelled_status = session.exec(
        select(AppointmentStatus).where(
            AppointmentStatus.status_name == "CANCELLED"
        )
    ).first()

    now = datetime.now()

    # Query for upcoming appointments (future and not cancelled)
    query = (
        select(Appointment, Doctor, OPD)
        .join(OPD)
        .join(Doctor)
        .where(
            Appointment.patient_id == patient.id,
            Appointment.appointment_datetime > now
        )
    )

    # Filter out cancelled appointments if status exists
    if cancelled_status:
        query = query.where(
            Appointment.appointment_status_id != cancelled_status.id
        )

    appointments = session.exec(query).all()

    upcoming_count = len(appointments)
    next_appointment = None

    if appointments:
        first_appointment, doctor, opd = appointments[0]
        next_appointment = {
            "doctor": doctor.name,
            "datetime": first_appointment.appointment_datetime.isoformat()
        }

    return {
        "upcoming_count": upcoming_count,
        "next_appointment": next_appointment
    }
