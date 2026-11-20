import re
from datetime import datetime, timedelta

class CabLangError(Exception):
    #Raised when a CabLang error is malformed or invalid
    pass

VALID_CHECKS = {
    "COMPANY",
    "ROSTER",
    "POLICY",
    "CABS",
    "REQUESTS"
}

TIME_PATTERN = r"(?:[01]?\d|2[0-3]):[0-5]\d"

MAX_MARGIN_HOURS = 12.0


def get_time_window(
    requested_time: str,
    margin_hours: float,
):
    #This function is used to get  a time window given a requested time and margin hours.

    if (
        not isinstance(margin_hours, (int, float))
        or isinstance(margin_hours, bool)
    ):
        raise CabLangError("Margin must be numeric")

    if margin_hours < 0 or margin_hours > MAX_MARGIN_HOURS:
        raise CabLangError(
            f"Margin must be between 0 and {MAX_MARGIN_HOURS} hours"
        )

    try:
        start = datetime.strptime(requested_time, "%H:%M")
    except (ValueError, TypeError):
        raise CabLangError("Invalid time")

    end = start + timedelta(hours=margin_hours)

    # The current roster model stores time separately from date.
    # Reject intervals that cross midnight.
    if end.date() != start.date():
        raise CabLangError(
            "Time window cannot extend beyond midnight"
        )

    return start.time(), end.time()

def analyse_command(command:str):
    #Analyse a CabLang Command and return a structured dictionary

    if not isinstance(command, str) or not command.strip():
        raise CabLangError("Command cannot be empty")

    #Normalize whitespaces
    command = " ".join(command.strip().split())

    #Try out CHECK COMMANDS
    match = re.fullmatch(
        r"CHECK\s+([A-Za-z_]+)",
        command,
        flags=re.IGNORECASE,
    )

    #If there is a match for CHECK COMPANY / ROSTER / POLICY / CABS / REQUESTS
    if match:
        item = match.group(1).upper()

        if item not in VALID_CHECKS:
            raise CabLangError(
                f"Unsupported CHECK operation: {item}"
            )

        return {
            "operation": "CHECK",
            "item": item,
        }
    
    # CHECK FOR CHECK TIME HH:MM MARGIN

    match = re.fullmatch(
        rf"CHECK\s+TIME\s+({TIME_PATTERN})\s+(\d+(?:\.\d+)?)",
        command,
        flags=re.IGNORECASE,
    )

    if match:
        requested_time = match.group(1)
        margin = float(match.group(2))

        start, end = get_time_window(
            requested_time,
            margin,
        )

        return {
            "operation": "CHECK",
            "item": "TIME",
            "time": requested_time,
            "margin_hours": margin,
            "start_time": start,
            "end_time": end,
        }

    #REQUEST functions

    #Request a pickup
    match = re.fullmatch(
    rf"REQUEST\s+PICKUP\s+({TIME_PATTERN})",
    command,
    flags=re.IGNORECASE)

    if match:
        return {
            "operation": "REQUEST",
            "target": "NEW_PICKUP",
            "time": match.group(1),
        }
    #Request Slot
    match = re.fullmatch(
        r"REQUEST\s+SLOT\s+(\d+)",
        command,
        flags=re.IGNORECASE,
    )

    if match:
        return {
            "operation": "REQUEST",
            "target": "SLOT",
            "slot_id": int(match.group(1)),
        }


    #REQUEST TIME [NEAREST]
    match = re.fullmatch(
        rf"REQUEST\s+TIME\s+({TIME_PATTERN})(?:\s+(NEAREST))?",
        command,
        flags=re.IGNORECASE,
    )

    if match:
        return {
            "operation": "REQUEST",
            "target": "TIME",
            "time": match.group(1),
            "nearest": bool(match.group(2)),
        }

    #REQUEST CAB
    match = re.fullmatch(
        r"REQUEST\s+CAB\s+([A-Za-z0-9_-]+)",
        command,
        flags=re.IGNORECASE,
    )

    if match:
        return {
            "operation": "REQUEST",
            "target": "CAB",
            "cab_code": match.group(1).upper(),
        }

    raise CabLangError(
        "Invalid or unsupported CabLang command"
    )

