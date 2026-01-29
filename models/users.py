from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlmodel import Field, Relationship

from .base import Base

if TYPE_CHECKING:
    from .appointment import OPD, Appointment


class AuthRole(str, Enum):
    ADMIN = "admin"
    DOCTOR = "doctor"
    PATIENT = "patient"


class Auth(Base, table=True):
    """
    Authentication and authorization table.
    Handles login credentials and role-based access.
    """
    phone_number: str = Field(
        unique=True, index=True, max_length=15, min_length=10
    )
    password_hash: str = Field(max_length=255)
    role: AuthRole = Field(index=True)

    is_active: bool = Field(default=True)

    admin: Optional["Admin"] = Relationship(back_populates="auth")
    doctor: Optional["Doctor"] = Relationship(back_populates="auth")
    patient: Optional["Patient"] = Relationship(back_populates="auth")


class Admin(Base, table=True):
    """
    Desk admin who manages appointments and statuses.
    """
    name: str = Field(index=True, max_length=100)
    is_active: bool = Field(default=True)

    auth_id: int = Field(foreign_key="auth.id", unique=True)
    auth: Auth = Relationship(back_populates="admin")


class Doctor(Base, table=True):
    """Doctor who runs OPD slots"""
    name: str = Field(index=True, max_length=100)
    is_available: bool = Field(default=True)

    auth_id: int = Field(foreign_key="auth.id", unique=True)
    auth: Auth = Relationship(back_populates="doctor")

    opds: list["OPD"] = Relationship(back_populates="doctor")  # type: ignore


class Patient(Base, table=True):
    name: str = Field(index=True, max_length=100)
    is_active: bool = Field(default=True)

    auth_id: int = Field(foreign_key="auth.id", unique=True)
    auth: Auth = Relationship(back_populates="patient")

    appointments: list["Appointment"] = Relationship(
        back_populates="patient")  # type: ignore
