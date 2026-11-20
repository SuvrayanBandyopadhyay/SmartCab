
import json

from app.ai.llm import GeminiClient
from app.ai.prompts import SYSTEM_PROMPT


def test_gemini_workflow():
    llm = GeminiClient()

    test_messages = [
        "Hi!",
        "I want to change my cab timing.",
        "Change my cab timing to 8 PM."
    ]

    try:
        for message in test_messages:

            prompt = f"""
{SYSTEM_PROMPT}

Employee message: {message}

Return the appropriate JSON response.
"""

            response = llm.generate_json(prompt)

            print(f"\nEmployee: {message}")
            print(json.dumps(response, indent=2))

            assert response["type"] in (
                "conversation",
                "clarification",
                "action"
            )

            assert isinstance(response["message"], str)
            assert isinstance(response["commands"], list)

    finally:
        llm.close()


if __name__ == "__main__":
    test_gemini_workflow()
