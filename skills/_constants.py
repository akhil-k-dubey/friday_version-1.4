"""
skills/_constants.py — Shared constants, registries, and module-level state.

All mutable global state (WhatsApp targets, active timers, etc.) lives here
so that multiple skill modules can read/write consistently.
"""
from __future__ import annotations

import os
from typing import Dict, List, Optional, Set


# ── App registry — common Windows apps ──────────────────────────────────────

_APP_REGISTRY: Dict[str, str] = {
    "notepad":    "notepad.exe",
    "calculator": "calc.exe",
    "calc":       "calc.exe",
    "paint":      "mspaint.exe",
    "explorer":   "explorer.exe",
    "file explorer": "explorer.exe",
    "files":      "explorer.exe",
    "cmd":        "cmd.exe",
    "terminal":   "wt.exe",
    "powershell": "powershell.exe",
    "task manager": "taskmgr.exe",
    "taskmgr":    "taskmgr.exe",
    "settings":   "ms-settings:",
    "control panel": "control.exe",
    "chrome":     r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "google chrome": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "firefox":    r"C:\Program Files\Mozilla Firefox\firefox.exe",
    "edge":       "msedge.exe",
    "microsoft edge": "msedge.exe",
    "brave":      r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
    "vscode":     "code",
    "vs code":    "code",
    "visual studio code": "code",
    "spotify":    r"C:\Users\{user}\AppData\Roaming\Spotify\Spotify.exe",
    "discord":    r"C:\Users\{user}\AppData\Local\Discord\Update.exe --processStart Discord.exe",
    "vlc":        r"C:\Program Files\VideoLAN\VLC\vlc.exe",
    "obs":        r"C:\Program Files\obs-studio\bin\64bit\obs64.exe",
}

# Browser process name → executable to launch a URL in that browser
_BROWSER_PROC_MAP: Dict[str, str] = {
    "msedge.exe":    "msedge.exe",
    "chrome.exe":    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "brave.exe":     r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
    "firefox.exe":   r"C:\Program Files\Mozilla Firefox\firefox.exe",
}

# WhatsApp state storage (mutable — written by messaging.py and intent.py)
_last_whatsapp_target: Optional[str] = None
_last_whatsapp_message: Optional[str] = None
_last_whatsapp_time: float = 0.0

# Apps that should run in the web browser
_BROWSER_APPS: Dict[str, str] = {
    "youtube":    "https://www.youtube.com",
    "gmail":      "https://mail.google.com",
    "whatsapp":   "https://web.whatsapp.com",
    "instagram":  "https://www.instagram.com",
    "google":     "https://www.google.com",
    "netflix":    "https://www.netflix.com",
    "chatgpt":    "https://chatgpt.com",
    "spotify":    "https://open.spotify.com",
}

# Site name → URL (for smart_open)
_SITE_MAP: Dict[str, str] = {
    "youtube":    "https://www.youtube.com",
    "gmail":      "https://mail.google.com",
    "github":     "https://github.com",
    "google":     "https://www.google.com",
    "chatgpt":    "https://chat.openai.com",
    "netflix":    "https://www.netflix.com",
    "twitter":    "https://twitter.com",
    "x":          "https://twitter.com",
    "reddit":     "https://www.reddit.com",
    "linkedin":   "https://www.linkedin.com",
    "stackoverflow": "https://stackoverflow.com",
    "wikipedia":  "https://www.wikipedia.org",
    "whatsapp":   "https://web.whatsapp.com",
    "instagram":  "https://www.instagram.com",
    "spotify":    "https://open.spotify.com",
    "notion":     "https://notion.so",
    # AI & Dev
    "claude":     "https://claude.ai",
    "claude ai":  "https://claude.ai",
    "perplexity": "https://www.perplexity.ai",
    "copilot":    "https://copilot.microsoft.com",
    "huggingface":"https://huggingface.co",
    "kaggle":     "https://www.kaggle.com",
    "colab":      "https://colab.research.google.com",
    "figma":      "https://www.figma.com",
    "vercel":     "https://vercel.com",
    # Browser aliases — so smart_open doesn't turn "browser" into "https://browser/"
    "browser":          "https://www.google.com",
    "edge":             "https://www.google.com",
    "microsoft edge":   "https://www.google.com",
    "chrome":           "https://www.google.com",
    "firefox":          "https://www.google.com",
}

# ── Timer storage ───────────────────────────────────────────────────────────

_active_timers: List[dict] = []

# ── Phase 4 constants ───────────────────────────────────────────────────────

_RESULT_LIMIT = 500   # max chars spoken to avoid wall-of-text in voice

# Paths that file_write must never touch
_BLOCKED_WRITE_DIRS = [
    os.environ.get("SystemRoot", r"C:\Windows"),
    r"C:\Windows", r"C:\System32", r"C:\Program Files",
    r"C:\Program Files (x86)", "/etc", "/usr", "/bin", "/sbin",
]

# Search roots for find_and_open — limited to user directories only.
_SEARCH_ROOTS = [
    os.path.expanduser("~\\Desktop"),
    os.path.expanduser("~\\Documents"),
    os.path.expanduser("~\\Downloads"),
    os.path.expanduser("~\\Pictures"),
    os.path.expanduser("~\\Videos"),
    os.path.expanduser("~\\Music"),
]

# Directories to skip during deep search (speeds up + avoids noise)
_SKIP_DIRS: Set[str] = {
    "Windows", "System32", "SysWOW64", "$Recycle.Bin", "ProgramData",
    "AppData\\Local\\Temp", "node_modules", ".git", "__pycache__",
    "WinSxS", "Temp",
}
