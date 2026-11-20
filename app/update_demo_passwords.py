from sqlalchemy import select

from app.database.connection import SessionLocal
from app.database.models import Employee
from app.core.security import hash_password


DEMO_PASSWORDS = {
    "EMPLOYEE": "employee123",
    "MANAGER": "manager123",
}


def update_demo_passwords():
    with SessionLocal() as db:
        employees = db.scalars(
            select(Employee)
        ).all()

        updated = 0
        skipped = 0

        for employee in employees:
            if employee.password_hash != "NOT_SET":
                skipped += 1
                continue

            password = DEMO_PASSWORDS.get(employee.role)

            if password is None:
                print(
                    f"Skipping employee {employee.id}: "
                    f"unknown role {employee.role}"
                )
                skipped += 1
                continue

            employee.password_hash = hash_password(password)
            updated += 1

        db.commit()

        print(f"Passwords updated: {updated}")
        print(f"Accounts skipped: {skipped}")


if __name__ == "__main__":
    update_demo_passwords()