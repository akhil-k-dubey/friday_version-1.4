"""
skills/engine.py — SkillEngine class: dispatches [ACTION:skill:args] tags from LLM output.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable, Dict, Optional

# Import all skill functions from submodules
from .app_management import skill_open_app, skill_close_app, skill_close_tab, skill_clear_app
from .web_browser import (
    skill_web_search, skill_open_url, skill_open_url_in_existing_browser,
    skill_smart_open, skill_browser_search, skill_youtube_search, skill_summarize_url,
)
from .system import skill_system_info, skill_system_diagnostics, skill_screenshot, skill_read_screen
from .clipboard import (
    skill_clipboard_read, skill_clipboard_write,
    skill_clipboard_history, skill_clipboard_paste_previous,
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


@dataclass
class SkillEngine:
    """
    Dispatches [ACTION:skill:args] tags from LLM output.
    """

    debug_fn: Optional[Callable] = None
    skills: Dict[str, Callable[[str], str]] = field(default_factory=dict)

    # Pattern: [ACTION:skill_name:arguments]  — tolerates whitespace around colons
    ACTION_PATTERN = re.compile(r'\[ACTION:\s*(\w+)\s*:\s*(.*?)\s*\]', re.DOTALL | re.IGNORECASE)
    # Fallback: catches common malformations (missing second colon, spaces)
    ACTION_FALLBACK = re.compile(r'\[ACTION:\s*(\w+)[\s:]+(.+?)\]', re.DOTALL | re.IGNORECASE)

    def __post_init__(self):
        self.skills = {
            "open_app":        skill_open_app,
            "close_app":       skill_close_app,
            "open_url":        skill_open_url,
            "web_search":      skill_web_search,
            "system_info":     skill_system_info,
            "clipboard_read":  skill_clipboard_read,
            "clipboard_write": skill_clipboard_write,
            "volume":          skill_volume,
            "timer":           skill_timer,
            "calculator":      skill_calculator,
            "weather":         skill_weather,
            "screenshot":      skill_screenshot,
            "file_search":     skill_file_search,
            "datetime":        skill_datetime,
            "remind":          skill_remind,
            # Phase 4 — Code, file, git, browser
            "file_read":       skill_file_read,
            "file_write":      skill_file_write,
            "file_edit":       skill_file_edit,
            "run_code":        skill_run_code,
            "git_query":       skill_git_query,
            "browser_search":  skill_browser_search,
            # Smart open, file finder, YouTube
            "smart_open":      skill_smart_open,
            "find_and_open":   skill_find_and_open,
            "youtube_search":  skill_youtube_search,
            # Phase 4+ — Desktop Automation & PowerShell
            "powershell":      skill_powershell,
            "type_text":       skill_type_text,
            "press_keys":      skill_press_keys,
            "click":           skill_click,
            "scroll":          skill_scroll,
            "focus_window":    skill_focus_window,
            "list_windows":    skill_list_windows,
            "wait":            skill_wait,
            "process_list":    skill_process_list,
            "close_tab":       skill_close_tab,
            "read_screen":     skill_read_screen,
            "open_url_in_existing_browser": skill_open_url_in_existing_browser,
            "whatsapp":        skill_whatsapp,
            "whatsapp_check_messages": skill_whatsapp_check_messages,
            "clear_app":       skill_clear_app,
            "remember":        skill_remember,
            "recall":          skill_recall,
            "system_diagnostics": skill_system_diagnostics,
            "open_file":       skill_open_file,
            "search_file":     skill_search_file,
            "rename_file":     skill_rename_file,
            "move_file":       skill_move_file,
            "summarize_url":   skill_summarize_url,
            "clipboard_history": skill_clipboard_history,
            "clipboard_paste_previous": skill_clipboard_paste_previous,
            "memory_explain":   skill_memory_explain,
        }

    def _debug(self, msg: str) -> None:
        if self.debug_fn:
            self.debug_fn(f"[skills] {msg}")

    def list_skills(self) -> str:
        """Human-readable list of available skills."""
        lines = []
        for name, fn in self.skills.items():
            doc = (fn.__doc__ or "").strip().split("\n")[0]
            lines.append(f"  {name}: {doc}")
        return "Available skills:\n" + "\n".join(lines)

    def _fuzzy_match_skill(self, name: str):
        """Fuzzy-match an unknown skill name to the closest known skill."""
        from difflib import get_close_matches
        matches = get_close_matches(name, self.skills.keys(), n=1, cutoff=0.75)
        return matches[0] if matches else None

    def validate_action_tags(self, text: str) -> tuple:
        """Check if [ACTION:] tags in text are well-formed and use valid skills.
        Returns (is_valid: bool, error_description: str).
        """
        if "[action" not in text.lower():
            return True, ""

        matches = list(self.ACTION_PATTERN.finditer(text))
        if not matches:
            # Tag marker present but primary regex failed — try fallback
            fallback = list(self.ACTION_FALLBACK.finditer(text))
            if not fallback:
                return False, (
                    "Malformed action tag. "
                    "Correct format: [ACTION:skill_name:arguments]"
                )
            matches = fallback

        for match in matches:
            skill_name = match.group(1).strip()
            if skill_name not in self.skills:
                closest = self._fuzzy_match_skill(skill_name)
                if not closest:
                    return False, (
                        f"Unknown skill '{skill_name}'. "
                        f"Available: {', '.join(sorted(self.skills.keys()))}"
                    )
        return True, ""

    def extract_and_execute(self, text: str) -> tuple[str, list[str]]:
        """
        Find all [ACTION:...] tags in text, execute them,
        and return (cleaned_text, list_of_results).
        Uses fuzzy matching for unknown skill names.
        Falls back to a lenient regex for malformed tags.
        """
        results = []
        matches = list(self.ACTION_PATTERN.finditer(text))

        # Fallback regex for malformed tags
        if not matches and "[action" in text.lower():
            matches = list(self.ACTION_FALLBACK.finditer(text))
            if matches:
                self._debug("Used fallback regex for malformed action tag")

        if not matches:
            return text, []

        for match in matches:
            skill_name = match.group(1).strip()
            skill_args = match.group(2).strip()

            # Fuzzy matching: auto-correct slightly wrong skill names
            fn = self.skills.get(skill_name)
            if fn is None:
                closest = self._fuzzy_match_skill(skill_name)
                if closest:
                    self._debug(f"Fuzzy matched '{skill_name}' → '{closest}'")
                    skill_name = closest
                    fn = self.skills[closest]

            self._debug(f"Executing skill: {skill_name}({skill_args})")

            if fn:
                try:
                    result = fn(skill_args)
                    results.append(result)
                    self._debug(f"Skill result: {result[:100]}")
                except Exception as exc:
                    error_msg = f"Skill {skill_name} failed: {exc}"
                    results.append(error_msg)
                    self._debug(error_msg)
            else:
                available = ", ".join(sorted(self.skills.keys()))
                results.append(f"Unknown skill: {skill_name}. Try: {available}")

        # Remove action tags from text (both patterns)
        cleaned = self.ACTION_PATTERN.sub("", text)
        cleaned = self.ACTION_FALLBACK.sub("", cleaned).strip()
        # Clean up leftover whitespace
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
        cleaned = re.sub(r'  +', ' ', cleaned)

        return cleaned, results

    def get_skill_prompt(self) -> str:
        """
        Returns instruction block for the LLM system prompt
        so it knows how to invoke skills.
        """
        return (
            "TOOL USE:\n"
            "You can perform real actions by including action tags in your response.\n"
            "Format: [ACTION:skill_name:arguments]\n\n"
            "═══ APPS & SYSTEM ═══\n"
            "  [ACTION:open_app:chrome] — open an application\n"
            "  [ACTION:close_app:notepad] — close an application\n"
            "  [ACTION:system_info:] — CPU, RAM, GPU/VRAM, battery\n"
            "  [ACTION:process_list:] — list running processes (optional filter name)\n"
            "  [ACTION:volume:up/down/mute/unmute] — control volume\n"
            "  [ACTION:clipboard_read:] — read clipboard\n"
            "  [ACTION:clipboard_write:text] — write to clipboard\n"
            "  [ACTION:screenshot:] — screenshot to Desktop\n"
            "  [ACTION:timer:30s or 5m] — countdown timer\n"
            "  [ACTION:remind:5m check oven] — timed reminder\n"
            "  [ACTION:calculator:2+2*3] — math evaluation\n"
            "  [ACTION:weather:Indore] — weather info\n"
            "  [ACTION:datetime:] — current date/time\n\n"
            "═══ BROWSER & WEB ═══\n"
            "  [ACTION:smart_open:youtube] — open named site in active browser\n"
            "  [ACTION:open_url:github.com] — open any URL\n"
            "  [ACTION:browser_search:query] — Google search in browser\n"
            "  [ACTION:youtube_search:lofi music] — play first YouTube result\n"
            "  [ACTION:web_search:query] — fetch search results as text\n\n"
            "═══ FILES & CODE ═══\n"
            "  [ACTION:file_read:/path/to/file.py] — read file (200 lines)\n"
            "  [ACTION:file_write:/path/file.txt||content] — write/create file\n"
            "  [ACTION:file_edit:/path/file.py||old_text||new_text] — surgical find-and-replace\n"
            "  [ACTION:file_search:report.pdf] — find files in common folders\n"
            "  [ACTION:find_and_open:resume.pdf] — find and open a file\n"
            "  [ACTION:run_code:python:print(1+2)] — run code (python/node, 10s)\n"
            "  [ACTION:git_query:status] — git status/diff/log/branch (read-only)\n\n"
            "═══ DESKTOP AUTOMATION ═══\n"
            "  [ACTION:type_text:Hello World] — type text at cursor position\n"
            "  [ACTION:press_keys:ctrl+c] — press keyboard shortcut\n"
            "  [ACTION:click:500,300] — click at x,y coordinates\n"
            "  [ACTION:scroll:down 5] — scroll up/down N clicks\n"
            "  [ACTION:focus_window:Chrome] — focus/switch to window by title\n"
            "  [ACTION:list_windows:] — list all visible windows\n"
            "  [ACTION:wait:3] — wait N seconds (for page loads etc.)\n"
            "  [ACTION:powershell:Get-Process] — run PowerShell command (sandboxed)\n\n"
            "═══ RULES ═══\n"
            "BROWSER: Use smart_open for named sites. Use youtube_search to play videos.\n"
            "  smart_open detects the active browser and opens in it.\n"
            "DESKTOP AUTOMATION WORKFLOW (for interacting with apps/websites):\n"
            "  1. smart_open or open_app to launch target\n"
            "  2. wait:2-3 for it to load\n"
            "  3. focus_window to ensure it's active\n"
            "  4. type_text / press_keys / click to interact\n"
            "  Example: open Claude AI, wait, focus, click text field, type prompt\n"
            "SECURITY:\n"
            "  file_write: blocked for C:\\Windows, system dirs. Safe paths are allowed.\n"
            "  run_code: no os.system, subprocess, network, file I/O in sandboxed code\n"
            "  powershell: destructive commands (format disk, delete system files) blocked\n"
            "  git_query: read-only (no push/commit/reset)\n"
            "ACTIONS: Use action tags ONLY when user asks to DO something.\n"
            "  For questions, answer normally without action tags.\n"
            "  You may include ONE action tag per response. Put it at the END.\n"
            "  After the action tag, do NOT add any more text.\n"
        )
