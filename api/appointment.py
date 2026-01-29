from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlmodel import Session, select

from dependencies.auth import require_roles
from models import get_session
from models.appointment import Appointment, OPD, AppointmentStatus, AppointmentType
from models.users import AuthRole


router = APIRouter(prefix="/appointment", tags=["Appointment"])


class CreateAppointmentStatusRequest(BaseModel):
    name: str
    description: str | None = None


class CreateAppointmentTypeRequest(BaseModel):
    name: str
    description: str | None = None


class BookAppointmentRequest(BaseModel):
    opd_id: int
    patient_id: int
    appointment_datetime: datetime
    appointment_type_id: int
    appointment_status_id: int


@router.post("/type/")
def create_appointment_type(
    request: CreateAppointmentTypeRequest,
    session: Session = Depends(get_session),
    _current_user: dict = Depends(
        require_roles(AuthRole.ADMIN, AuthRole.DOCTOR)),
):
    """
    Create a new appointment type.
    Parameters:
    - name: Name of the appointment type.
    - description: Optional description of the appointment type.
    Returns:
    - Details of the created appointment type.
    """

    appointment_type = AppointmentType(
        type_name=request.name,
        description=request.description
    )
    session.add(appointment_type)
    session.commit()
    session.refresh(appointment_type)

    return {
        "id": appointment_type.id,
        "name": appointment_type.type_name,
        "description": appointment_type.description
    }


@router.post("/status/")
def create_appointment_status(
    request: CreateAppointmentStatusRequest,
    session: Session = Depends(get_session),
    _current_user: dict = Depends(
        require_roles(AuthRole.ADMIN, AuthRole.DOCTOR)),
):
    """
    Create a new appointment status.
    Parameters:
    - name: Name of the appointment status.
    - description: Optional description of the appointment status.
    Returns:
    - Details of the created appointment status.
    """
    appointment_status = AppointmentStatus(
        status_name=request.name,
        description=request.description
    )
    session.add(appointment_status)
    session.commit()
    session.refresh(appointment_status)

    return {
        "id": appointment_status.id,
        "name": appointment_status.status_name,
        "description": appointment_status.description
    }


@router.get("/{doctor_id}/")
def get_appointments(
    doctor_id: int,
    start_date: date = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: date = Query(..., description="End date (YYYY-MM-DD)"),
    session: Session = Depends(get_session),
):
    """
    Returns a list of appointments by doctor and date range.
    Compute appointments based on OPD schedules and existing bookings.
    1. Fetch OPD schedules for the specified doctor.
    2. Generate potential appointment slots based on the OPD schedule and avg opd time.
    3. Filter out slots that are already booked by searching existing appointments.
    Parameters:
    - doctor_id: ID of the doctor to fetch appointments for.
    - start_date: Start date of the range to fetch appointments.
    - end_date: End date of the range to fetch appointments.
    Returns:
    - List of available appointment slots within the specified date range.
    """
    if end_date < start_date:
        raise HTTPException(
            status_code=400,
            detail="end_date must be on or after start_date"
        )

    # Fetch OPD schedules for the specified doctor
    opds = session.exec(
        select(OPD).where(OPD.doctor_id == doctor_id, OPD.is_active)
    ).all()

    if not opds:
        return {"appointments": []}

    # Fetch existing appointments for the date range
    start_dt = datetime.combine(start_date, time.min)
    end_dt = datetime.combine(end_date + timedelta(days=1), time.min)
    appointments = session.exec(
        select(Appointment).where(
            Appointment.opd_id.in_([opd.id for opd in opds]),  # type: ignore
            Appointment.appointment_datetime >= start_dt,
            Appointment.appointment_datetime < end_dt,
        )
    ).all()

    booked = {(appt.opd_id, appt.appointment_datetime)
              for appt in appointments}

    available_slots: list[dict] = []
    total_days = (end_date - start_date).days

    for day_offset in range(total_days + 1):
        current_date = start_date + timedelta(days=day_offset)
        # Convert weekday to Sunday=0 .. Saturday=6
        weekday = (current_date.weekday() + 1) % 7

        for opd in opds:
            # Check if OPD runs on this day
            if (opd.day_of_week_mask & (1 << weekday)) == 0:
                continue

            slot_start = datetime.combine(current_date, opd.starting_time)
            slot_end_limit = datetime.combine(current_date, opd.ending_time)
            step = timedelta(minutes=opd.avg_opd_time)

            while slot_start + step <= slot_end_limit:
                if (opd.id, slot_start) not in booked:
                    available_slots.append({
                        "opd_id": opd.id,
                        "doctor_id": opd.doctor_id,
                        "date": current_date.isoformat(),
                        "start_time": slot_start.time().isoformat(timespec="minutes"),
                        "end_time": (slot_start + step).time().isoformat(timespec="minutes"),
                    })
                slot_start += step

    return {"appointments": available_slots}


@router.post("/book/")
def book_appointment(
    request: BookAppointmentRequest,
    session: Session = Depends(get_session),
):
    """
    Book an appointment for a given OPD at a specified datetime.
    Parameters:
    - opd_id: ID of the OPD to book the appointment for.
    - appointment_datetime: Desired datetime for the appointment.
    Returns:
    - Details of the booked appointment.
    """
    # Check if OPD exists and is active
    opd = session.get(OPD, request.opd_id)
    if not opd or not opd.is_active:
        raise HTTPException(
            status_code=404, detail="OPD not found or inactive")

    # Check if the appointment slot is already booked
    existing_appointment = session.exec(
        select(Appointment).where(
            Appointment.opd_id == request.opd_id,
            Appointment.appointment_datetime == request.appointment_datetime
        )
    ).first()

    if existing_appointment:
        raise HTTPException(
            status_code=400, detail="Appointment slot already booked")

    # Create new appointment
    appointment = Appointment(
        opd_id=request.opd_id,
        appointment_datetime=request.appointment_datetime,
        appointment_status_id=request.appointment_status_id,
        appointment_type_id=request.appointment_type_id,
        patient_id=request.patient_id
    )

    session.add(appointment)
    session.commit()
    session.refresh(appointment)

    return {
        "appointment_id": appointment.id,
        "opd_id": appointment.opd_id,
        "appointment_datetime": appointment.appointment_datetime.isoformat()
    }
