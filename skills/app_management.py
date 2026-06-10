"""
skills/app_management.py — Open, close, and clear application skills.
"""
from __future__ import annotations

import os
import shutil
import subprocess

from ._constants import _APP_REGISTRY, _BROWSER_APPS
from ._utils import _find_executable


def skill_open_app(args: str) -> str:
    """Open a Windows application by name."""
    # Import here to avoid circular imports at module level
    from .web_browser import skill_open_url_in_existing_browser

    app_name = args.strip().lower()
    if not app_name:
        return "No application name provided."

    # Clean leading articles and common conversational prefixes
    for prefix in ["the ", "a ", "an ", "my "]:
        if app_name.startswith(prefix):
            app_name = app_name[len(prefix):].strip()
    # Clean trailing noise words like "app" or "application"
    for suffix in [" app", " application"]:
        if app_name.endswith(suffix):
            app_name = app_name[:-len(suffix)].strip()

    # Intercept browser apps
    if app_name in _BROWSER_APPS:
        return skill_open_url_in_existing_browser(_BROWSER_APPS[app_name])

    exe = _APP_REGISTRY.get(app_name)
    if exe:
        # Replace {user} placeholder
        user = os.environ.get("USERNAME", os.environ.get("USER", ""))
        exe = exe.replace("{user}", user)
        # Resolve hardcoded paths through _find_executable if the path doesn't exist
        known_paths = [exe] if not os.path.exists(exe) and os.path.isabs(exe) else []
        if known_paths:
            exe = _find_executable(os.path.basename(exe), known_paths=known_paths)
    else:
        # Try running it directly (works for PATH-accessible apps)
        exe = app_name

    # Try resolving via shutil.which for absolute path resolution
    resolved = shutil.which(exe.split()[0] if exe else "")
    if resolved:
        # Re-attach any arguments if present
        parts = exe.split(maxsplit=1)
        if len(parts) > 1:
            exe = f'"{resolved}" {parts[1]}'
        else:
            exe = resolved

    try:
        if exe.startswith("ms-") or exe.endswith(".lnk") or exe.endswith(".url"):
            # UWP / ms-settings links / shortcuts
            os.startfile(exe)
        elif " " not in exe or os.path.exists(exe):
            # No arguments and is a simple exe/path — use os.startfile for reliable interactive GUI launch
            os.startfile(exe)
        else:
            # Has arguments (e.g. Discord) — use Popen
            subprocess.Popen(
                exe, shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        return f"Opened {app_name}."
    except Exception as exc:
        # Fallback to Popen if startfile fails
        try:
            subprocess.Popen(
                exe, shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return f"Opened {app_name}."
        except Exception as exc2:
            return f"Could not open {app_name}: {exc2}"


def skill_close_app(args: str) -> str:
    """Close a running application by name."""
    app_name = args.strip().lower()
    if not app_name:
        return "No application name provided."

    # Clean leading articles and common conversational prefixes
    for prefix in ["the ", "a ", "an ", "my "]:
        if app_name.startswith(prefix):
            app_name = app_name[len(prefix):].strip()
    # Clean trailing noise words like "app" or "application"
    for suffix in [" app", " application"]:
        if app_name.endswith(suffix):
            app_name = app_name[:-len(suffix)].strip()

    # Alias map: common names → actual Windows process names
    _PROCESS_ALIASES = {
        "chrome": "msedge",      # user has Edge, not Chrome
        "browser": "msedge",
        "edge": "msedge",
        "microsoft edge": "msedge",
        "explorer": "explorer",
        "word": "winword",
        "excel": "excel",
        "powerpoint": "powerpnt",
        "vscode": "code",
        "vs code": "code",
        "terminal": "WindowsTerminal",
        "cmd": "cmd",
        "calculator": "CalculatorApp",
        "calc": "CalculatorApp",
    }
    process_name = _PROCESS_ALIASES.get(app_name, app_name)

    try:
        result = subprocess.run(
            ["taskkill", "/IM", f"{process_name}.exe", "/F"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            return f"Closed {app_name}."

        # If it was calculator, try Calculator.exe as a fallback (for post-2021 Windows versions)
        if process_name == "CalculatorApp":
            result_calc = subprocess.run(
                ["taskkill", "/IM", "Calculator.exe", "/F"],
                capture_output=True, text=True, timeout=5,
            )
            if result_calc.returncode == 0:
                return f"Closed {app_name}."

        # If alias didn't work, try original name as fallback
        if process_name != app_name:
            result2 = subprocess.run(
                ["taskkill", "/IM", f"{app_name}.exe", "/F"],
                capture_output=True, text=True, timeout=5,
            )
            if result2.returncode == 0:
                return f"Closed {app_name}."
        return f"Could not find {app_name} running."
    except Exception as exc:
        return f"Failed to close {app_name}: {exc}"


def skill_close_tab(args: str) -> str:
    """Close the current browser tab (Ctrl+W). Does NOT kill the entire browser."""
    from automation import press_hotkey, focus_window
    import time
    import re

    hint = args.strip()
    hint = re.sub(r"\s+tabs?$", "", hint, flags=re.IGNORECASE).strip()
    focused = False
    if hint:
        res = focus_window(hint)
        if "Focused" in res:
            focused = True
            time.sleep(0.3)
    else:
        # Safe default: try to focus any active browser window first
        for browser_hint in ("edge", "chrome", "firefox", "browser", "msedge"):
            res = focus_window(browser_hint)
            if "Focused" in res:
                focused = True
                time.sleep(0.3)
                break

    if not focused and not hint:
        return "Refused: Could not find or focus any browser window to safely close a tab."

    result = press_hotkey("ctrl+w")
    if "Pressed" in result:
        return f"Closed current tab{' (' + hint + ')' if hint else ''}."
    return f"Could not close tab: {result}"


def skill_clear_app(args: str = "") -> str:
    """Selects all content in the focused app and deletes it."""
    import pyautogui
    import time
    pyautogui.hotkey("ctrl", "a")
    time.sleep(0.1)
    pyautogui.press("delete")
    return "Cleared all content in focused window."
