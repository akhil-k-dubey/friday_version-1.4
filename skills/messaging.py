"""
skills/messaging.py — WhatsApp send and check message skills.
"""
from __future__ import annotations

import re
import time

from . import _constants
from ._utils import _type_or_paste_safely


def skill_whatsapp(args: str) -> str:
    """Send a WhatsApp message. Args format: 'contact||message' or 'message' (reuses last contact)."""
    import pyautogui
    import win32gui
    from .web_browser import skill_open_url_in_existing_browser
    from .system import skill_read_screen

    parts = args.split("||", 1)
    if len(parts) == 2:
        contact, message = parts[0].strip(), parts[1].strip()
        _constants._last_whatsapp_target = contact
        _constants._last_whatsapp_message = message
    else:
        message = parts[0].strip()
        contact = _constants._last_whatsapp_target
        if not message and _constants._last_whatsapp_message:
            message = _constants._last_whatsapp_message

    if not contact:
        return "No contact target specified for WhatsApp."
    if not message:
        return "No message content provided."

    # Open/focus WhatsApp
    res = skill_open_url_in_existing_browser("https://web.whatsapp.com")

    # Wait for WhatsApp Web to fully load by checking screen content (up to 12.0s)
    start_wait = time.monotonic()
    loaded = False
    while time.monotonic() - start_wait < 12.0:
        scr = skill_read_screen()
        if "search" in scr.lower() or "unread" in scr.lower() or "chats" in scr.lower() or "status" in scr.lower():
            loaded = True
            break
        time.sleep(1.0)

    if not loaded:
        time.sleep(4.0)

    # Bring foreground window and click viewport to guarantee page focus
    edge_hwnd = win32gui.GetForegroundWindow()
    try:
        rect = win32gui.GetWindowRect(edge_hwnd)
        if rect[2] > rect[0] and rect[3] > rect[1]:
            safe_x = rect[0] + min(150, (rect[2] - rect[0]) // 4)
            safe_y = rect[1] + min(250, (rect[3] - rect[1]) // 3)
            pyautogui.click(safe_x, safe_y)
            time.sleep(0.3)
    except Exception:
        pass

    # Ensure any active menus or overlays are cleared first
    pyautogui.press("escape")
    time.sleep(0.2)

    # Focus search bar
    clicked = False
    try:
        import uiautomation as auto
        edge_ctrl = auto.ControlFromHandle(edge_hwnd)
        if edge_ctrl:
            search_elem = edge_ctrl.Control(searchDepth=15, Name="Search or start new chat")
            if not search_elem.Exists(0, 0):
                search_elem = edge_ctrl.Control(searchDepth=15, Name="Search")

            if search_elem.Exists(0.1, 0):
                rect = search_elem.BoundingRectangle
                if rect.width() > 0 and rect.height() > 0:
                    pyautogui.click(rect.left + rect.width() // 2, rect.top + rect.height() // 2)
                    clicked = True
    except Exception:
        pass

    if not clicked:
        pyautogui.hotkey("ctrl", "alt", "/")
        time.sleep(0.4)

        try:
            rect = win32gui.GetWindowRect(edge_hwnd)
            width = rect[2] - rect[0]
            height = rect[3] - rect[1]
            if width > 400 and height > 400:
                click_x = rect[0] + min(200, width // 4)
                click_y = rect[1] + min(180, height // 3)
                pyautogui.click(click_x, click_y)
                time.sleep(0.25)
        except Exception:
            pass

    # Clean the input field safely
    for _ in range(35):
        pyautogui.press("backspace")
    for _ in range(10):
        pyautogui.press("delete")
    time.sleep(0.1)

    # Type contact name
    _type_or_paste_safely(contact, interval=0.03)
    time.sleep(1.5)

    # Select contact and enter chat
    pyautogui.press("down")
    time.sleep(0.25)
    pyautogui.press("enter")
    time.sleep(1.5)

    # Validate if the contact chat actually opened
    scr_after_open = skill_read_screen()

    def verify_chat_open(scr_text: str, target_name: str) -> bool:
        target_name_lower = target_name.lower()
        if target_name_lower in scr_text.lower():
            return True
        words = [w.strip() for w in re.split(r'[^a-zA-Z0-9]', target_name) if len(w.strip()) >= 2]
        if not words:
            return False
        return any(w.lower() in scr_text.lower() for w in words)

    if not verify_chat_open(scr_after_open, contact):
        if "no chats" in scr_after_open.lower() or "no contacts" in scr_after_open.lower():
            return f"Failed to send WhatsApp message: Contact '{contact}' was not found in your chats."
        time.sleep(1.5)
        scr_after_open = skill_read_screen()
        if not verify_chat_open(scr_after_open, contact):
            return f"Failed to send WhatsApp message: Could not verify that chat with '{contact}' was opened."

    # Send message
    for _ in range(50):
        pyautogui.press("backspace")
    for _ in range(10):
        pyautogui.press("delete")
    time.sleep(0.1)

    _type_or_paste_safely(message, interval=0.02)
    time.sleep(0.15)
    pyautogui.press("enter")
    return f"Sent WhatsApp message to {contact}: '{message}'"


def skill_whatsapp_check_messages(args: str = "") -> str:
    """Checks WhatsApp Web for any new or unread messages using UI Automation screen reading."""
    import win32gui
    from .system import skill_read_screen

    # Find and focus WhatsApp tab/Edge window
    edge_hwnd = 0
    def _cb(h, _):
        nonlocal edge_hwnd
        t = win32gui.GetWindowText(h)
        if "whatsapp" in t.lower() or "edge" in t.lower():
            if win32gui.IsWindowVisible(h):
                edge_hwnd = h
    win32gui.EnumWindows(_cb, None)

    if edge_hwnd:
        try:
            from automation import force_foreground
            force_foreground(edge_hwnd)
        except Exception:
            try:
                win32gui.ShowWindow(edge_hwnd, 9)
                win32gui.SetForegroundWindow(edge_hwnd)
            except Exception:
                pass
        time.sleep(0.5)

    # Read screen content
    content = skill_read_screen()
    lines = content.split("\n")
    unread_updates = []
    for line in lines:
        if "unread" in line.lower() or "new message" in line.lower() or "notification" in line.lower():
            unread_updates.append(line)

    if unread_updates:
        return "Found unread updates on WhatsApp:\n" + "\n".join(unread_updates)
    else:
        recent_lines = [l for l in lines if len(l) > 3][:10]
        if recent_lines:
            return "Checked WhatsApp screen, here is the active view:\n" + "\n".join(recent_lines)
        return "No unread messages or active chats found on WhatsApp screen."
