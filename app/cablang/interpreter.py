from datetime import date, datetime

from sqlalchemy import func

from app.database.models import (
    Company,
    Employee,
    CompanyPolicy,
    Cab,
    Slot,
    RosterEntry,
    ShiftChangeRequest,
)


def get_available_slots(
    db,
    company_id,
    requested_date,
    requested_time=None,
    exclude_slot_id=None,
):
    policy = (
        db.query(CompanyPolicy)
        .filter(CompanyPolicy.company_id == company_id)
        .first()
    )

    max_capacity = (
        policy.policy_data.get("max_cab_capacity")
        if policy else None
    )

    slots = (
        db.query(Slot, Cab)
        .join(
            Cab,
            (Slot.cab_id == Cab.id)
            & (Slot.company_id == Cab.company_id),
        )
        .filter(
            Slot.company_id == company_id,
            Slot.service_date == requested_date,
            Slot.status == "OPEN",
            Cab.active.is_(True),
        )
        .all()
    )

    available = []

    for slot, cab in slots:

        if exclude_slot_id is not None and slot.id == exclude_slot_id:
            continue

        occupancy = (
            db.query(func.count(RosterEntry.id))
            .filter(
                RosterEntry.company_id == company_id,
                RosterEntry.slot_id == slot.id,
            )
            .scalar()
        ) or 0

        capacity = cab.capacity

        if max_capacity is not None:
            capacity = min(capacity, max_capacity)

        if occupancy < capacity:
            available.append({
                "slot": slot,
                "cab": cab,
                "occupancy": occupancy,
                "available_seats": capacity - occupancy,
            })

    if requested_time is not None:
        available.sort(
            key=lambda item: abs(
                (
                    datetime.combine(
                        requested_date,
                        item["slot"].scheduled_time,
                    )
                    - datetime.combine(
                        requested_date,
                        requested_time,
                    )
                ).total_seconds()
            )
        )

    return available


def execute_command(command_data, employee, db):

    company_id = employee.company_id

    if command_data["operation"] == "CHECK":

        item = command_data["item"]

        if item == "COMPANY":

            company = (
                db.query(Company)
                .filter(Company.id == company_id)
                .first()
            )

            return {
                "company": company.name if company else None,
            }

        if item == "ROSTER":

            entries = (
                db.query(RosterEntry, Slot, Cab)
                .join(
                    Slot,
                    (RosterEntry.slot_id == Slot.id)
                    & (RosterEntry.company_id == Slot.company_id),
                )
                .join(
                    Cab,
                    (Slot.cab_id == Cab.id)
                    & (Slot.company_id == Cab.company_id),
                )
                .filter(
                    RosterEntry.company_id == company_id,
                    RosterEntry.employee_id == employee.id,
                    Slot.service_date == date.today(),
                )
                .order_by(Slot.scheduled_time)
                .all()
            )

            return [
                {
                    "roster_entry_id": entry.id,
                    "slot_id": slot.id,
                    "cab": cab.cab_code,
                    "date": str(slot.service_date),
                    "time": str(slot.scheduled_time),
                }
                for entry, slot, cab in entries
            ]

        if item == "POLICY":

            policy = (
                db.query(CompanyPolicy)
                .filter(
                    CompanyPolicy.company_id == company_id
                )
                .first()
            )

            return policy.policy_data if policy else None

        if item == "CABS":

            cabs = (
                db.query(Cab)
                .filter(
                    Cab.company_id == company_id,
                    Cab.active.is_(True),
                )
                .order_by(Cab.cab_code)
                .all()
            )

            result = []

            for cab in cabs:

                slots = (
                    db.query(Slot)
                    .filter(
                        Slot.company_id == company_id,
                        Slot.cab_id == cab.id,
                        Slot.status == "OPEN",
                    )
                    .order_by(
                        Slot.service_date,
                        Slot.scheduled_time,
                    )
                    .all()
                )

                slot_details = []

                for slot in slots:

                    occupancy = (
                        db.query(func.count(RosterEntry.id))
                        .filter(
                            RosterEntry.company_id == company_id,
                            RosterEntry.slot_id == slot.id,
                        )
                        .scalar()
                    ) or 0

                    slot_details.append({
                        "slot_id": slot.id,
                        "date": str(slot.service_date),
                        "time": str(slot.scheduled_time),
                        "booked": occupancy,
                        "capacity": cab.capacity,
                        "available_seats": max(
                            0, cab.capacity - occupancy
                        ),
                    })

                result.append({
                    "cab": cab.cab_code,
                    "capacity": cab.capacity,
                    "slots": slot_details,
                })

            return result

        if item == "REQUESTS":

            requests = (
                db.query(ShiftChangeRequest)
                .filter(
                    ShiftChangeRequest.company_id == company_id,
                    ShiftChangeRequest.employee_id == employee.id,
                    ShiftChangeRequest.status.in_(
                        ["PENDING", "APPROVAL_REQUIRED"]
                    ),
                )
                .order_by(ShiftChangeRequest.created_at)
                .all()
            )

            return [
                {
                    "request_id": request.id,
                    "roster_entry_id": request.roster_entry_id,
                    "requested_slot_id": request.requested_slot_id,
                    "requested_date": str(request.requested_date),
                    "requested_time": str(request.requested_time),
                    "status": request.status,
                    "approval_given": request.approval_given,
                }
                for request in requests
            ]

        if item == "TIME":

            requested_time = command_data["start_time"]
            end_time = command_data["end_time"]

            slots = get_available_slots(
                db,
                company_id,
                date.today(),
            )

            return [
                {
                    "slot_id": item["slot"].id,
                    "cab": item["cab"].cab_code,
                    "date": str(item["slot"].service_date),
                    "time": str(item["slot"].scheduled_time),
                    "available_seats": item["available_seats"],
                }
                for item in slots
                if (
                    requested_time
                    <= item["slot"].scheduled_time
                    <= end_time
                )
            ]

    if command_data["operation"] == "REQUEST":

        if command_data["target"] == "SLOT":

            requested_slot_id = command_data["slot_id"]
            requested_date = date.today()

            roster = (
                db.query(RosterEntry, Slot)
                .join(
                    Slot,
                    (RosterEntry.slot_id == Slot.id)
                    & (RosterEntry.company_id == Slot.company_id),
                )
                .filter(
                    RosterEntry.company_id == company_id,
                    RosterEntry.employee_id == employee.id,
                    Slot.service_date == requested_date,
                )
                .order_by(Slot.scheduled_time)
                .first()
            )

            if roster is None:
                return {
                    "status": "FAILED",
                    "message": "No existing booking found to change",
                }

            roster_entry, current_slot = roster

            if requested_slot_id == current_slot.id:
                return {
                    "status": "FAILED",
                    "message": "You are already booked in this slot",
                }

            already_booked = (
                db.query(RosterEntry)
                .filter(
                    RosterEntry.company_id == company_id,
                    RosterEntry.employee_id == employee.id,
                    RosterEntry.slot_id == requested_slot_id,
                )
                .first()
            )

            if already_booked:
                return {
                    "status": "FAILED",
                    "message": "You are already booked in this slot",
                }

            available_slots = get_available_slots(
                db,
                company_id,
                requested_date,
                exclude_slot_id=current_slot.id,
            )

            selected = next(
                (
                    item for item in available_slots
                    if item["slot"].id == requested_slot_id
                ),
                None,
            )

            if selected is None:
                return {
                    "status": "FAILED",
                    "message": (
                        "Requested slot does not exist, is unavailable, "
                        "or has no available seats"
                    ),
                }

            selected_slot = selected["slot"]
            selected_cab = selected["cab"]

            request = ShiftChangeRequest(
                company_id=company_id,
                employee_id=employee.id,
                roster_entry_id=roster_entry.id,
                requested_slot_id=selected_slot.id,
                requested_date=selected_slot.service_date,
                requested_time=selected_slot.scheduled_time,
                status="PENDING",
                approval_given=False,
            )

            db.add(request)
            db.flush()

            return {
                "status": "PENDING",
                "request_id": request.id,
                "roster_entry_id": roster_entry.id,
                "requested_slot_id": selected_slot.id,
                "cab": selected_cab.cab_code,
                "requested_date": str(selected_slot.service_date),
                "requested_time": str(selected_slot.scheduled_time),
                "message": "Request created successfully. Awaiting policy evaluation.",
            }

        if command_data["target"] != "TIME":
            return {"error": "Unsupported request"}

        requested_time = datetime.strptime(
            command_data["time"],
            "%H:%M",
        ).time()

        requested_date = date.today()

        roster = (
            db.query(RosterEntry, Slot)
            .join(
                Slot,
                (RosterEntry.slot_id == Slot.id)
                & (RosterEntry.company_id == Slot.company_id),
            )
            .filter(
                RosterEntry.company_id == company_id,
                RosterEntry.employee_id == employee.id,
                Slot.service_date == requested_date,
            )
            .order_by(Slot.scheduled_time)
            .first()
        )

        if roster is None:
            return {
                "status": "FAILED",
                "message": "No existing booking found to change",
            }

        roster_entry, current_slot = roster

        available_slots = get_available_slots(
            db,
            company_id,
            requested_date,
            requested_time,
            exclude_slot_id=current_slot.id,
        )

        if command_data["nearest"]:

            if not available_slots:
                return {
                    "status": "FAILED",
                    "message": "No available slots found",
                }

            selected = available_slots[0]

        else:

            selected = next(
                (
                    item for item in available_slots
                    if item["slot"].scheduled_time == requested_time
                ),
                None,
            )

            if selected is None:
                return {
                    "status": "FAILED",
                    "message": (
                        "No available slot at the requested time. "
                        "Try NEAREST."
                    ),
                }

        selected_slot = selected["slot"]
        selected_cab = selected["cab"]

        request = ShiftChangeRequest(
            company_id=company_id,
            employee_id=employee.id,
            roster_entry_id=roster_entry.id,
            requested_slot_id=selected_slot.id,
            requested_date=selected_slot.service_date,
            requested_time=selected_slot.scheduled_time,
            status="PENDING",
            approval_given=False,
        )

        db.add(request)
        db.flush()

        return {
            "status": "PENDING",
            "request_id": request.id,
            "roster_entry_id": roster_entry.id,
            "requested_slot_id": selected_slot.id,
            "cab": selected_cab.cab_code,
            "requested_date": str(selected_slot.service_date),
            "requested_time": str(selected_slot.scheduled_time),
            "message": "Request created successfully. Awaiting policy evaluation.",
        }

    return {"error": "Invalid CabLang operation"}
