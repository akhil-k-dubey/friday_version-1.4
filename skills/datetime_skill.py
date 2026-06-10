"""
skills/datetime_skill.py — Date and time information.
"""
from __future__ import annotations

import datetime


def skill_datetime(args: str) -> str:
    """Get current date, time, or day information."""
    now = datetime.datetime.now()
    query = args.strip().lower()

    if "date" in query:
        return f"Today is {now.strftime('%A, %d %B %Y')}."
    elif "day" in query:
        return f"Today is {now.strftime('%A')}."
    else:
        return f"It is {now.strftime('%I:%M %p')} on {now.strftime('%A, %d %B %Y')}."
