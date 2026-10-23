"""The business calendar: "today" in the configured time zone, not in the server's.

A server running in UTC would otherwise move to the next day at 6 pm in Mexico City, which changes
date validation, each credit's standing and the upcoming due dates.
"""

from datetime import date, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from flask import current_app


def check_time_zone(name: str) -> None:
    try:
        ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        raise ValueError(f"Unknown APP_TIMEZONE '{name}'. Use an IANA name such as America/Mexico_City.") from None


def now() -> datetime:
    return datetime.now(ZoneInfo(current_app.config["TIMEZONE"]))


def today() -> date:
    return now().date()
