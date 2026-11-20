
from pydantic import BaseModel


class LoginRequest(BaseModel):
    company_name: str
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class EmployeeIdentity(BaseModel):
    id: int
    company_id: int
    name: str
    email: str
    role: str
