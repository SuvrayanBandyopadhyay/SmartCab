
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from app.config import settings
from app.ai.prompts import SYSTEM_PROMPT
from app.ai.memory import get_chat_history, get_recent_messages

from app.auth.dependencies import (
    get_current_employee,
    get_db
)

from app.database.models import Employee

from app.cablang.analyser import analyse_command
from app.cablang.interpreter import execute_command


router = APIRouter(
    prefix="/chat",
    tags=["AI Chatbot"]
)


class ChatRequest(BaseModel):
    message: str


class ChatPlan(BaseModel):
    type: Literal["conversation", "clarification", "action"]
    message: str
    commands: list[str]


@router.post("/message")
def chat(
    request: ChatRequest,
    employee: Employee = Depends(get_current_employee),
    db: Session = Depends(get_db)
):
    try:
        # 1. Initialize Gemini
        llm = ChatGoogleGenerativeAI(
            model=settings.GEMINI_MODEL,
            google_api_key=settings.GEMINI_API_KEY,
            temperature=0
        )

        # 2. Retrieve conversation memory
        history = get_chat_history(employee.id)
        recent_messages = get_recent_messages(employee.id)

        # 3. Create planning chain with conversation history
        planning_prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT.replace("{", "{{").replace("}", "}}")),
            ("placeholder", "{history}"),
            (
                "human",
                "Employee message: {employee_message}\n"
                "Return the appropriate structured response."
            )
        ])

        planning_chain = (
            planning_prompt
            | llm.with_structured_output(ChatPlan)
        )

        # 4. Generate a plan
        plan = planning_chain.invoke({
            "history": recent_messages,
            "employee_message": request.message
        })

        response_type = plan.type
        commands = plan.commands

        # 5. Handle conversation and clarification
        if response_type != "action":

            if commands:
                raise HTTPException(
                    status_code=502,
                    detail="Unexpected commands in non-action response."
                )

            history.add_user_message(request.message)
            history.add_ai_message(plan.message)

            return {
                "message": plan.message,
                "results": []
            }

        # 6. Execute CabLang commands
        results = []

        for command in commands:
            command_data = analyse_command(command)

            result = execute_command(
                command_data,
                employee,
                db
            )

            results.append({
                "command": command,
                "result": result
            })

        # 7. Generate natural-language explanation
        explanation_prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                """
                You are SmartCab, a conversational employee transport assistant.

                Explain execution results clearly and naturally.

                Rules:
                - Only report information present in the results.
                - Never claim an operation succeeded if it failed.
                - Explain pending requests as pending, not approved.
                - Do not invent employee, cab, or timing details.
                """
            ),
            (
                "human",
                """
                Employee message:
                {employee_message}

                CabLang execution results:
                {execution_results}
                """
            )
        ])

        explanation_chain = (
            explanation_prompt
            | llm
            | StrOutputParser()
        )

        final_message = explanation_chain.invoke({
            "employee_message": request.message,
            "execution_results": str(results)
        })

        # 8. Commit database changes
        db.commit()

        # 9. Update conversation memory
        history.add_user_message(request.message)
        history.add_ai_message(final_message)

        return {
            "message": final_message,
            "results": results
        }

    except HTTPException:
        db.rollback()
        raise

    except Exception as e:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=f"Chatbot execution failed: {str(e)}"
        )
