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
                )
                .order_by(ShiftChangeRequest.created_at.desc())
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

            #Validate requested slot without checking its occupancy

            selected_slot = (
                db.query(Slot)
                .filter(
                    Slot.id == requested_slot_id,
                    Slot.company_id == company_id,
                    Slot.service_date == requested_date,
                    Slot.status == "OPEN",
                )
                .first()
            )

            if selected_slot is None:
                return {
                    "status": "FAILED",
                    "message": "Requested slot does not exist or is unavailable",
                }

            selected_cab = (
                db.query(Cab)
                .filter(
                    Cab.id == selected_slot.cab_id,
                    Cab.company_id == company_id,
                    Cab.active == True,
                )
                .first()
            )

            if selected_cab is None:
                return {
                    "status": "FAILED",
                    "message": "Requested cab is unavailable",
                }

            #Create request even if the slot is full

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

        
        if command_data["nearest"]:

            #Find all valid slots, including full slots

            candidate_slots = (
                db.query(Slot, Cab)
                .join(
                    Cab,
                    (Slot.cab_id == Cab.id)
                    & (Slot.company_id == Cab.company_id),
                )
                .filter(
                    Slot.company_id == company_id,
                    Slot.service_date == requested_date,
                    Slot.id != current_slot.id,
                    Slot.status == "OPEN",
                    Cab.active == True,
                )
                .all()
            )

            if not candidate_slots:
                return {
                    "status": "FAILED",
                    "message": "No valid slots found",
                }

            #Select the chronologically nearest slot

            selected_slot, selected_cab = min(
                candidate_slots,
                key=lambda item: (
                    abs(
                        (
                            datetime.combine(
                                requested_date,
                                item[0].scheduled_time,
                            )
                            -
                            datetime.combine(
                                requested_date,
                                requested_time,
                            )
                        ).total_seconds()
                    ),
                    item[0].scheduled_time,
                    item[0].id,
                ),
            )


        else:

            #Exact time requests can target full slots

            selected_slot = (
                db.query(Slot)
                .filter(
                    Slot.company_id == company_id,
                    Slot.service_date == requested_date,
                    Slot.scheduled_time == requested_time,
                    Slot.status == "OPEN",
                )
                .first()
            )

            if selected_slot is None:
                return {
                    "status": "FAILED",
                    "message": "No slot exists at the requested time.",
                }

            selected_cab = (
                db.query(Cab)
                .filter(
                    Cab.id == selected_slot.cab_id,
                    Cab.company_id == company_id,
                    Cab.active == True,
                )
                .first()
            )

            if selected_cab is None:
                return {
                    "status": "FAILED",
                    "message": "Requested cab is unavailable",
                }

        #Create the shift change request

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
