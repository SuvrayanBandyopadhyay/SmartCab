
from datetime import datetime, timezone

from sqlalchemy import func

from app.database.connection import SessionLocal
from app.database.models import (
    CompanyPolicy,
    Cab,
    Slot,
    RosterEntry,
    ShiftChangeRequest,
)

CURRENT_TIME = datetime(2026, 11, 20, 17, 30)
DECIDED_AT = CURRENT_TIME.replace(tzinfo=timezone.utc)

ACTIVE_STATUSES = [
    "PENDING",
    "APPROVAL_REQUIRED",
    "WAITLISTED",
]


def evaluate_request(request_id):

    with SessionLocal() as db:

        try:
            with db.begin():

                request = (
                    db.query(ShiftChangeRequest)
                    .filter(
                        ShiftChangeRequest.id == request_id
                    )
                    .with_for_update()
                    .first()
                )

                if request is None:
                    return "NOT_FOUND"

                if request.status not in ACTIVE_STATUSES:
                    return request.status

                #Identify the latest active request

                active_requests = (
                    db.query(ShiftChangeRequest)
                    .filter(
                        ShiftChangeRequest.company_id == request.company_id,
                        ShiftChangeRequest.employee_id == request.employee_id,
                        ShiftChangeRequest.roster_entry_id == request.roster_entry_id,
                        ShiftChangeRequest.status.in_(ACTIVE_STATUSES)
                    )
                    .order_by(
                        ShiftChangeRequest.created_at.desc(),
                        ShiftChangeRequest.id.desc()
                    )
                    .with_for_update()
                    .all()
                )

                if not active_requests:
                    return request.status

                latest_request = active_requests[0]

                if latest_request.id != request.id:
                    request.status = "SUPERSEDED"
                    request.decided_at = DECIDED_AT
                    return "SUPERSEDED"

                #Supersede older active requests

                for previous_request in active_requests[1:]:
                    previous_request.status = "SUPERSEDED"
                    previous_request.decided_at = DECIDED_AT

                slot = (
                    db.query(Slot)
                    .filter(
                        Slot.id == request.requested_slot_id,
                        Slot.company_id == request.company_id,
                    )
                    .with_for_update()
                    .first()
                )

                if slot is None:
                    print("FAILED: Slot not found")
                    request.status = "FAILED"
                    request.decided_at = DECIDED_AT
                    return "FAILED"

                scheduled_datetime = datetime.combine(
                    slot.service_date,
                    slot.scheduled_time,
                )

                if CURRENT_TIME >= scheduled_datetime:
                    request.status = "REJECTED"
                    request.decided_at = DECIDED_AT
                    return "REJECTED"

                policy = (
                    db.query(CompanyPolicy)
                    .filter(
                        CompanyPolicy.company_id == request.company_id
                    )
                    .first()
                )

                if policy is None:
                    print("FAILED: Company policy not found")
                    request.status = "FAILED"
                    request.decided_at = DECIDED_AT
                    return "FAILED"

                cutoff_minutes = policy.policy_data.get(
                    "cutoff_minutes", 0
                )

                time_remaining = (
                    scheduled_datetime - CURRENT_TIME
                ).total_seconds() / 60

                cutoff_violated = (
                    time_remaining < cutoff_minutes
                )

                if (
                    cutoff_violated
                    and not request.approval_given
                ):
                    request.status = "APPROVAL_REQUIRED"
                    return "APPROVAL_REQUIRED"

                cab = (
                    db.query(Cab)
                    .filter(
                        Cab.id == slot.cab_id,
                        Cab.company_id == request.company_id,
                    )
                    .with_for_update()
                    .first()
                )

                if cab is None or not cab.active:
                    print("FAILED: Cab missing or inactive")
                    request.status = "FAILED"
                    request.decided_at = DECIDED_AT
                    return "FAILED"

                if slot.status != "OPEN":
                    print("FAILED: Slot is not OPEN:", slot.status)
                    request.status = "FAILED"
                    request.decided_at = DECIDED_AT
                    return "FAILED"

                roster_entry = (
                    db.query(RosterEntry)
                    .filter(
                        RosterEntry.id == request.roster_entry_id,
                        RosterEntry.company_id == request.company_id,
                        RosterEntry.employee_id == request.employee_id,
                    )
                    .with_for_update()
                    .first()
                )

                if roster_entry is None:
                    print("FAILED: Roster entry not found")
                    request.status = "FAILED"
                    request.decided_at = DECIDED_AT
                    return "FAILED"

                if roster_entry.slot_id == slot.id:
                    print("FAILED: Employee already assigned to requested slot")
                    request.status = "FAILED"
                    request.decided_at = DECIDED_AT
                    return "FAILED"

                #Check current slot occupancy

                occupancy = (
                    db.query(func.count(RosterEntry.id))
                    .filter(
                        RosterEntry.company_id == request.company_id,
                        RosterEntry.slot_id == slot.id,
                    )
                    .scalar()
                ) or 0

                max_capacity = policy.policy_data.get(
                    "max_cab_capacity"
                )

                capacity = cab.capacity

                if max_capacity is not None:
                    capacity = min(capacity, max_capacity)

                #Add request to waitlist if cab is full

                if occupancy >= capacity:
                    request.status = "WAITLISTED"
                    return "WAITLISTED"

                #Apply the shift change

                roster_entry.slot_id = slot.id

                request.status = "APPLIED"
                request.decided_at = DECIDED_AT

                return "APPLIED"

        except Exception as e:
            import traceback
            traceback.print_exc()
            print("Evaluator exception:", repr(e))
            db.rollback()

            request = (
                db.query(ShiftChangeRequest)
                .filter(
                    ShiftChangeRequest.id == request_id
                )
                .first()
            )

            if request and request.status in ACTIVE_STATUSES:
                request.status = "FAILED"
                request.decided_at = DECIDED_AT
                db.commit()

            return "FAILED"


def evaluate_pending_requests():

    with SessionLocal() as db:

        request_ids = [
            request_id
            for (request_id,) in (
                db.query(ShiftChangeRequest.id)
                .filter(
                    ShiftChangeRequest.status.in_(ACTIVE_STATUSES)
                )
                .order_by(
                    ShiftChangeRequest.created_at.asc(),
                    ShiftChangeRequest.id.asc()
                )
                .all()
            )
        ]

    results = {
        "APPLIED": 0,
        "APPROVAL_REQUIRED": 0,
        "WAITLISTED": 0,
        "REJECTED": 0,
        "FAILED": 0,
        "SUPERSEDED": 0,
    }

    for request_id in request_ids:

        status = evaluate_request(request_id)

        if status in results:
            results[status] += 1

    return results


#Daemon

if __name__ == "__main__":

    import time

    print("SmartCab Evaluator started.")

    while True:
        try:
            results = evaluate_pending_requests()

            if any(results.values()):
                print("Evaluation results:", results)

        except Exception as e:
            print("Evaluator error:", str(e))

        time.sleep(1)
