"""
skills/weather.py — Weather info via wttr.in (free, no API key).
"""
from __future__ import annotations

import json
from urllib import parse as urlparse, request as urlreq


def skill_weather(args: str) -> str:
    """Get weather info from wttr.in (free, no API key)."""
    location = args.strip() or "Indore"
    try:
        url = f"https://wttr.in/{urlparse.quote(location)}?format=j1"
        req = urlreq.Request(url, headers={"User-Agent": "FRIDAY/1.0"})
        with urlreq.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())

        current = data.get("current_condition", [{}])[0]
        temp_c = current.get("temp_C", "?")
        desc = current.get("weatherDesc", [{}])[0].get("value", "unknown")
        humidity = current.get("humidity", "?")
        feels = current.get("FeelsLikeC", "?")
        wind = current.get("windspeedKmph", "?")

        area = data.get("nearest_area", [{}])[0]
        city = area.get("areaName", [{}])[0].get("value", location)

        return (
            f"Weather in {city}: {desc}, {temp_c} degrees celsius, "
            f"feels like {feels} degrees. "
            f"Humidity is {humidity} percent. "
            f"Wind speed is {wind} kilometers per hour."
        )
    except Exception as exc:
        return f"Could not get weather: {exc}"
