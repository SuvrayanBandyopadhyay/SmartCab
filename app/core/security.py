from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from pwdlib import PasswordHash

from app.config import settings

#The Password Hashing configuration
password_hasher = PasswordHash.recommended()

#Function to hash passwords
def hash_password(password:str):
    return password_hasher.hash(password)

#Verify Passwords
def verify_password(password:str,hashed_password:str):
    return password_hasher.verify(password,hashed_password)

#JWT Generation Function
def create_access_token(employee_id:int,company_id: int,role:str):
    time_now = datetime.now(timezone.utc)
    payload = {
        "sub": str(employee_id),
        "company_id": company_id,
        "role": role,
        "iat": time_now,
        "exp": time_now + timedelta
            (
            minutes=settings.JWT_EXPIRATION_MINUTES
            )
    }
    return jwt.encode(payload,settings.JWT_SECRET,algorithm=settings.JWT_ALGORITHM)

def decode_access_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
        )

        employee_id = payload.get("sub")
        company_id = payload.get("company_id")
        role = payload.get("role")

        if (
            not isinstance(employee_id, str)
            or not employee_id.isdigit()
            or int(employee_id) <= 0
            or not isinstance(company_id, int)
            or isinstance(company_id, bool)
            or company_id <= 0
            or role not in ("EMPLOYEE", "MANAGER")
        ):
            return None

        return payload

    except JWTError:
        return None