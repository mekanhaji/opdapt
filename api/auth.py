from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from config import ACCESS_TOKEN_EXPIRE_MINUTES
from core.jwt import create_access_token
from core.security import hash_password, verify_password
from dependencies.auth import get_current_user
from models import get_session
from models.users import AuthRole, Auth, Patient

router = APIRouter(prefix="/auth", tags=["Auth"])


class PatientRegisterRequest(BaseModel):
    phone_number: str
    password: str
    name: str


class LoginRequest(BaseModel):
    phone_number: str
    password: str


@router.get("/")
def read_root(current_user: dict = Depends(get_current_user)):
    return {"message": "Hello from FastAPI + uv!", "user": current_user}


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
        password_hash=hash_password(request.password),
        role=AuthRole.PATIENT
    )
    session.add(auth)
    session.flush()  # Flush to get the auth.id

    # Ensure auth.id is not None before creating patient record
    if auth.id is None:
        session.rollback()
        raise HTTPException(
            status_code=500, detail="Failed to create auth record")

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


@router.post("/login")
def login(
    request: LoginRequest,
    session: Session = Depends(get_session)
):
    # Find user by phone number
    auth = session.exec(
        select(Auth).where(Auth.phone_number == request.phone_number)
    ).first()

    if not auth:
        raise HTTPException(
            status_code=401,
            detail="Invalid phone number or password"
        )

    # Verify password
    if not verify_password(request.password, auth.password_hash):
        raise HTTPException(
            status_code=401,
            detail="Invalid phone number or password"
        )

    # Check if user is active
    if not auth.is_active:
        raise HTTPException(
            status_code=403,
            detail="Account is inactive"
        )

    # Create access token
    access_token = create_access_token(
        data={"sub": str(auth.id), "role": auth.role},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": auth.id,
        "role": auth.role
    }
