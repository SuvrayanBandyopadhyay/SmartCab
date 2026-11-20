
from datetime import date, time

from app.database.connection import Base, engine, SessionLocal
from app.database.models import (
    Company,
    Employee,
    CompanyPolicy,
    Cab,
    Slot,
    RosterEntry,
)
from app.core.security import hash_password


def seed():

    #Delete all existing tables and recreate them

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    with SessionLocal() as db:

        companies = [
            {
                "name": "X Technologies",
                "policy": {
                    "version": 1,
                    "max_cab_capacity": 4,
                    "cutoff_minutes": 120,
                    "capacity": {
                        "allow_overcapacity": False
                    },
                    "approval": {
                        "cutoff_violation": "MANAGER_REQUIRED"
                    },
                },
                "cab_code": "X-101",
                "capacity": 4,
            },
            {
                "name": "Y Solutions",
                "policy": {
                    "version": 1,
                    "max_cab_capacity": 6,
                    "cutoff_minutes": 90,
                    "capacity": {
                        "allow_overcapacity": False
                    },
                    "approval": {
                        "cutoff_violation": "MANAGER_REQUIRED"
                    },
                },
                "cab_code": "Y-101",
                "capacity": 6,
            },
        ]

        for company_index, company_data in enumerate(companies):

            company = Company(name=company_data["name"])
            db.add(company)
            db.flush()

            #Create employees

            if company_index == 0:

                employee_emails = [
                    "employee@X.test",
                    "employee2@X.test",
                    "employee3@X.test",
                    "employee4@X.test",
                    "full1@X.test",
                    "full2@X.test",
                    "full3@X.test",
                    "full4@X.test",
                ]

            else:
                employee_emails = [
                    "employee@Y.test",
                ]

            employees = []

            for email in employee_emails:

                employee = Employee(
                    company_id=company.id,
                    name=email.split("@")[0],
                    email=email,
                    password_hash=hash_password("employee123"),
                    role="EMPLOYEE",
                )

                db.add(employee)
                employees.append(employee)

            manager_email = (
                "manager@X.test"
                if company_index == 0
                else "manager@Y.test"
            )

            manager = Employee(
                company_id=company.id,
                name="Test Manager",
                email=manager_email,
                password_hash=hash_password("manager123"),
                role="MANAGER",
            )

            db.add(manager)
            db.flush()

            #Create company policy

            policy = CompanyPolicy(
                company_id=company.id,
                policy_data=company_data["policy"],
                version=1,
            )

            cab = Cab(
                company_id=company.id,
                cab_code=company_data["cab_code"],
                capacity=company_data["capacity"],
                active=True,
            )

            db.add_all([policy, cab])
            db.flush()

            #Create slots

            slot_times = [
                time(18, 0),
                time(19, 0),
                time(20, 0),
                time(21, 0),
            ]

            DEMO_DATE = date(2026, 11, 20)

            slots = []

            for slot_time in slot_times:

                slot = Slot(
                    company_id=company.id,
                    cab_id=cab.id,
                    service_date=DEMO_DATE,
                    scheduled_time=slot_time,
                    status="OPEN",
                )

                db.add(slot)
                slots.append(slot)

            db.flush()

            #Assign employees to slots

            if company_index == 0:

                #First four employees occupy Slot 1

                for employee in employees[:4]:
                    db.add(
                        RosterEntry(
                            company_id=company.id,
                            employee_id=employee.id,
                            slot_id=slots[0].id,
                        )
                    )

                #Next four employees completely fill Slot 3

                for employee in employees[4:8]:
                    db.add(
                        RosterEntry(
                            company_id=company.id,
                            employee_id=employee.id,
                            slot_id=slots[2].id,
                        )
                    )

            else:

                #Company Y retains its original assignment

                db.add(
                    RosterEntry(
                        company_id=company.id,
                        employee_id=employees[0].id,
                        slot_id=slots[0].id,
                    )
                )

        db.commit()

        print("Database reset and seeded successfully.")
        print("Companies: 2")
        print("Employees: 9")
        print("Managers: 2")
        print("Cabs: 2")
        print("Slots: 8")
        print("Roster entries: 9")
        print("Company X Slot 1: FULL")
        print("Company X Slot 3: FULL")


if __name__ == "__main__":
    seed()
