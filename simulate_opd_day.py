"""Simulate one OPD day with at least 3 doctors.

This script seeds demo data (doctors, patients, OPDs, appointment types/statuses)
and books a handful of appointments for today.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Iterable

from sqlmodel import Session, select

from core.security import hash_password
from models import create_db_and_tables, engine
from models.appointment import Appointment, AppointmentStatus, AppointmentType, OPD
from models.users import Auth, AuthRole, Doctor, Patient


def get_or_create_auth(
    session: Session,
    *,
    phone_number: str,
    password: str,
    role: AuthRole,
) -> Auth:
    auth = session.exec(
        select(Auth).where(Auth.phone_number == phone_number)
    ).first()
    if auth:
        return auth

    auth = Auth(
        phone_number=phone_number,
        password_hash=hash_password(password),
        role=role,
    )
    session.add(auth)
    session.commit()
    session.refresh(auth)
    return auth


def get_or_create_doctor(
    session: Session,
    *,
    name: str,
    phone_number: str,
    password: str,
) -> Doctor:
    auth = get_or_create_auth(
        session,
        phone_number=phone_number,
        password=password,
        role=AuthRole.DOCTOR,
    )
    doctor = session.exec(
        select(Doctor).where(Doctor.auth_id == auth.id)
    ).first()
    if doctor:
        return doctor

    doctor = Doctor(name=name, auth_id=auth.id)  # type: ignore[arg-type]
    session.add(doctor)
    session.commit()
    session.refresh(doctor)
    return doctor


def get_or_create_patient(
    session: Session,
    *,
    name: str,
    phone_number: str,
    password: str,
) -> Patient:
    auth = get_or_create_auth(
        session,
        phone_number=phone_number,
        password=password,
        role=AuthRole.PATIENT,
    )
    patient = session.exec(
        select(Patient).where(Patient.auth_id == auth.id)
    ).first()
    if patient:
        return patient

    patient = Patient(name=name, auth_id=auth.id)  # type: ignore[arg-type]
    session.add(patient)
    session.commit()
    session.refresh(patient)
    return patient


def get_or_create_appointment_status(
    session: Session,
    *,
    status_name: str,
    description: str | None = None,
) -> AppointmentStatus:
    status = session.exec(
        select(AppointmentStatus).where(
            AppointmentStatus.status_name == status_name)
    ).first()
    if status:
        return status

    status = AppointmentStatus(
        status_name=status_name, description=description)
    session.add(status)
    session.commit()
    session.refresh(status)
    return status


def get_or_create_appointment_type(
    session: Session,
    *,
    type_name: str,
    description: str | None = None,
) -> AppointmentType:
    appt_type = session.exec(
        select(AppointmentType).where(AppointmentType.type_name == type_name)
    ).first()
    if appt_type:
        return appt_type

    appt_type = AppointmentType(type_name=type_name, description=description)
    session.add(appt_type)
    session.commit()
    session.refresh(appt_type)
    return appt_type


def get_or_create_opd(
    session: Session,
    *,
    doctor_id: int,
    name: str,
    starting_time: time,
    ending_time: time,
    avg_opd_time: int,
    day_of_week_mask: int,
) -> OPD:
    opd = session.exec(
        select(OPD).where(
            OPD.doctor_id == doctor_id,
            OPD.name == name,
            OPD.starting_time == starting_time,
            OPD.ending_time == ending_time,
        )
    ).first()
    if opd:
        if not opd.is_active:
            opd.is_active = True
        opd.day_of_week_mask = day_of_week_mask
        opd.avg_opd_time = avg_opd_time
        session.add(opd)
        session.commit()
        session.refresh(opd)
        return opd

    opd = OPD(
        name=name,
        starting_time=starting_time,
        ending_time=ending_time,
        avg_opd_time=avg_opd_time,
        day_of_week_mask=day_of_week_mask,
        doctor_id=doctor_id,
    )
    session.add(opd)
    session.commit()
    session.refresh(opd)
    return opd


def generate_slots_for_day(opd: OPD, appt_date: date) -> list[datetime]:
    slot_start = datetime.combine(appt_date, opd.starting_time)
    slot_end_limit = datetime.combine(appt_date, opd.ending_time)
    step = timedelta(minutes=opd.avg_opd_time)

    slots: list[datetime] = []
    while slot_start + step <= slot_end_limit:
        slots.append(slot_start)
        slot_start += step

    return slots


def book_appointments(
    session: Session,
    *,
    opd: OPD,
    patient_ids: Iterable[int],
    appointment_type_id: int,
    appointment_status_id: int,
    appt_date: date,
    max_bookings: int,
) -> int:
    booked_count = 0
    slots = generate_slots_for_day(opd, appt_date)

    for slot_time in slots:
        if booked_count >= max_bookings:
            break

        existing = session.exec(
            select(Appointment).where(
                Appointment.opd_id == opd.id,
                Appointment.appointment_datetime == slot_time,
            )
        ).first()
        if existing:
            continue

        patient_id = list(patient_ids)[booked_count % len(list(patient_ids))]
        appointment = Appointment(
            opd_id=opd.id,  # type: ignore
            patient_id=patient_id,
            appointment_datetime=slot_time,
            appointment_type_id=appointment_type_id,
            appointment_status_id=appointment_status_id,
        )
        session.add(appointment)
        session.commit()
        session.refresh(appointment)
        booked_count += 1

    return booked_count


def simulate_opd_day() -> None:
    create_db_and_tables()

    today = date.today()
    weekday = (today.weekday() + 1) % 7  # Sunday=0
    day_mask = 1 << weekday

    with Session(engine) as session:
        scheduled_status = get_or_create_appointment_status(
            session,
            status_name="SCHEDULED",
            description="Appointment is scheduled",
        )
        consultation_type = get_or_create_appointment_type(
            session,
            type_name="CONSULTATION",
            description="General consultation",
        )

        doctors = [
            get_or_create_doctor(
                session,
                name="Dr. Asha Nair",
                phone_number="9000000001",
                password="doctor123",
            ),
            get_or_create_doctor(
                session,
                name="Dr. Rahul Mehta",
                phone_number="9000000002",
                password="doctor123",
            ),
            get_or_create_doctor(
                session,
                name="Dr. Priya Iyer",
                phone_number="9000000003",
                password="doctor123",
            ),
        ]

        patients = [
            get_or_create_patient(
                session,
                name="Patient One",
                phone_number="9100000001",
                password="patient123",
            ),
            get_or_create_patient(
                session,
                name="Patient Two",
                phone_number="9100000002",
                password="patient123",
            ),
            get_or_create_patient(
                session,
                name="Patient Three",
                phone_number="9100000003",
                password="patient123",
            ),
            get_or_create_patient(
                session,
                name="Patient Four",
                phone_number="9100000004",
                password="patient123",
            ),
        ]

        patient_ids = [
            patient.id for patient in patients if patient.id is not None]

        print(f"Simulating OPD day for {today.isoformat()}\n")

        total_booked = 0
        for idx, doctor in enumerate(doctors, start=1):
            opd = get_or_create_opd(
                session,
                doctor_id=doctor.id,  # type: ignore[arg-type]
                name=f"OPD Session {idx}",
                starting_time=time(9, 0),
                ending_time=time(12, 0),
                avg_opd_time=15,
                day_of_week_mask=day_mask,
            )

            booked = book_appointments(
                session,
                opd=opd,
                patient_ids=patient_ids,
                # type: ignore[arg-type]
                appointment_type_id=consultation_type.id,  # type: ignore
                # type: ignore[arg-type]
                appointment_status_id=scheduled_status.id,  # type: ignore
                appt_date=today,
                max_bookings=4,
            )
            total_booked += booked

            print(
                f"Doctor: {doctor.name} | OPD: {opd.name} | "
                f"Booked: {booked} appointments"
            )

        print(f"\nTotal appointments booked: {total_booked}")


if __name__ == "__main__":
    simulate_opd_day()
