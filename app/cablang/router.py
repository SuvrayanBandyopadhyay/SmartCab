
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.dependencies import (
    get_current_employee,
    get_db
)

from app.database.models import Employee

from app.cablang.analyser import analyse_command
from app.cablang.interpreter import execute_command


router = APIRouter(
    prefix="/cablang",
    tags=["CabLang"]
)


class CommandRequest(BaseModel):
    command: str


@router.post("/execute")
def execute_cablang(
    request: CommandRequest,
    employee: Employee = Depends(get_current_employee),
    db: Session = Depends(get_db)
):
    command_data = analyse_command(request.command)

    result = execute_command(
        command_data,
        employee,
        db
    )

    db.commit()

    return {
        "command": request.command,
        "result": result
    }
