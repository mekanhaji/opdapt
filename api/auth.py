from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from models import get_session
from models.users import AuthRole, Auth, Patient

router = APIRouter(prefix="/auth", tags=["Auth"])


class PatientRegisterRequest(BaseModel):
    phone_number: str
    password: str
    name: str


@router.get("/")
def read_root():
    return {"message": "Hello from FastAPI + uv!"}


@router.post("/register")
def register():
    return {"message": "User registered"}


@router.post("/new-patient")
def register_patient(
    request: PatientRegisterRequest,
    session: Session = Depends(get_session)
):
    # Check if phone number already exists
    existing_auth = session.exec(
        select(Auth).where(Auth.phone_number == request.phone_number)
    ).first()

    if existing_auth:
        raise HTTPException(
            status_code=400, detail="Phone number already registered")

    # Create auth record
    auth = Auth(
        phone_number=request.phone_number,
        password_hash=request.password,  # TODO: Hash password properly
        role=AuthRole.PATIENT
    )
    session.add(auth)
    session.flush()  # Flush to get the auth.id

    # Ensure auth.id is not None before creating patient record
    if auth.id is None:
        session.rollback()
        raise HTTPException(status_code=500, detail="Failed to create auth record")

    # Create patient record
    patient = Patient(
        name=request.name,
        auth_id=auth.id
    )
    session.add(patient)
    session.commit()

    return {
        "message": "Patient registered successfully",
        "patient_id": patient.id,
        "auth_id": auth.id
    }
