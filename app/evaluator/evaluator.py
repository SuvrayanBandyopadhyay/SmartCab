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

                if request.status not in (
                    "PENDING",
                    "APPROVAL_REQUIRED",
                ):
                    return request.status

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

                if (
                    cab is None
                    or not cab.active
                    or slot.status != "OPEN"
                ):
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
                    request.status = "FAILED"
                    request.decided_at = DECIDED_AT
                    return "FAILED"

                if roster_entry.slot_id == slot.id:
                    request.status = "FAILED"
                    request.decided_at = DECIDED_AT
                    return "FAILED"

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

                if occupancy >= capacity:
                    request.status = "FAILED"
                    request.decided_at = DECIDED_AT
                    return "FAILED"

                roster_entry.slot_id = slot.id

                request.status = "APPLIED"
                request.decided_at = DECIDED_AT

                return "APPLIED"

        except Exception:
            db.rollback()

            request = (
                db.query(ShiftChangeRequest)
                .filter(
                    ShiftChangeRequest.id == request_id
                )
                .first()
            )

            if request and request.status in (
                "PENDING",
                "APPROVAL_REQUIRED",
            ):
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
                    ShiftChangeRequest.status.in_(
                        ["PENDING", "APPROVAL_REQUIRED"]
                    )
                )
                .order_by(ShiftChangeRequest.created_at)
                .all()
            )
        ]

    results = {
        "APPLIED": 0,
        "APPROVAL_REQUIRED": 0,
        "REJECTED": 0,
        "FAILED": 0,
    }

    for request_id in request_ids:

        status = evaluate_request(request_id)

        if status in results:
            results[status] += 1

    return results
