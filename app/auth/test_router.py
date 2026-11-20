
from fastapi import APIRouter, Depends

from app.auth.dependencies import get_current_employee
from app.database.models import Employee


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)


@router.get("/me")
def get_me(
    employee: Employee = Depends(get_current_employee)
):
    return {
        "employee_id": employee.id,
        "name": employee.name,
        "email": employee.email,
        "company_id": employee.company_id,
        "role": employee.role
    }
