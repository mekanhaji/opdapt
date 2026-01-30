# OPD Appointment Management System - API Design Documentation

## Overview

This document describes the complete API design for the OPD (Out-Patient Department) Appointment Management System. The API is built with FastAPI and provides endpoints for managing appointments, doctors, patients, and administrative operations.

**Base URL**: `/api`
**API Version**: 0.1.0

---

## Table of Contents

1. [Authentication](#authentication)
2. [Data Schemas](#data-schemas)
3. [Endpoints](#endpoints)
   - [Authentication Endpoints](#authentication-endpoints)
   - [Doctor Endpoints](#doctor-endpoints)
   - [Patient Endpoints](#patient-endpoints)
   - [Appointment Endpoints](#appointment-endpoints)
   - [OPD Endpoints](#opd-endpoints)
4. [Error Handling](#error-handling)
5. [Authorization & Roles](#authorization--roles)

---

## Authentication

### JWT Token-Based Authentication

The API uses JWT (JSON Web Tokens) for authentication. All protected endpoints require a valid JWT token in the `Authorization` header.

**Token Format**: `Authorization: Bearer <token>`

**Token Expiration**: 30 minutes (configurable via `ACCESS_TOKEN_EXPIRE_MINUTES`)

**Token Payload**:

```json
{
  "sub": "user_id",
  "role": "admin|doctor|patient"
}
```

### User Roles

Three user roles with different permission levels:

- **admin**: Can register users, manage OPD schedules, update appointment statuses
- **doctor**: Can manage their own OPD schedules, view appointments, check in patients
- **patient**: Can book appointments, view their appointments, cancel appointments

---

## Data Schemas

### Core User Models

#### Auth Model

User authentication and authorization entity.

```json
{
  "id": integer,
  "phone_number": string (10-15 chars, unique),
  "password_hash": string,
  "role": "admin" | "doctor" | "patient",
  "is_active": boolean,
  "created_at": ISO 8601 datetime,
  "updated_at": ISO 8601 datetime
}
```

#### Admin Model

Administrative user who manages the system.

```json
{
  "id": integer,
  "name": string (max 100 chars),
  "is_active": boolean,
  "auth_id": integer (foreign key to Auth),
  "created_at": ISO 8601 datetime,
  "updated_at": ISO 8601 datetime
}
```

#### Doctor Model

Healthcare provider managing OPD schedules and appointments.

```json
{
  "id": integer,
  "name": string (max 100 chars),
  "is_available": boolean,
  "auth_id": integer (foreign key to Auth),
  "opds": array[OPD],
  "created_at": ISO 8601 datetime,
  "updated_at": ISO 8601 datetime
}
```

#### Patient Model

End user who books appointments.

```json
{
  "id": integer,
  "name": string (max 100 chars),
  "is_active": boolean,
  "auth_id": integer (foreign key to Auth),
  "appointments": array[Appointment],
  "created_at": ISO 8601 datetime,
  "updated_at": ISO 8601 datetime
}
```

### Appointment-Related Models

#### OPD Model

Out-Patient Department schedule defining when a doctor is available.

```json
{
  "id": integer,
  "name": string (max 100 chars),
  "starting_time": time (HH:MM:SS),
  "ending_time": time (HH:MM:SS),
  "patient_limit": integer (1-100, default: 20),
  "avg_opd_time": integer (1-60 minutes, default: 5),
  "day_of_week_mask": integer (0-127, bitmask: 0=Sunday, 1=Monday, ..., 6=Saturday),
  "is_active": boolean,
  "doctor_id": integer (foreign key to Doctor),
  "appointments": array[Appointment],
  "created_at": ISO 8601 datetime,
  "updated_at": ISO 8601 datetime
}
```

**Day of Week Mask Example**:

- `0b0111110` (62) = Monday to Friday
- `0b1111111` (127) = All days
- `0b0100010` (34) = Monday and Friday

#### AppointmentType Model

Classification of appointment types (e.g., consultation, follow-up).

```json
{
  "id": integer,
  "type_name": string (max 100 chars, unique),
  "description": string (max 255 chars, optional),
  "is_active": boolean,
  "appointments": array[Appointment],
  "created_at": ISO 8601 datetime,
  "updated_at": ISO 8601 datetime
}
```

#### AppointmentStatus Model

Status tracking for appointments (e.g., scheduled, completed, cancelled).

```json
{
  "id": integer,
  "status_name": string (max 100 chars, unique),
  "description": string (max 255 chars, optional),
  "is_active": boolean,
  "appointments": array[Appointment],
  "created_at": ISO 8601 datetime,
  "updated_at": ISO 8601 datetime
}
```

#### Appointment Model

Individual appointment booking for a patient at a specific OPD slot.

```json
{
  "id": integer,
  "appointment_datetime": ISO 8601 datetime,
  "checked_in": boolean,
  "notes": string (max 500 chars, optional),
  "patient_id": integer (foreign key to Patient),
  "opd_id": integer (foreign key to OPD),
  "appointment_type_id": integer (foreign key to AppointmentType),
  "appointment_status_id": integer (foreign key to AppointmentStatus),
  "patient": Patient,
  "opd": OPD,
  "appointment_type": AppointmentType,
  "appointment_status": AppointmentStatus,
  "created_at": ISO 8601 datetime,
  "updated_at": ISO 8601 datetime
}
```

**Constraints**:

- Unique constraint on (opd_id, appointment_datetime)

---

## Endpoints

### Authentication Endpoints

#### `POST /api/auth/login`

Authenticate user and receive JWT token.

**Request Body**:

```json
{
  "phone_number": "9876543210",
  "password": "password123"
}
```

**Response** (200 OK):

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user_id": 1,
  "role": "doctor"
}
```

**Error Responses**:

- `401 Unauthorized`: Invalid phone number or password
- `403 Forbidden`: Account is inactive

---

#### `POST /api/auth/new-patient`

Register a new patient.

**Authentication**: Not required

**Request Body**:

```json
{
  "phone_number": "9876543210",
  "password": "password123",
  "name": "John Doe"
}
```

**Response** (200 OK):

```json
{
  "message": "Patient registered successfully",
  "patient_id": 1,
  "auth_id": 1
}
```

**Error Responses**:

- `400 Bad Request`: Phone number already registered

---

#### `POST /api/auth/new-doctor`

Register a new doctor.

**Authentication**: Required
**Roles**: `admin`, `doctor`

**Request Body**:

```json
{
  "phone_number": "9876543211",
  "password": "password123",
  "name": "Dr. Smith"
}
```

**Response** (200 OK):

```json
{
  "message": "Doctor registered successfully",
  "doctor_id": 2,
  "auth_id": 2
}
```

**Error Responses**:

- `400 Bad Request`: Phone number already registered
- `401 Unauthorized`: Not authenticated
- `403 Forbidden`: Insufficient permissions

---

#### `POST /api/auth/new-admin`

Register a new admin.

**Authentication**: Required
**Roles**: `admin`, `doctor`

**Request Body**:

```json
{
  "phone_number": "9876543212",
  "password": "password123",
  "name": "Admin User"
}
```

**Response** (200 OK):

```json
{
  "message": "Admin registered successfully",
  "admin_id": 1,
  "auth_id": 3
}
```

**Error Responses**:

- `400 Bad Request`: Phone number already registered
- `401 Unauthorized`: Not authenticated
- `403 Forbidden`: Insufficient permissions

---

#### `GET /api/auth/`

Verify authentication status.

**Authentication**: Required
**Roles**: All

**Response** (200 OK):

```json
{
  "message": "Hello from FastAPI + uv!",
  "user": {
    "user_id": 1,
    "role": "doctor"
  }
}
```

---

### Doctor Endpoints

#### `GET /api/doctor/profile`

Retrieve doctor's profile information.

**Authentication**: Required
**Roles**: `doctor`, `admin`

**Response** (200 OK):

```json
{
  "id": 2,
  "name": "Dr. Smith",
  "is_available": true,
  "created_at": "2026-01-30T10:00:00"
}
```

**Error Responses**:

- `401 Unauthorized`: Not authenticated
- `404 Not Found`: Doctor profile not found

---

#### `PATCH /api/doctor/availability`

Update doctor's availability status.

**Authentication**: Required
**Roles**: `doctor`, `admin`

**Request Body**:

```json
{
  "is_available": false,
  "doctor_id": null
}
```

**Note**: If role is `admin`, `doctor_id` is required to update another doctor's availability.

**Response** (200 OK):

```json
{
  "message": "Availability updated successfully"
}
```

**Error Responses**:

- `400 Bad Request`: Missing required fields for admin role
- `401 Unauthorized`: Not authenticated
- `404 Not Found`: Doctor profile not found

---

#### `GET /api/doctor/appointments?date=YYYY-MM-DD`

List appointments for a doctor on a specific date.

**Authentication**: Required
**Roles**: `doctor`

**Query Parameters**:

- `date` (required): Date in YYYY-MM-DD format

**Response** (200 OK):

```json
[
  {
    "appointment_id": 1,
    "datetime": "2026-02-01T09:00:00",
    "patient_name": "John Doe",
    "status": "scheduled",
    "checked_in": false
  }
]
```

**Error Responses**:

- `401 Unauthorized`: Not authenticated
- `404 Not Found`: Doctor profile not found

---

#### `GET /api/doctor/appointments/{appointment_id}`

Retrieve details of a specific appointment.

**Authentication**: Required
**Roles**: `doctor`

**Path Parameters**:

- `appointment_id` (required): ID of the appointment

**Response** (200 OK):

```json
{
  "appointment_id": 1,
  "patient": "John Doe",
  "type": "consultation",
  "notes": "Patient reported fever",
  "status": "scheduled",
  "checked_in": false
}
```

**Error Responses**:

- `401 Unauthorized`: Not authenticated
- `404 Not Found`: Doctor profile or appointment not found

---

#### `POST /api/doctor/appointments/{appointment_id}/check-in`

Check in a patient for their appointment.

**Authentication**: Required
**Roles**: `doctor`

**Path Parameters**:

- `appointment_id` (required): ID of the appointment

**Response** (200 OK):

```json
{
  "message": "Patient checked in"
}
```

**Error Responses**:

- `401 Unauthorized`: Not authenticated
- `404 Not Found`: Doctor profile or appointment not found

---

### Patient Endpoints

#### `GET /api/patient/profile`

Retrieve patient's profile information.

**Authentication**: Required
**Roles**: `patient`, `admin`, `doctor`

**Response** (200 OK):

```json
{
  "id": 1,
  "name": "John Doe",
  "is_active": true,
  "created_at": "2026-01-30T08:30:00"
}
```

**Error Responses**:

- `401 Unauthorized`: Not authenticated
- `404 Not Found`: Patient profile not found

---

#### `PATCH /api/patient/profile`

Update patient's profile information.

**Authentication**: Required
**Roles**: `patient`, `admin`, `doctor`

**Request Body**:

```json
{
  "patient_id": null,
  "name": "Jane Doe",
  "phone_number": "9876543220"
}
```

**Note**: If role is `admin` or `doctor`, `patient_id` is required.

**Response** (200 OK):

```json
{
  "message": "Profile updated successfully"
}
```

**Error Responses**:

- `400 Bad Request`: Phone number already in use or no fields provided
- `401 Unauthorized`: Not authenticated
- `404 Not Found`: Patient or auth record not found

---

#### `GET /api/patient/appointments/{appointment_id}`

Retrieve details of a patient's appointment.

**Authentication**: Required
**Roles**: `patient`

**Path Parameters**:

- `appointment_id` (required): ID of the appointment

**Response** (200 OK):

```json
{
  "appointment_id": 1,
  "doctor": "Dr. Smith",
  "opd": "General Consultation",
  "type": "consultation",
  "notes": "Regular checkup",
  "status": "scheduled"
}
```

**Error Responses**:

- `401 Unauthorized`: Not authenticated
- `404 Not Found`: Patient profile or appointment not found

---

#### `POST /api/patient/appointments/{appointment_id}/cancel`

Cancel a patient's appointment.

**Authentication**: Required
**Roles**: `patient`

**Path Parameters**:

- `appointment_id` (required): ID of the appointment to cancel

**Response** (200 OK):

```json
{
  "message": "Appointment cancelled successfully"
}
```

**Error Responses**:

- `401 Unauthorized`: Not authenticated
- `404 Not Found`: Patient profile, appointment not found, or CANCELLED status not found
- `500 Internal Server Error`: CANCELLED status not configured

---

#### `GET /api/patient/appointments/upcoming`

Get upcoming appointments for the patient.

**Authentication**: Required
**Roles**: `patient`

**Response** (200 OK):

```json
[
  {
    "appointment_id": 1,
    "doctor": "Dr. Smith",
    "opd": "General Consultation",
    "type": "consultation",
    "datetime": "2026-02-01T09:00:00",
    "status": "scheduled"
  }
]
```

**Error Responses**:

- `401 Unauthorized`: Not authenticated
- `404 Not Found`: Patient profile not found

---

### Appointment Endpoints

#### `POST /api/appointment/type/`

Create a new appointment type.

**Authentication**: Required
**Roles**: `admin`, `doctor`

**Request Body**:

```json
{
  "name": "Consultation",
  "description": "General consultation with doctor"
}
```

**Response** (200 OK):

```json
{
  "id": 1,
  "name": "Consultation",
  "description": "General consultation with doctor"
}
```

**Error Responses**:

- `401 Unauthorized`: Not authenticated
- `403 Forbidden`: Insufficient permissions

---

#### `POST /api/appointment/status/`

Create a new appointment status.

**Authentication**: Required
**Roles**: `admin`, `doctor`

**Request Body**:

```json
{
  "name": "scheduled",
  "description": "Appointment is scheduled"
}
```

**Response** (200 OK):

```json
{
  "id": 1,
  "name": "scheduled",
  "description": "Appointment is scheduled"
}
```

**Error Responses**:

- `401 Unauthorized`: Not authenticated
- `403 Forbidden`: Insufficient permissions

---

#### `GET /api/appointment/{doctor_id}/?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD`

Get available appointment slots for a doctor.

**Authentication**: Not required

**Path Parameters**:

- `doctor_id` (required): ID of the doctor

**Query Parameters**:

- `start_date` (required): Start date in YYYY-MM-DD format
- `end_date` (required): End date in YYYY-MM-DD format

**Behavior**:

- Fetches OPD schedules for the doctor
- Generates potential slots based on OPD times and average consultation duration
- Filters out already booked slots
- Returns available slots within the date range

**Response** (200 OK):

```json
{
  "appointments": [
    {
      "opd_id": 1,
      "doctor_id": 2,
      "date": "2026-02-01",
      "start_time": "09:00",
      "end_time": "09:05"
    },
    {
      "opd_id": 1,
      "doctor_id": 2,
      "date": "2026-02-01",
      "start_time": "09:05",
      "end_time": "09:10"
    }
  ]
}
```

**Error Responses**:

- `400 Bad Request`: end_date is before start_date

---

#### `POST /api/appointment/book/`

Book an appointment for a patient.

**Authentication**: Not required (but recommended for audit trail)

**Request Body**:

```json
{
  "opd_id": 1,
  "patient_id": 1,
  "appointment_datetime": "2026-02-01T09:00:00",
  "appointment_type_id": 1,
  "appointment_status_id": 1
}
```

**Response** (200 OK):

```json
{
  "message": "Appointment booked successfully",
  "appointment_id": 1
}
```

**Error Responses**:

- `400 Bad Request`: Requested slot already booked
- `404 Not Found`: OPD not found or inactive

---

### OPD Endpoints

#### `POST /api/opd/`

Create a new OPD schedule for a doctor.

**Authentication**: Required
**Roles**: `doctor`

**Request Body**:

```json
{
  "name": "General Consultation",
  "starting_time": "09:00:00",
  "ending_time": "12:00:00",
  "patient_limit": 20,
  "avg_opd_time": 5,
  "day_of_week_mask": [1, 2, 3, 4, 5]
}
```

**Note**: `day_of_week_mask` is a list of day indices (0=Sunday, 1=Monday, ..., 6=Saturday).

**Response** (200 OK):

```json
{
  "message": "OPD created successfully",
  "opd_id": 1,
  "doctor_id": 2
}
```

**Error Responses**:

- `400 Bad Request`: ending_time must be greater than starting_time
- `401 Unauthorized`: Not authenticated
- `404 Not Found`: Doctor profile not found

---

#### `GET /api/opd/`

List OPD schedules.

**Authentication**: Required
**Roles**: All

**Behavior**:

- Doctors can see their own OPD schedules
- Non-doctors can see all active OPD schedules

**Response** (200 OK):

```json
{
  "opd_records": [
    {
      "id": 1,
      "name": "General Consultation",
      "starting_time": "09:00:00",
      "ending_time": "12:00:00",
      "patient_limit": 20,
      "avg_opd_time": 5,
      "day_of_week_mask": [1, 2, 3, 4, 5],
      "is_active": true,
      "doctor_id": 2,
      "created_at": "2026-01-30T10:00:00"
    }
  ]
}
```

**Error Responses**:

- `401 Unauthorized`: Not authenticated
- `404 Not Found`: Doctor profile not found (for doctors)

---

#### `GET /api/opd/{doctor_id}`

List OPD schedules for a specific doctor.

**Authentication**: Required

**Path Parameters**:

- `doctor_id` (required): ID of the doctor

**Response** (200 OK):

```json
[
  {
    "id": 1,
    "name": "General Consultation",
    "starting_time": "09:00:00",
    "ending_time": "12:00:00",
    "patient_limit": 20,
    "avg_opd_time": 5,
    "day_of_week_mask": [1, 2, 3, 4, 5],
    "is_active": true,
    "doctor_id": 2,
    "created_at": "2026-01-30T10:00:00"
  }
]
```

---

#### `GET /api/opd/{doctor_id}/today`

List OPD schedules running today for a doctor.

**Authentication**: Not required

**Path Parameters**:

- `doctor_id` (required): ID of the doctor

**Behavior**:

- Filters OPD schedules by current day of the week
- Returns only active schedules for today

**Response** (200 OK):

```json
[
  {
    "id": 1,
    "name": "General Consultation",
    "starting_time": "09:00:00",
    "ending_time": "12:00:00",
    "patient_limit": 20,
    "avg_opd_time": 5,
    "day_of_week_mask": [1, 2, 3, 4, 5],
    "is_active": true,
    "doctor_id": 2
  }
]
```

---

#### `PATCH /api/opd/{opd_id}`

Update an OPD schedule.

**Authentication**: Required
**Roles**: `doctor` (own OPD only), `admin`

**Path Parameters**:

- `opd_id` (required): ID of the OPD to update

**Request Body** (all fields optional):

```json
{
  "name": "Updated Consultation",
  "starting_time": "09:30:00",
  "ending_time": "13:00:00",
  "patient_limit": 25,
  "avg_opd_time": 6,
  "day_of_week_mask": [1, 2, 3, 4, 5, 6],
  "is_active": true
}
```

**Response** (200 OK):

```json
{
  "message": "OPD updated successfully"
}
```

**Error Responses**:

- `400 Bad Request`: Invalid data or constraints violated
- `401 Unauthorized`: Not authenticated
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: OPD not found

---

## Error Handling

All error responses follow a standard format:

```json
{
  "detail": "Error message describing what went wrong"
}
```

### HTTP Status Codes

- `200 OK`: Successful request
- `201 Created`: Resource created successfully
- `400 Bad Request`: Invalid request data or validation error
- `401 Unauthorized`: Missing or invalid authentication
- `403 Forbidden`: Authenticated but insufficient permissions
- `404 Not Found`: Resource not found
- `500 Internal Server Error`: Server-side error

---

## Authorization & Roles

### Role-Based Access Control (RBAC)

| Endpoint                                | Admin | Doctor | Patient |
| --------------------------------------- | ----- | ------ | ------- |
| POST /auth/login                        | ✓     | ✓      | ✓       |
| POST /auth/new-patient                  | ✓     | ✓      | ✗       |
| POST /auth/new-doctor                   | ✓     | ✓      | ✗       |
| POST /auth/new-admin                    | ✓     | ✓      | ✗       |
| GET /doctor/profile                     | ✓     | ✓      | ✗       |
| PATCH /doctor/availability              | ✓     | ✓      | ✗       |
| GET /doctor/appointments                | ✓     | ✓\*    | ✗       |
| GET /doctor/appointments/{id}           | ✓     | ✓\*    | ✗       |
| POST /doctor/appointments/{id}/check-in | ✓     | ✓\*    | ✗       |
| GET /patient/profile                    | ✓     | ✓      | ✓\*     |
| PATCH /patient/profile                  | ✓     | ✓      | ✓\*     |
| GET /patient/appointments/{id}          | ✓     | ✓      | ✓\*     |
| POST /patient/appointments/{id}/cancel  | ✓     | ✓      | ✓\*     |
| GET /patient/appointments/upcoming      | ✓     | ✓      | ✓\*     |
| POST /appointment/type                  | ✓     | ✓      | ✗       |
| POST /appointment/status                | ✓     | ✓      | ✗       |
| GET /appointment/{doctor_id}            | ✓     | ✓      | ✓       |
| POST /appointment/book                  | ✓     | ✓      | ✓       |
| POST /opd/                              | ✓     | ✓\*    | ✗       |
| GET /opd/                               | ✓     | ✓\*    | ✓       |
| GET /opd/{doctor_id}                    | ✓     | ✓      | ✓       |
| GET /opd/{doctor_id}/today              | ✓     | ✓      | ✓       |
| PATCH /opd/{opd_id}                     | ✓     | ✓\*    | ✗       |

_\* = Can only access/modify own data_

---

## Security Considerations

1. **Password Security**: Passwords are hashed using secure algorithms before storage
2. **JWT Expiration**: Access tokens expire after 30 minutes for enhanced security
3. **Phone Number Validation**: Phone numbers must be 10-15 characters long
4. **Unique Constraints**: Phone numbers and certain fields are enforced as unique at the database level
5. **Foreign Key Constraints**: Referential integrity is maintained at the database level

---

## Notes

- All timestamps are in UTC format (ISO 8601)
- The `day_of_week_mask` uses a bitmask system for efficient storage (0-127)
- Appointments have a unique constraint preventing double booking at the same time slot
- Database operations are transactional with proper rollback on failures
