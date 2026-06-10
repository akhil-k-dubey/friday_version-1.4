"""
skills/timer_remind.py — Countdown timer and reminder skills.
"""
from __future__ import annotations

import datetime
import json
import os
import re
import threading
import time

from ._constants import _active_timers
from ._utils import _announce, _play_beep


def skill_timer(args: str) -> str:
    """Set a countdown timer. Args: seconds or 'Xm' for minutes."""
    raw = args.strip().lower()
    if not raw:
        return "Specify a duration, like 30 for 30 seconds or 5m for 5 minutes."

    try:
        if raw.endswith("m"):
            seconds = int(raw[:-1]) * 60
        elif raw.endswith("min"):
            seconds = int(raw[:-3]) * 60
        elif raw.endswith("h"):
            seconds = int(raw[:-1]) * 3600
        elif raw.endswith("s"):
            seconds = int(raw[:-1])
        else:
            seconds = int(raw)
    except ValueError:
        return f"Could not parse duration: {raw}"

    if seconds <= 0:
        return "Duration must be positive."
    if seconds > 86400:
        return "Maximum timer is 24 hours."

    def _alarm():
        time.sleep(seconds)
        label_done = f"{seconds}s" if seconds < 60 else f"{seconds//60}m{seconds%60:02d}s"
        _announce(f"Timer done! {label_done} elapsed.")
        _play_beep(880, 300)
        _play_beep(1047, 300)
        _play_beep(1319, 400)
        # Cleanup: remove this timer from the active list
        _active_timers[:] = [t for t in _active_timers if t.get("thread") is not threading.current_thread()]

    t = threading.Thread(target=_alarm, daemon=True, name=f"timer-{seconds}s")
    t.start()
    _active_timers.append({"seconds": seconds, "started": time.time(), "thread": t})

    if seconds >= 60:
        mins = seconds // 60
        secs = seconds % 60
        label = f"{mins} minute{'s' if mins != 1 else ''}"
        if secs:
            label += f" {secs} second{'s' if secs != 1 else ''}"
    else:
        label = f"{seconds} second{'s' if seconds != 1 else ''}"

    return f"Timer set for {label}."


def skill_remind(args: str) -> str:
    """Set a quick reminder (same as timer but with a message)."""
    # Parse "in Xm message" or "X seconds message"
    match = re.match(r'(?:in\s+)?(\d+)\s*(s|sec|seconds?|m|min|minutes?|h|hours?)\s*(.*)', args.strip(), re.IGNORECASE)
    if not match:
        return "Format: remind in 5m check the oven"

    amount = int(match.group(1))
    unit = match.group(2).lower()
    message = match.group(3).strip() or "Time's up!"

    if unit.startswith("m"):
        seconds = amount * 60
    elif unit.startswith("h"):
        seconds = amount * 3600
    else:
        seconds = amount

    target_time = time.time() + seconds
    target_dt = datetime.datetime.fromtimestamp(target_time).isoformat()

    # Save persistent time-tagged entry to memory.json
    path = os.path.join(os.path.expanduser("~"), ".friday", "memory.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        data = {}
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

        reminders = data.setdefault("reminders", [])
        reminders.append({
            "target_time": target_time,
            "target_dt": target_dt,
            "message": message,
            "fired": False
        })

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

    def _remind():
        time.sleep(seconds)
        _announce(f"Reminder: {message}")
        _play_beep(600, 300)
        _play_beep(880, 300)
        _play_beep(600, 300)

        # Mark fired=True in memory.json
        try:
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    r_data = json.load(f)
                r_reminders = r_data.get("reminders", [])
                for r in r_reminders:
                    if abs(r.get("target_time", 0.0) - target_time) < 0.1 and r.get("message") == message:
                        r["fired"] = True
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(r_data, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

        # Cleanup: remove from active list
        _active_timers[:] = [t for t in _active_timers if t.get("thread") is not threading.current_thread()]

    remind_thread = threading.Thread(target=_remind, daemon=True, name=f"remind-{seconds}s")
    remind_thread.start()
    _active_timers.append({"seconds": seconds, "started": time.time(), "thread": remind_thread, "msg": message})

    if seconds >= 60:
        label = f"{seconds // 60} minute{'s' if seconds // 60 != 1 else ''}"
    else:
        label = f"{seconds} second{'s' if seconds != 1 else ''}"

    return f"Reminder set: '{message}' in {label}."
