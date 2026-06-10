"""
skills/_utils.py — Shared utility functions used across skill modules.
"""
from __future__ import annotations

import os
import platform
import shutil
import subprocess
from typing import Callable, Optional

from ._constants import _BROWSER_PROC_MAP, _RESULT_LIMIT


# ── Executable path resolver ───────────────────────────────────────────────

def _find_executable(name: str, known_paths: Optional[list[str]] = None) -> str:
    """Resolve an executable path. Tries: shutil.which → registry → known paths."""
    # Try PATH first
    resolved = shutil.which(name)
    if resolved:
        return resolved
    # Try registry (App Paths)
    if platform.system() == "Windows":
        name_base = name[:-4] if name.lower().endswith(".exe") else name
        try:
            import winreg
            key_path = rf"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\{name_base}.exe"
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path, 0, winreg.KEY_READ) as key:
                resolved = winreg.QueryValue(key, None)
                if resolved and os.path.exists(resolved):
                    return resolved
        except (OSError, ImportError):
            pass
        try:
            # Also check HKCU
            import winreg
            key_path = rf"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\{name_base}.exe"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ) as key:
                resolved = winreg.QueryValue(key, None)
                if resolved and os.path.exists(resolved):
                    return resolved
        except (OSError, ImportError):
            pass
    # Known fallback paths
    if known_paths:
        for p in known_paths:
            expanded = os.path.expandvars(os.path.expanduser(p))
            if os.path.exists(expanded):
                return expanded
    return name  # return as-is, might work via shell


# ── Sounddevice beep helper ────────────────────────────────────────────────

try:
    import sounddevice as _sd_beep
    import numpy as _np_beep
    _HAVE_SD = True
except ImportError:
    _sd_beep = None  # type: ignore
    _np_beep = None  # type: ignore
    _HAVE_SD = False


def _play_beep(freq: float, duration_ms: int, volume: float = 0.3) -> None:
    """Play a sine-wave beep via sounddevice (non-blocking)."""
    if not _HAVE_SD:
        return
    try:
        sr = 22050
        t = _np_beep.linspace(0, duration_ms / 1000, int(sr * duration_ms / 1000), endpoint=False)
        tone = (volume * _np_beep.sin(2 * _np_beep.pi * freq * t)).astype(_np_beep.float32)
        _sd_beep.play(tone, sr)
    except Exception:
        pass


# ── Announce hook ────────────────────────────────────────────────────────────
# Set by main.py via set_announce_fn() so timer/remind fire spoken alerts.
# If None, falls back to print-only.

_announce_fn: Optional[Callable[[str], None]] = None


def set_announce_fn(fn: Optional[Callable[[str], None]]) -> None:
    """Set the voice announce callback (called by main.py at startup)."""
    global _announce_fn
    _announce_fn = fn


def _announce(msg: str) -> None:
    """Print and optionally speak a timed alert message."""
    print(f"\n{'='*60}")
    print(f"  {msg}")
    print(f"{'='*60}")
    if _announce_fn is not None:
        try:
            _announce_fn(msg)
        except Exception:
            pass


# ── Text truncation ─────────────────────────────────────────────────────────

def _truncate(text: str, limit: int = _RESULT_LIMIT) -> str:
    """Trim result to voice-safe length."""
    text = text.strip()
    if len(text) > limit:
        return text[:limit] + f"… [{len(text)-limit} chars truncated]"
    return text


# ── Type or paste safely ────────────────────────────────────────────────────

def _type_or_paste_safely(text: str, interval: float = 0.01) -> None:
    """Type text safely. If it is long or contains non-ASCII characters, copy it to clipboard and paste it to avoid drops."""
    is_ascii = all(ord(c) < 128 for c in text)
    if is_ascii and len(text) <= 5:
        import pyautogui
        pyautogui.typewrite(text, interval=interval)
    else:
        import pyperclip
        import pyautogui
        import time
        pyperclip.copy(text)
        time.sleep(0.05)
        pyautogui.hotkey("ctrl", "v")
        time.sleep(0.05)


# ── UI text collector ───────────────────────────────────────────────────────

def _collect_text(ctrl, results: list, depth: int, max_depth: int):
    if depth > max_depth or len(results) >= 150:  # limit total collected nodes
        return

    # Ignore purely structural layout panels
    name = getattr(ctrl, "Name", "") or ""
    val = ""
    try:
        val = ctrl.GetValuePattern().Value or ""
    except Exception:
        pass

    text = (name + " " + val).strip()
    if text and len(text) > 1 and not text.isdigit():
        results.append(text)

    for child in ctrl.GetChildren():
        _collect_text(child, results, depth + 1, max_depth)


# ── Browser detection ───────────────────────────────────────────────────────

def _get_active_browser() -> Optional[str]:
    """
    Detect which browser is currently running using psutil.
    Returns the executable path/name to use for opening a URL,
    or None if no browser is found (caller falls back to webbrowser.open).
    Priority: Edge > Chrome > Brave > Firefox (matches most common Windows setups).
    """
    try:
        import psutil
        running = {p.name().lower() for p in psutil.process_iter(["name"])}
        for proc_name, exe in _BROWSER_PROC_MAP.items():
            if proc_name.lower() in running:
                return exe
    except Exception:
        pass
    return None


def _open_url_in_browser(url: str, browser_exe: Optional[str] = None) -> str:
    """
    Open a URL — in the active browser if detected, else via webbrowser.open().
    Always opens as a new tab in the existing window (--new-tab flag).
    """
    if browser_exe is None:
        browser_exe = _get_active_browser()

    if browser_exe:
        try:
            # --new-tab opens in the existing browser window
            subprocess.Popen([browser_exe, "--new-tab", url],
                             creationflags=subprocess.DETACHED_PROCESS)
            return browser_exe
        except Exception:
            pass   # fall through to webbrowser

    import webbrowser
    webbrowser.open(url)
    return "default browser"
