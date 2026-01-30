# Token Allocation Algorithm (Appointment Slot Generation)

## Overview

This document describes the token allocation algorithm used to generate available appointment slots for a doctor. The algorithm is implemented in the appointment availability endpoint and is responsible for computing unbooked time slots based on OPD schedules.

**Source of Truth**: Appointment availability logic in the appointment API route.

---

## Purpose

- Generate available appointment slots for a doctor within a date range.
- Respect OPD schedules (start/end time, day-of-week mask, average slot duration).
- Exclude slots already booked by existing appointments.

---

## Inputs

| Parameter    | Type | Description                                            |
| ------------ | ---- | ------------------------------------------------------ |
| `doctor_id`  | int  | Doctor whose OPD schedules are used to generate slots. |
| `start_date` | date | Inclusive start date for slot generation.              |
| `end_date`   | date | Inclusive end date for slot generation.                |

---

## Data Dependencies

### OPD (Schedule)

- `starting_time`: Time when OPD begins.
- `ending_time`: Time when OPD ends.
- `avg_opd_time`: Average time per appointment (minutes). Used as slot duration.
- `day_of_week_mask`: Bitmask for which days the OPD is active.
- `is_active`: Only active OPDs are considered.

### Appointment (Booking)

- `appointment_datetime`: Used to determine already booked slots.
- Unique constraint on `(opd_id, appointment_datetime)` ensures single booking per slot.

---

## Output

A list of available slots:

```json
{
  "appointments": [
    {
      "opd_id": 1,
      "doctor_id": 10,
      "date": "2026-02-01",
      "start_time": "09:00",
      "end_time": "09:05"
    }
  ]
}
```

---

## Algorithm Steps

1. **Validate Date Range**
   - Ensure `end_date` is on or after `start_date`.

2. **Fetch OPDs for the Doctor**
   - Load all active OPDs for `doctor_id`.
   - If none exist, return an empty result.

3. **Fetch Existing Appointments in Range**
   - Compute range bounds: `start_date 00:00` to `end_date + 1 day 00:00`.
   - Load all appointments whose `appointment_datetime` is within the range and whose `opd_id` is in the doctor’s OPDs.

4. **Create Booked Slot Set**
   - Convert appointments to a set of `(opd_id, appointment_datetime)` for $O(1)$ lookup.

5. **Iterate Date Range**
   - For each date from `start_date` to `end_date` (inclusive):
     - Convert weekday into Sunday=0..Saturday=6 format.

6. **Check OPD Day-of-Week**
   - Skip OPDs that are not active on the current weekday using bitmask check:
     - If `(day_of_week_mask & (1 << weekday)) == 0` then skip.

7. **Generate Slots**
   - Set `slot_start = date + starting_time`.
   - Set `slot_end_limit = date + ending_time`.
   - Set `step = avg_opd_time` minutes.
   - While `slot_start + step <= slot_end_limit`:
     - If `(opd_id, slot_start)` is **not** in booked set, append a slot.
     - Increment `slot_start` by `step`.

8. **Return Available Slots**
   - Return the aggregated list of available slots.

---

## Pseudocode

```text
function get_available_slots(doctor_id, start_date, end_date):
  if end_date < start_date:
      error

  opds = load_active_opds(doctor_id)
  if opds is empty:
      return []

  appointments = load_appointments(opds, start_date, end_date)
  booked = set((appt.opd_id, appt.datetime) for appt in appointments)

  slots = []
  for each date in [start_date .. end_date]:
      weekday = (date.weekday() + 1) % 7  // Sunday=0

      for each opd in opds:
          if (opd.day_of_week_mask & (1 << weekday)) == 0:
              continue

          slot_start = combine(date, opd.starting_time)
          slot_end_limit = combine(date, opd.ending_time)
          step = opd.avg_opd_time minutes

          while slot_start + step <= slot_end_limit:
              if (opd.id, slot_start) not in booked:
                  slots.add({
                      opd_id, doctor_id, date, start_time, end_time
                  })
              slot_start += step

  return slots
```

---

## Correctness Notes

- **No Overlaps**: Slots are generated at fixed intervals defined by `avg_opd_time`.
- **No Double Booking**: Booked slots are excluded using the `(opd_id, appointment_datetime)` set.
- **Day-of-Week Compliance**: Bitmask ensures slots are only generated for active days.
- **Date Bounds**: Start and end dates are inclusive.

---

## Prioritization Logic

The current implementation does **not** apply any explicit prioritization or ranking beyond deterministic generation order. Slots are produced in the following implicit order:

1. **Date order**: From `start_date` to `end_date` (inclusive).
2. **OPD order**: The iteration order returned by the OPD query.
3. **Time order**: Within each OPD, slots are generated from `starting_time` forward in fixed `avg_opd_time` increments.

If future prioritization is required (e.g., high‑priority appointment types, urgency flags, or doctor availability weighting), it should be applied as a post‑processing step on the generated list or integrated by changing the iteration order.

---

## Complexity

Let:

- $D$ = number of days in range
- $O$ = number of OPDs for the doctor
- $S$ = average number of slots per OPD per day
- $A$ = number of appointments in range

**Time Complexity**: $O(A + D \cdot O \cdot S)$

**Space Complexity**: $O(A + D \cdot O \cdot S)$ for booked set and output slots.

---

## Edge Cases

- **No OPDs for doctor** → returns empty list.
- **End date before start date** → returns 400 error.
- **OPD with invalid times** → prevented by validation at OPD creation/update.
- **All slots booked** → returns empty list for availability.
- **Day-of-week mask empty** → no slots generated.
- **OPD inactive** → excluded from slot generation by query filter.
- **Avg OPD time larger than session window** → zero slots for that OPD on that date.
- **Existing appointment at session boundary** → booked slot is removed if it matches a generated slot start time.
- **No matching AppointmentStatus/AppointmentType** → does not affect availability generation (only booking).

---

## Failure Handling

- **Invalid date range**: If `end_date < start_date`, the endpoint returns `400 Bad Request` with a descriptive error message.
- **Database query failures**: Unhandled database errors propagate as `500 Internal Server Error` from the API layer.
- **Invalid OPD time configuration**: Prevented during OPD create/update; availability assumes OPDs are valid.
- **Missing OPDs**: Returns an empty `appointments` list (not an error).
- **Concurrency race on booking**: Availability can show a slot that is booked immediately after; booking is protected by the unique constraint `(opd_id, appointment_datetime)` and returns `400` if already booked.

---

## Related Endpoints

- Availability generation: `GET /api/appointment/{doctor_id}/?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD`
- Booking slots: `POST /api/appointment/book/`

---

## Notes

- The algorithm is deterministic and relies on existing OPD schedules and bookings.
- Slot granularity is controlled by `avg_opd_time` in minutes.
- Appointment capacity per OPD is implicitly handled by slot generation and booking uniqueness.
