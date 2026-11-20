
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.connection import SessionLocal
from app.database.models import Employee
from app.core.security import (
    verify_password,
    create_access_token
)


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


class LoginRequest(BaseModel):
    email: str
    password: str
    company_id: int


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/login", response_model=LoginResponse)
def login(
    request: LoginRequest,
    db: Session = Depends(get_db)
):
    employee = db.query(Employee).filter(
        Employee.email == request.email,
        Employee.company_id == request.company_id
    ).first()

    if not employee or not verify_password(
        request.password,
        employee.password_hash
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid email, password, or company."
        )

    token = create_access_token(
        employee_id=employee.id,
        company_id=employee.company_id,
        role=employee.role
    )

    return LoginResponse(
        access_token=token
    )
