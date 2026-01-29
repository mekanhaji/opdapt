# OPDapt - Appointment Management System

A FastAPI-based appointment management system for managing doctor OPD (Out-Patient Department) schedules and patient appointments.

## Tech Stack

- **Framework**: FastAPI
- **Database**: SQLite with SQLModel (ORM)
- **Authentication**: JWT with passlib (Argon2 hashing)
- **Password Hashing**: Argon2
- **Python Version**: 3.12+

## Project Structure

```
opdapt/
├── app.py                    # FastAPI application entry point
├── config.py                 # Configuration (SECRET_KEY, ALGORITHM, tokens)
├── pyproject.toml           # Project dependencies
├── api/                      # API routes
│   ├── auth.py              # Authentication & user registration
│   ├── opd.py               # OPD schedule management
│   ├── appointment.py        # Appointment availability & booking
│   └── router.py            # Route aggregation
├── core/                     # Core utilities
│   ├── security.py          # Password hashing & verification
│   └── jwt.py               # JWT token creation & decoding
├── dependencies/             # FastAPI dependencies
│   └── auth.py              # Authentication dependencies & role checks
├── models/                   # SQLModel data models
│   ├── users.py             # Auth, Admin, Doctor, Patient models
│   ├── appointment.py        # OPD, Appointment, AppointmentType, AppointmentStatus
│   ├── base.py              # Base model with timestamps
│   └── __init__.py          # Database engine & session management
└── README.md
```

## Features

### Authentication & Authorization

- User registration for patients, doctors, and admins
- JWT-based authentication
- Role-based access control (RBAC)
- Argon2 password hashing

### OPD Management

- Doctors create and manage OPD schedules
- Time-based OPD sessions with patient limits
- Weekly recurring schedules (bitmask-based day selection)
- Average appointment duration tracking

### Appointment System

- Dynamic slot generation based on OPD schedules
- Existing appointment filtering
- Date range queries for available slots
- Unique constraint on OPD + appointment datetime

## Installation & Setup

### Prerequisites

- Python 3.12+
- `uv` package manager

### Install Dependencies

```bash
uv sync
```

### Run the Application

```bash
uv run fastapi dev app.py
```

The server will start at `http://localhost:8000`

### API Documentation

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Database

SQLite database file: `opdapt.db` (auto-created on first run)

### Key Models

**Auth** - User credentials & roles

- phone_number (unique, 10-15 chars)
- password_hash (hashed with Argon2)
- role (admin, doctor, patient)
- is_active (boolean)

**Doctor** - Doctor profiles linked to Auth
**Patient** - Patient profiles linked to Auth
**Admin** - Admin profiles linked to Auth

**OPD** - Doctor's clinic sessions

- name, starting_time, ending_time
- patient_limit (1-100)
- avg_opd_time (appointment duration in minutes)
- day_of_week_mask (bitmask: Sun=bit0, Sat=bit6)

**Appointment** - Scheduled patient appointments

- appointment_datetime
- checked_in (boolean)
- Unique constraint on (opd_id, appointment_datetime)

## API Endpoints

### Authentication

- `POST /api/auth/login` - Login with phone & password
- `POST /api/auth/new-patient` - Register new patient
- `POST /api/auth/new-admin` - Register admin (doctor/admin only)
- `POST /api/auth/new-doctor` - Register doctor (doctor/admin only)

### OPD Management

- `POST /api/opd/` - Create OPD schedule (doctor only)
- `GET /api/opd/` - List OPD schedules
- `GET /api/opd/{doctor_id}` - List OPDs for doctor
- `GET /api/opd/{doctor_id}/today` - Today's OPD schedules

### Appointments

- `GET /api/appointment/{doctor_id}?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD` - Get available slots

## Notes

- This is a **personal project** - contributions are not needed
- Passwords are hashed with Argon2 for security
- JWT tokens expire based on `ACCESS_TOKEN_EXPIRE_MINUTES` config
- Role-based authorization enforced on protected routes
