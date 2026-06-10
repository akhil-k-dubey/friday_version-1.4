"""
skills/desktop.py — Desktop automation thin wrappers.

These are thin delegates to the root-level automation.py module.
"""
from __future__ import annotations


def skill_powershell(args: str) -> str:
    """Run a PowerShell command (sandboxed, dangerous commands blocked)."""
    from automation import powershell_exec
    return powershell_exec(args)


def skill_type_text(args: str) -> str:
    """Type text at the current cursor position using keyboard simulation."""
    from automation import type_text
    return type_text(args)


def skill_press_keys(args: str) -> str:
    """Press a keyboard shortcut (e.g. ctrl+c, alt+tab, enter, ctrl+shift+n)."""
    from automation import press_hotkey
    return press_hotkey(args)


def skill_click(args: str) -> str:
    """Click at x,y coordinates or current cursor position. Args: 'x,y' or empty."""
    from automation import click_at
    return click_at(args)


def skill_scroll(args: str) -> str:
    """Scroll up or down. Args: 'up 5' or 'down 3'."""
    from automation import scroll_mouse
    return scroll_mouse(args)


def skill_focus_window(args: str) -> str:
    """Focus/switch to a window by title. Args: partial window title."""
    from automation import focus_window
    return focus_window(args)


def skill_list_windows(args: str) -> str:
    """List all visible windows with their titles."""
    from automation import list_windows
    return list_windows()


def skill_wait(args: str) -> str:
    """Wait for N seconds (max 30). Use for page/app load delays."""
    from automation import wait_seconds
    return wait_seconds(args)


def skill_process_list(args: str) -> str:
    """List running processes, optionally filtered. Args: filter name or empty."""
    from automation import list_processes
    return list_processes(args)
