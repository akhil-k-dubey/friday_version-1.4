"""
skills/intent.py — Pre-LLM intent detector for obvious skill commands.

Qwen3 8B frequently ignores the [ACTION:...] tag format and responds
conversationally ("Sure, opening notepad for you.") without actually
invoking the skill. This fast regex-based detector intercepts obvious
commands BEFORE they reach the LLM, ensuring instant + reliable execution.
"""
from __future__ import annotations

import re
import time
from typing import Optional

from . import _constants
from ._constants import _SITE_MAP, _APP_REGISTRY


def detect_direct_intent(user_input: str) -> Optional[tuple[str, str, str]]:
    """
    Fast pre-LLM intent detector for obvious skill commands.

    Returns (skill_name, skill_args, spoken_response) if a clear intent
    is detected, or None if the input should go to the LLM.
    """
    text = user_input.strip()
    lower = text.lower()
    # Normalize common speech artifacts
    clean = re.sub(r"[^a-z0-9\s]", " ", lower)
    clean = re.sub(r"\s+", " ", clean).strip()

    # ── Open app ────────────────────────────────────────────────────────
    m = re.match(
        r"(?:please\s+)?(?:can you\s+)?(?:hey\s+friday\s+)?"
        r"(?:open|launch|start|run)\s+(.+)",
        clean,
    )
    if m:
        app_raw = m.group(1).strip()
        # Remove trailing filler ("for me", "please", "now")
        app_raw = re.sub(r"\s+(for me|please|now|real quick|quickly)$", "", app_raw)

        # Check if it's a website (smart_open) vs a desktop app (open_app)
        if app_raw in _SITE_MAP:
            return ("smart_open", app_raw, f"Opening {app_raw.title()} for you, sir.")
        if app_raw in _APP_REGISTRY:
            return ("open_app", app_raw, f"Opening {app_raw.title()} for you, sir.")
        # Could be an app not in registry — still try open_app
        if len(app_raw.split()) <= 2 and not any(
            w in app_raw for w in ("the", "a", "my", "this", "that", "door", "window", "curtain")
        ):
            return ("open_app", app_raw, f"Opening {app_raw} for you, sir.")

    # ── Close app ───────────────────────────────────────────────────────
    m = re.match(
        r"(?:please\s+)?(?:can you\s+)?"
        r"(?:close|kill|stop|quit|exit|terminate|end)\s+(.+)",
        clean,
    )
    if m:
        app_raw = m.group(1).strip()
        app_raw = re.sub(r"\s+(for me|please|now)$", "", app_raw)
         # Route tab/site close commands to close_tab, not close_app
        _TAB_HINTS = {"tab", "this tab", "the tab", "current tab"}
        _SITE_CLOSE_HINTS = {
            "youtube", "gmail", "github", "reddit", "twitter",
            "netflix", "whatsapp", "instagram", "google",
            "linkedin", "stackoverflow", "wikipedia", "spotify",
            "chatgpt", "claude", "perplexity", "copilot",
        }
        _PRONOUNS = {"it", "this", "that", "them", "app", "the app", "application", "the application", "window", "the window", "program", "the program"}

        is_tab = "tab" in app_raw.lower()
        is_site = any(site in app_raw.lower() for site in _SITE_CLOSE_HINTS)

        if app_raw in _PRONOUNS:
            # Skip direct routing; let LLM resolve the context-dependent pronoun/noun
            pass
        elif is_tab or is_site or app_raw in _TAB_HINTS:
            return ("close_tab", app_raw, f"Closing {app_raw} tab.")
        elif app_raw and len(app_raw.split()) <= 3:
            return ("close_app", app_raw, f"Closing {app_raw}.")

    # ── Volume ──────────────────────────────────────────────────────────
    if re.match(r"(?:turn\s+)?volume\s+(up|down|mute|unmute)", clean):
        action = re.search(r"(up|down|mute|unmute)", clean).group(1)
        return ("volume", action, f"Volume {action}.")
    if clean in ("mute", "unmute", "mute volume", "unmute volume"):
        action = "mute" if "unmute" not in clean else "unmute"
        return ("volume", action, f"Volume {action}.")

    # Match: "volume 100", "volume 50%", "set volume to max", etc.
    volume_match = re.match(
        r"(?:set\s+|turn\s+)?volume\s+(?:to\s+)?(\d+%?|max|maximum|full|high|medium|half|low|min|minimum|zero|off)",
        clean
    )
    if volume_match:
        action = volume_match.group(1)
        return ("volume", action, f"Setting volume to {action}.")

    # ── Weather ─────────────────────────────────────────────────────────
    m = re.match(
        r"(?:what(?:'s| is) the )?weather\s*(?:in\s+(.+))?|"
        r"(?:how(?:'s| is) the )?weather\s*(?:in\s+(.+))?|"
        r"(?:what(?:'s| is) the )?temperature\s*(?:in\s+(.+))?",
        clean,
    )
    if m:
        location = (m.group(1) or m.group(2) or m.group(3) or "").strip()
        return ("weather", location or "Indore", "Let me check the weather.")

    # ── Timer ───────────────────────────────────────────────────────────
    m = re.match(
        r"(?:set\s+(?:a\s+)?)?timer\s+(?:for\s+)?(\d+)\s*(s|sec|seconds?|m|min|minutes?|h|hours?)",
        clean,
    )
    if m:
        amount = m.group(1)
        unit = m.group(2)[0]  # s, m, or h
        return ("timer", f"{amount}{unit}", f"Setting a timer for {amount} {m.group(2)}.")

    # ── Remind ──────────────────────────────────────────────────────────
    m = re.match(
        r"remind\s+(?:me\s+)?(?:to\s+)?(?:in\s+)?(\d+)\s*(s|sec|seconds?|m|min|minutes?|h|hours?)\s*(.*)",
        clean,
    )
    if m:
        amount = m.group(1)
        unit = m.group(2)[0]
        message = m.group(3).strip() or "Time's up"
        return ("remind", f"{amount}{unit} {message}", f"Reminder set.")

    # ── Screenshot ──────────────────────────────────────────────────────
    if re.match(r"(?:take\s+(?:a\s+)?)?screenshot", clean):
        return ("screenshot", "", "Taking a screenshot.")

    # ── Date/time ───────────────────────────────────────────────────────
    if clean in (
        "what time is it", "whats the time", "what is the time",
        "current time", "time", "time please",
    ):
        return ("datetime", "time", "")
    if clean in (
        "what day is it", "whats the date", "what is the date",
        "current date", "date", "todays date", "what date is it",
    ):
        return ("datetime", "date", "")

    # ── System info ─────────────────────────────────────────────────────
    if any(p in clean for p in (
        "system info", "system status", "cpu usage", "ram usage",
        "battery status", "battery level", "how much ram", "how much battery",
        "how is my system", "system health",
    )):
        return ("system_info", "", "Checking system status.")

    # ── Read Screen ─────────────────────────────────────────────────────
    if any(p in clean for p in (
        "read screen", "read my screen", "what s on my screen", "what's on my screen", "what is on my screen",
        "read this for me", "read this", "what do you see on my screen",
        "what do you see", "analyze screen", "analyze my screen"
    )):
        return ("read_screen", "", "Let me read your screen.")

    # ── Calculator ──────────────────────────────────────────────────────
    m = re.match(
        r"(?:calculate|what(?:'s| is)|compute|solve)\s+(.+)",
        clean,
    )
    if m:
        expr = m.group(1).strip()
        # Only match if it looks like a math expression
        if re.search(r"\d", expr) and re.search(r"[+\-*/^%]|(?:plus|minus|times|divided|power|sqrt|root)", expr):
            return ("calculator", expr, "")

    # ── WhatsApp check/send direct routing ──────────────────────────────

    # Check for unread or new messages
    if any(p in clean for p in ("check whatsapp", "any new messages", "get a new message", "whatsapp notifications")):
        return ("whatsapp_check_messages", "", "Checking WhatsApp messages for you.")

    # Match "send same message to Jay"
    if "same" in clean or "last" in clean:
        same_match = re.search(r"(?:same|last)\s+(?:message\s+|msg\s+|text\s+|whatsapp\s+)?(?:to\s+|with\s+|for\s+|at\s+)?(\w+)$", clean)
        if same_match:
            contact = same_match.group(1).strip()
            if contact and contact.lower() not in ("me", "him", "her", "them", "whatsapp", "message", "msg", "text", "it"):
                if _constants._last_whatsapp_message:
                    _constants._last_whatsapp_target = contact
                    _constants._last_whatsapp_time = time.monotonic()
                    return ("whatsapp", f"{contact}||{_constants._last_whatsapp_message}", f"Sending the same WhatsApp message to {contact.title()}.")

    # Match corrections
    if _constants._last_whatsapp_target and (time.monotonic() - _constants._last_whatsapp_time < 30.0):
        correction_match = re.match(
            r"(?:no\s+|not\s+that\s+|i\s+meant\s+|tell\s+him\s+|tell\s+her\s+|say\s+)(.+)",
            clean
        )
        if correction_match:
            corrected_msg = correction_match.group(1).strip()
            is_new_msg_cmd = any(w in clean for w in ("send ", "message to", "whatsapp to", "tell ", "msg to"))
            if not is_new_msg_cmd:
                corrected_msg = re.sub(r"^(?:say\s+|send\s+|tell\s+him\s+|tell\s+her\s+)", "", corrected_msg).strip()
                if len(corrected_msg.split()) > 0 and corrected_msg not in ("yes", "no", "ok", "sure"):
                    _constants._last_whatsapp_message = corrected_msg
                    _constants._last_whatsapp_time = time.monotonic()
                    return ("whatsapp", f"{_constants._last_whatsapp_target.lower()}||{corrected_msg}", f"Correcting message to {_constants._last_whatsapp_target.title()}.")

    # Match new WhatsApp send message
    whatsapp_patterns = [
        r"(?:send\s+)?(?:a\s+)?(?:message|whatsapp|msg|text)\s+(?:on|in|via|through\s+)?(?:whatsapp\s+)?(?:to|with|for|at)\s+(\w+)\s+(?:saying|say|that|to|msg|about|asking)\s+(.+)",
        r"(?:whatsapp|message|tell|text|msg)\s+(\w+)\s+(?:on|in|via|through\s+)?(?:whatsapp\s+)?(?:saying|say|that|to|msg|about|asking)\s+(.+)",
        r"send\s+(\w+)\s+(?:a\s+)?(?:whatsapp\s+)?(?:message|whatsapp|msg|text)\s+(?:saying|say|that|to|msg|about|asking)\s+(.+)",
        r"(?:on|in|via)\s+whatsapp\s+(?:send\s+)?(?:a\s+)?(?:message|msg|text)?\s*(?:to|with|for)?\s*(\w+)\s+(?:saying|say|that|to|msg|about|asking)\s+(.+)"
    ]

    for pat in whatsapp_patterns:
        m = re.search(pat, clean)
        if m:
            contact = m.group(1).strip()
            message = m.group(2).strip()
            if contact and message and contact.lower() not in ("me", "him", "her", "them", "whatsapp", "message", "msg", "text"):
                _constants._last_whatsapp_target = contact
                _constants._last_whatsapp_message = message
                _constants._last_whatsapp_time = time.monotonic()
                return ("whatsapp", f"{contact}||{message}", f"Sending WhatsApp message to {contact.title()}.")

    # ── Clear content direct routing ────────────────────────────────────
    if re.match(r"(?:please\s+)?(?:clear|erase|delete|wipe)\s+(everything|all|the\s+content|it|notepad|the\s+notepad)", clean):
        return ("clear_app", "", "Clearing the screen.")

    # ── Switch to / focus window direct routing ──────────────────────────
    switch_match = re.match(
        r"(?:please\s+)?(?:can you\s+)?(?:switch\s+to|go\s+to|focus\s+on)\s+(.+)",
        clean
    )
    if switch_match:
        app_raw = switch_match.group(1).strip()
        app_raw = re.sub(r"\s+(for me|please|now)$", "", app_raw)
        if app_raw and len(app_raw.split()) <= 3:
            return ("focus_window", app_raw, f"Switching to {app_raw.title()}.")

    # ── Remember direct routing ─────────────────────────────────────────
    remember_match = re.match(
        r"(?:please\s+)?(?:can you\s+)?(?:remember\s+that|remember)\s+(.+)",
        clean
    )
    if remember_match:
        content = remember_match.group(1).strip()
        return ("remember", content, "I've saved that to my memory.")

    # ── Recall direct routing ───────────────────────────────────────────
    recall_match = re.match(
        r"(?:please\s+)?(?:can you\s+)?(?:recall|what\s+did\s+i\s+ask\s+you\s+to\s+remember\s+about|what\s+do\s+you\s+remember\s+about|what\s+is\s+my|what\s+is\s+the\s+note\s+on)\s+(.+)",
        clean
    )
    if recall_match:
        query = recall_match.group(1).strip()
        return ("recall", query, f"Let me check my memories for {query}.")

    # ── System diagnostics direct routing ───────────────────────────────
    if any(p in clean for p in ("how is my cpu", "cpu usage", "system diagnostics", "system health", "diagnose system")):
        return ("system_diagnostics", "", "Running system diagnostics.")

    summarize_match = re.match(
        r"(?:please\s+)?(?:can you\s+)?(?:summarize\s+the\s+webpage\s+|summarize\s+the\s+url\s+|summarize\s+|fetch\s+and\s+summarize\s+)(https?://\S+)",
        lower
    )
    if summarize_match:
        url = summarize_match.group(1).strip()
        return ("summarize_url", url, f"Fetching and summarizing {url}.")

    # ── Memory Explanation direct routing ───────────────────────────────
    if any(p in clean for p in (
        "do you have a long time memory or short time memory",
        "do you have long time memory or short time memory",
        "do you have a long term memory or short term memory",
        "do you have long term memory or short term memory",
        "do you have long term or short term memory",
        "do you have long time or short time memory",
        "what kind of memory do you have"
    )):
        return ("memory_explain", "", "Let me explain my memory system, sir.")

    # No clear intent detected — let the LLM handle it
    return None
