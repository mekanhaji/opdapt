from datetime import datetime, time
from typing import TYPE_CHECKING, Optional

from pydantic import field_validator
from sqlmodel import Field, Relationship, UniqueConstraint

from .base import Base

if TYPE_CHECKING:
    from .users import Doctor, Patient


class OPD(Base, table=True):
    """OPD details"""
    name: str = Field(index=True, max_length=100)
    starting_time: time = Field()  # Use proper time type
    ending_time: time = Field()  # Use proper time type
    # Minimum 1, maximum 100
    patient_limit: int = Field(default=20, ge=1, le=100)
    avg_opd_time: int = Field(default=5, ge=1, le=60)  # in minutes, 1-60 range
    # Bitmask: Monday=bit 0, Sunday=bit 6
    # 7 bits for 7 days, e.g. 0b0111110 means Mon–Fri
    day_of_week_mask: int = Field(default=0, ge=0, le=127)
    is_active: bool = Field(default=True)

    doctor_id: int = Field(foreign_key="doctor.id")

    doctor: "Doctor" = Relationship(back_populates="opds")
    appointments: list["Appointment"] = Relationship(back_populates="opd")

    @field_validator("ending_time")
    @classmethod
    def validate_ending_time(cls, v, info):
        if "starting_time" in info.data and v <= info.data["starting_time"]:
            raise ValueError("ending_time must be greater than starting_time")
        return v


class AppointmentType(Base, table=True):
    # TODO: add priority levels normal, high, emergency (currently priority is stored in discussion)
    type_name: str = Field(unique=True, index=True,
                           max_length=100)  # Unique constraint
    description: Optional[str] = Field(default=None, max_length=255)
    is_active: bool = Field(default=True)

    appointments: list["Appointment"] = Relationship(
        back_populates="appointment_type")


class AppointmentStatus(Base, table=True):
    status_name: str = Field(unique=True, index=True,
                             max_length=100)  # Unique constraint
    description: Optional[str] = Field(default=None, max_length=255)
    is_active: bool = Field(default=True)

    appointments: list["Appointment"] = Relationship(
        back_populates="appointment_status")


class Appointment(Base, table=True):
    appointment_datetime: datetime = Field(
        index=True)  # Use datetime instead of just time
    checked_in: bool = Field(default=False)
    notes: Optional[str] = Field(default=None, max_length=500)

    patient_id: int = Field(foreign_key="patient.id")
    opd_id: int = Field(foreign_key="opd.id")
    appointment_type_id: int = Field(foreign_key="appointmenttype.id")
    appointment_status_id: int = Field(foreign_key="appointmentstatus.id")

    patient: "Patient" = Relationship(back_populates="appointments")
    opd: "OPD" = Relationship(back_populates="appointments")
    appointment_type: "AppointmentType" = Relationship(
        back_populates="appointments")
    appointment_status: "AppointmentStatus" = Relationship(
        back_populates="appointments")

    __table_args__ = (
        UniqueConstraint("opd_id", "appointment_datetime",
                         name="uq_opd_appointment_datetime"),
    )
