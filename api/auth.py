from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from config import ACCESS_TOKEN_EXPIRE_MINUTES
from core.jwt import create_access_token
from core.security import hash_password, verify_password
from dependencies.auth import get_current_user, require_roles
from models import get_session
from models.users import AuthRole, Auth, Admin, Doctor, Patient

router = APIRouter(prefix="/auth", tags=["Auth"])


class PatientRegisterRequest(BaseModel):
    phone_number: str
    password: str
    name: str


class AdminRegisterRequest(BaseModel):
    phone_number: str
    password: str
    name: str


class LoginRequest(BaseModel):
    phone_number: str
    password: str


def _create_auth_with_profile(
    *,
    session: Session,
    phone_number: str,
    password: str,
    name: str,
    role: AuthRole,
    profile_model
):
    existing_auth = session.exec(
        select(Auth).where(Auth.phone_number == phone_number)
    ).first()

    if existing_auth:
        raise HTTPException(
            status_code=400, detail="Phone number already registered")

    auth = Auth(
        phone_number=phone_number,
        password_hash=hash_password(password),
        role=role
    )
    session.add(auth)
    session.flush()

    if auth.id is None:
        session.rollback()
        raise HTTPException(
            status_code=500, detail="Failed to create auth record")

    profile = profile_model(
        name=name,
        auth_id=auth.id
    )
    session.add(profile)
    session.commit()

    return auth, profile


@router.get("/")
def read_root(current_user: dict = Depends(get_current_user)):
    return {"message": "Hello from FastAPI + uv!", "user": current_user}


@router.post("/new-doctor")
def register_doctor(
    request: AdminRegisterRequest,
    session: Session = Depends(get_session),
    _current_user: dict = Depends(
        require_roles(AuthRole.ADMIN, AuthRole.DOCTOR))
):
    auth, doctor = _create_auth_with_profile(
        session=session,
        phone_number=request.phone_number,
        password=request.password,
        name=request.name,
        role=AuthRole.DOCTOR,
        profile_model=Doctor
    )

    return {
        "message": "Doctor registered successfully",
        "doctor_id": doctor.id,
        "auth_id": auth.id
    }


@router.post("/new-admin")
def register_admin(
    request: AdminRegisterRequest,
    session: Session = Depends(get_session),
    _current_user: dict = Depends(
        require_roles(AuthRole.ADMIN, AuthRole.DOCTOR))
):
    auth, admin = _create_auth_with_profile(
        session=session,
        phone_number=request.phone_number,
        password=request.password,
        name=request.name,
        role=AuthRole.ADMIN,
        profile_model=Admin
    )

    return {
        "message": "Admin registered successfully",
        "admin_id": admin.id,
        "auth_id": auth.id
    }


@router.post("/new-patient")
def register_patient(
    request: PatientRegisterRequest,
    session: Session = Depends(get_session)
):
    auth, patient = _create_auth_with_profile(
        session=session,
        phone_number=request.phone_number,
        password=request.password,
        name=request.name,
        role=AuthRole.PATIENT,
        profile_model=Patient
    )

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
