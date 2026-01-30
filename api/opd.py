from datetime import time
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlmodel import Session, select, col

from dependencies.auth import get_current_user, require_roles
from models import get_session
from models.users import AuthRole, Doctor
from models.appointment import OPD

router = APIRouter(prefix="/opd", tags=["OPD"])


class OPDCreateRequest(BaseModel):
    name: str
    starting_time: time
    ending_time: time
    patient_limit: int = 20
    avg_opd_time: int = 5
    day_of_week_mask: list[int] = [0, 0, 0, 0, 0, 0, 0]  # Sunday to Saturday


class OPDUpdateRequest(BaseModel):
    name: Optional[str] = None
    starting_time: Optional[time] = None
    ending_time: Optional[time] = None
    patient_limit: Optional[int] = None
    avg_opd_time: Optional[int] = None
    day_of_week_mask: Optional[list[int]] = None
    is_active: Optional[bool] = None


def week_list_to_bit_mask(week_list: list[int]) -> int:
    """
    Docstring for week_list_to_bit_mask
    example: [0,2,4] -> 0b00010101 -> 21
    0 - Sunday
    1 - Monday
    2 - Tuesday
    3 - Wednesday
    4 - Thursday
    5 - Friday
    6 - Saturday
    """
    bit_mask = 0
    for day in week_list:
        bit_mask |= (1 << day)
    return bit_mask


def week_bit_mask_to_list(bit_mask: int) -> list[int]:
    """
    Docstring for week_bit_mask_to_list
    example: 21 -> 0b00010101 -> [0,2,4]
    """
    week_list = []
    for i in range(7):
        if (bit_mask >> i) & 1:
            week_list.append(i)
    return week_list


@router.post("/")
def create_opd_record(
    request: OPDCreateRequest,
    session: Session = Depends(get_session),
    current_user: dict = Depends(
        require_roles(AuthRole.DOCTOR))
):
    # Validate time constraints
    if request.ending_time <= request.starting_time:
        raise HTTPException(
            status_code=400,
            detail="ending_time must be greater than starting_time"
        )

    # Get the doctor associated with current user
    doctor = session.exec(
        select(Doctor).where(Doctor.auth_id == current_user["user_id"])
    ).first()

    if not doctor:
        raise HTTPException(
            status_code=404,
            detail="Doctor profile not found"
        )

    day_mask = week_list_to_bit_mask(request.day_of_week_mask)

    opd = OPD(
        name=request.name,
        starting_time=request.starting_time,
        ending_time=request.ending_time,
        patient_limit=request.patient_limit,
        avg_opd_time=request.avg_opd_time,
        day_of_week_mask=day_mask,
        doctor_id=doctor.id  # type: ignore
    )
    session.add(opd)
    session.commit()
    session.refresh(opd)

    return {
        "message": "OPD created successfully",
        "opd_id": opd.id,
        "doctor_id": doctor.id
    }


@router.get("/")
def list_opd_records(
    session: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user)
):
    query = select(OPD)

    if current_user["role"] == AuthRole.DOCTOR.value:
        # Get the doctor associated with current user
        doctor = session.exec(
            select(Doctor).where(Doctor.auth_id == current_user["user_id"])
        ).first()

        if not doctor:
            raise HTTPException(
                status_code=404,
                detail="Doctor profile not found"
            )

        query = query.where(OPD.doctor_id == doctor.id)

    opd_records = session.exec(query).all()

    result = []
    for opd in opd_records:
        opd_dict = opd.dict() if hasattr(opd, "dict") else dict(opd)
        opd_dict["day_of_week_mask"] = week_bit_mask_to_list(
            opd.day_of_week_mask)
        result.append(opd_dict)
    opd_records = result

    return {
        "opd_records": opd_records
    }


@router.get("/{doctor_id}")
def list_opd_records_for_doctor(
    doctor_id: int,
    session: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user)
):
    opd_records = session.exec(
        select(OPD).where(OPD.doctor_id == doctor_id)
    ).all()

    result = []
    for opd in opd_records:
        opd_dict = opd.dict() if hasattr(opd, "dict") else dict(opd)
        opd_dict["day_of_week_mask"] = week_bit_mask_to_list(
            opd.day_of_week_mask)
        result.append(opd_dict)
    opd_records = result

    return opd_records


@router.get("/{doctor_id}/today")
def list_today_opd_records_for_doctor(
    doctor_id: int,
    session: Session = Depends(get_session)
):
    from datetime import datetime
    today_weekday = datetime.now().weekday()  # Monday is 0 and Sunday is 6
    # Adjust to make Sunday 0
    today_weekday = (today_weekday + 1) % 7

    opd_records = session.exec(
        select(OPD).where(
            OPD.doctor_id == doctor_id,
            (col(OPD.day_of_week_mask).op('&')(1 << today_weekday)) != 0
        )
    ).all()

    result = []
    for opd in opd_records:
        opd_dict = opd.dict() if hasattr(opd, "dict") else dict(opd)
        opd_dict["day_of_week_mask"] = week_bit_mask_to_list(
            opd.day_of_week_mask)
        result.append(opd_dict)
    opd_records = result

    return opd_records


@router.patch("/{opd_id}")
def update_opd(
    opd_id: int,
    request: OPDUpdateRequest,
    session: Session = Depends(get_session),
    current_user: dict = Depends(
        require_roles(AuthRole.DOCTOR, AuthRole.ADMIN))
):
    opd = session.exec(
        select(OPD).where(OPD.id == opd_id)
    ).first()

    if not opd:
        raise HTTPException(status_code=404, detail="OPD not found")

    if current_user.get("role") == AuthRole.DOCTOR.value:
        doctor = session.exec(
            select(Doctor).where(Doctor.auth_id == current_user["user_id"])
        ).first()

        if not doctor:
            raise HTTPException(
                status_code=404, detail="Doctor profile not found")

        if opd.doctor_id != doctor.id:
            raise HTTPException(status_code=403, detail="Not authorized")

    updated = False

    if request.name is not None:
        opd.name = request.name
        updated = True

    if request.starting_time is not None or request.ending_time is not None:
        new_start = request.starting_time or opd.starting_time
        new_end = request.ending_time or opd.ending_time
        if new_end <= new_start:
            raise HTTPException(
                status_code=400,
                detail="ending_time must be greater than starting_time"
            )
        opd.starting_time = new_start
        opd.ending_time = new_end
        updated = True

    if request.patient_limit is not None:
        opd.patient_limit = request.patient_limit
        updated = True

    if request.avg_opd_time is not None:
        opd.avg_opd_time = request.avg_opd_time
        updated = True

    if request.day_of_week_mask is not None:
        opd.day_of_week_mask = week_list_to_bit_mask(request.day_of_week_mask)
        updated = True

    if request.is_active is not None:
        opd.is_active = request.is_active
        updated = True

    if not updated:
        raise HTTPException(
            status_code=400, detail="No fields provided to update")

    session.add(opd)
    session.commit()

    return {"message": "OPD updated successfully"}
