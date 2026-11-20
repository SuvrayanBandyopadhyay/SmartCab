
import json

from pathlib import Path

from app.database.connection import SessionLocal
from app.database.models import Employee, ShiftChangeRequest
from app.cablang.analyser import analyse_command
from app.cablang.interpreter import execute_command


TEST_FILE = Path(__file__).with_name("interpreter_cases.jsonl")


def check_result(actual, expected):
    if isinstance(actual, list):
        if "count" in expected and len(actual) != expected["count"]:
            return False

        if "first_cab" in expected:
            if not actual or actual[0].get("cab") != expected["first_cab"]:
                return False

        if "first_slot_count" in expected:
            if not actual or len(actual[0].get("slots", [])) != expected["first_slot_count"]:
                return False

        if "first_time" in expected:
            if not actual or actual[0].get("time") != expected["first_time"]:
                return False

        return True

    if isinstance(actual, dict):
        return all(actual.get(key) == value for key, value in expected.items())

    return actual == expected


def run_tests():
    with SessionLocal() as db:
        employee = (
            db.query(Employee)
            .filter(Employee.email == "employee@X.test")
            .first()
        )

        if employee is None:
            print("Test employee not found. Run the seed script first.")
            return

        db.query(ShiftChangeRequest).filter(
            ShiftChangeRequest.company_id == employee.company_id,
            ShiftChangeRequest.employee_id == employee.id,
        ).delete(synchronize_session=False)

        db.commit()

        with open(TEST_FILE, "r", encoding="utf-8") as file:
            cases = [
                json.loads(line)
                for line in file
                if line.strip()
            ]

        passed = 0

        for case in cases:
            try:
                command_data = analyse_command(case["input"])

                actual = execute_command(
                    command_data,
                    employee,
                    db,
                )

                case["actual"] = actual
                case["pass"] = check_result(
                    actual,
                    case["expected"],
                )

                db.commit()

            except Exception as exc:
                db.rollback()
                case["actual"] = str(exc)
                case["pass"] = False

            if case["pass"]:
                passed += 1

            print(
                f'{case["id"]}: '
                f'{"PASS" if case["pass"] else "FAIL"}'
            )

        with open(TEST_FILE, "w", encoding="utf-8") as file:
            for case in cases:
                file.write(json.dumps(case, default=str) + "\n")

        print()
        print(f"Total tests: {len(cases)}")
        print(f"Passed: {passed}")
        print(f"Failed: {len(cases) - passed}")


if __name__ == "__main__":
    run_tests()
