
from langchain_core.chat_history import InMemoryChatMessageHistory

chat_histories = {}


def get_chat_history(employee_id: int):
    if employee_id not in chat_histories:
        chat_histories[employee_id] = InMemoryChatMessageHistory()

    return chat_histories[employee_id]


def get_recent_messages(employee_id: int):
    return get_chat_history(employee_id).messages[-10:]


def clear_chat_history(employee_id: int):
    chat_histories.pop(employee_id, None)
