"""
skills — Built-in skill engine for FRIDAY.

Every skill is a callable that returns a string result.
The LLM triggers skills by emitting [ACTION:skill_name:args] in its response.
The main loop intercepts these, runs the skill, and feeds the result back.

All tools are FREE FOREVER — no API keys required.

This package re-exports everything that was previously in the monolithic skills.py
for full backward compatibility.
"""
from __future__ import annotations

# ── Core exports ────────────────────────────────────────────────────────────
from .engine import SkillEngine
from .intent import detect_direct_intent

# ── Announce hook setter (replaces direct module attribute assignment) ───────
from ._utils import set_announce_fn

# ── Constants re-exports (used by oracle.py, test files) ────────────────────
from ._constants import _SITE_MAP, _APP_REGISTRY

# ── Skill function re-exports (used by _verify_fixes.py, test files) ────────
from .app_management import skill_open_app, skill_close_app, skill_close_tab, skill_clear_app
from .web_browser import (
    skill_web_search, skill_open_url, skill_open_url_in_existing_browser,
    skill_smart_open, skill_browser_search, skill_youtube_search, skill_summarize_url,
)
from .system import skill_system_info, skill_system_diagnostics, skill_screenshot, skill_read_screen
from .clipboard import (
    skill_clipboard_read, skill_clipboard_write,
    skill_clipboard_history, skill_clipboard_paste_previous,
    clipboard_ring, ClipboardRing,
)
from .volume import skill_volume
from .timer_remind import skill_timer, skill_remind
from .calculator import skill_calculator
from .weather import skill_weather
from .datetime_skill import skill_datetime
from .files import (
    skill_file_search, skill_open_file, skill_search_file,
    skill_rename_file, skill_move_file, skill_find_and_open,
    skill_file_read, skill_file_write, skill_file_edit,
)
from .memory_skills import skill_remember, skill_recall, skill_memory_explain
from .messaging import skill_whatsapp, skill_whatsapp_check_messages
from .code import skill_run_code, skill_git_query
from .desktop import (
    skill_powershell, skill_type_text, skill_press_keys, skill_click,
    skill_scroll, skill_focus_window, skill_list_windows, skill_wait,
    skill_process_list,
)

# ── Backward compatibility for _announce_fn attribute assignment ────────────
# main.py does: import skills as _skills_mod; _skills_mod._announce_fn = voice.speak_alarm
# This intercepts that and forwards to _utils.set_announce_fn()
from ._utils import _announce_fn as _announce_fn  # noqa: F811 — re-export for reads

def __getattr__(name):
    """Module-level __getattr__ for backward-compatible attribute access."""
    if name == "_announce_fn":
        from ._utils import _announce_fn as _fn
        return _fn
    raise AttributeError(f"module 'skills' has no attribute {name!r}")
