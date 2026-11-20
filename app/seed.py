
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


def seed():
    Base.metadata.create_all(bind=engine)

    with SessionLocal() as db:
        if db.query(Company).first():
            print("Database already seeded. Skipping.")
            return

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
                "employee_email": "employee@X.test",
                "manager_email": "manager@X.test",
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
                "employee_email": "employee@Y.test",
                "manager_email": "manager@Y.test",
            },
        ]

        for company_data in companies:
            company = Company(name=company_data["name"])
            db.add(company)
            db.flush()

            employee = Employee(
                company_id=company.id,
                name="Test Employee",
                email=company_data["employee_email"],
                password_hash="NOT_SET",
                role="EMPLOYEE",
            )

            manager = Employee(
                company_id=company.id,
                name="Test Manager",
                email=company_data["manager_email"],
                password_hash="NOT_SET",
                role="MANAGER",
            )

            db.add_all([employee, manager])
            db.flush()

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

            slot_times = [
                time(18, 0),
                time(19, 0),
                time(20, 0),
                time(21, 0),
            ]

            slots = []
            DEMO_DATE = date(2026, 11, 20) #We fix the date so that the tests dont fail
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

            db.add(
                RosterEntry(
                    company_id=company.id,
                    employee_id=employee.id,
                    slot_id=slots[0].id,
                )
            )

        db.commit()

        print("Database seeded successfully.")
        print("Companies: 2")
        print("Employees: 4")
        print("Cabs: 2")
        print("Slots: 8")
        print("Roster entries: 2")


if __name__ == "__main__":
    seed()
