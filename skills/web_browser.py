"""
skills/web_browser.py — Web search, URL navigation, smart open, YouTube search.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import time
from urllib import parse as urlparse, request as urlreq

from ._constants import _SITE_MAP
from ._utils import _type_or_paste_safely, _get_active_browser, _open_url_in_browser, _announce


def skill_web_search(args: str) -> str:
    """Search the web using DuckDuckGo (free, no API key)."""
    query = args.strip()
    if not query:
        return "No search query provided."

    # Try the new 'ddgs' package first, then legacy 'duckduckgo_search'
    ddgs_cls = None
    try:
        from ddgs import DDGS as _DDGS  # type: ignore
        ddgs_cls = _DDGS
    except ImportError:
        try:
            from duckduckgo_search import DDGS as _DDGS2  # type: ignore
            ddgs_cls = _DDGS2
        except ImportError:
            pass

    if ddgs_cls is not None:
        try:
            with ddgs_cls() as ddgs:
                results = list(ddgs.text(query, max_results=5))
            if not results:
                return _web_search_fallback(query)

            summary_parts = []
            for i, r in enumerate(results, 1):
                title = r.get("title", "")
                body = r.get("body", "")
                summary_parts.append(f"{i}. {title}: {body}")

            return "Here is what I found. " + " ".join(summary_parts)
        except Exception as exc:
            return _web_search_fallback(query)
    else:
        return _web_search_fallback(query)


def _web_search_fallback(query: str) -> str:
    """Minimal DuckDuckGo search without extra packages."""
    try:
        url = f"https://api.duckduckgo.com/?q={urlparse.quote(query)}&format=json&no_html=1"
        req = urlreq.Request(url, headers={"User-Agent": "FRIDAY/1.0"})
        with urlreq.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())

        abstract = data.get("AbstractText", "")
        answer = data.get("Answer", "")
        related = data.get("RelatedTopics", [])

        parts = []
        if answer:
            parts.append(answer)
        if abstract:
            parts.append(abstract)
        for topic in related[:3]:
            text = topic.get("Text", "")
            if text:
                parts.append(text)

        if parts:
            return "Here is what I found. " + " ".join(parts)
        return f"I could not find a clear answer for: {query}"
    except Exception as exc:
        return f"Web search failed: {exc}"


def skill_open_url(args: str) -> str:
    """Navigate the focused browser to a URL. Uses Ctrl+L to guarantee address bar focus."""
    import pyautogui
    url = args.strip()
    if not url:
        return "No URL provided."
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    try:
        pyautogui.hotkey("ctrl", "l")   # focus address bar, always
        time.sleep(0.2)
        pyautogui.hotkey("ctrl", "a")   # clear existing URL
        time.sleep(0.1)
        _type_or_paste_safely(url, interval=0.01)
        time.sleep(0.1)
        pyautogui.press("enter")
        return f"Navigated to {url}"
    except Exception as exc:
        return f"Could not navigate browser: {exc}"


def skill_open_url_in_existing_browser(url: str) -> str:
    """Open a URL in the existing browser window, or launch a new one if not running."""
    import win32gui
    import win32con
    import pyautogui

    # Find existing Edge window
    edge_hwnd = 0
    def _cb(h, _):
        nonlocal edge_hwnd
        t = win32gui.GetWindowText(h)
        if "edge" in t.lower() or "microsoft" in t.lower():
            if win32gui.IsWindowVisible(h):
                edge_hwnd = h
    win32gui.EnumWindows(_cb, None)

    domain_keyword = ""
    match = re.search(r'https?://(?:www\.)?([^./]+)', url)
    if match:
        domain_keyword = match.group(1).lower()

    if domain_keyword:
        # A. Check if the URL is already active/open in any window title
        target_hwnd = 0
        def _find_target_cb(h, _):
            nonlocal target_hwnd
            t = win32gui.GetWindowText(h).lower()
            if domain_keyword in t and win32gui.IsWindowVisible(h):
                target_hwnd = h
        win32gui.EnumWindows(_find_target_cb, None)

        if target_hwnd:
            try:
                from automation import force_foreground
                msg = "Sir, I'm already seeing that URL open, and should I use it like that? It might decrease the latency and saves time."
                _announce(msg)
                force_foreground(target_hwnd)
                time.sleep(1.2)
                return f"Focused existing {domain_keyword} tab in Edge."
            except Exception:
                pass

        # B. If Edge is open, try searching for the tab via Tab Search (Ctrl+Shift+A)
        if edge_hwnd:
            try:
                from automation import force_foreground
                force_foreground(edge_hwnd)
                time.sleep(0.3)

                pyautogui.hotkey("ctrl", "shift", "a")
                time.sleep(0.4)
                pyautogui.hotkey("ctrl", "a")
                time.sleep(0.1)
                pyautogui.press("delete")
                time.sleep(0.1)
                _type_or_paste_safely(domain_keyword, interval=0.02)
                time.sleep(0.4)
                pyautogui.press("enter")
                time.sleep(0.8)

                active_title = win32gui.GetWindowText(win32gui.GetForegroundWindow()).lower()
                if domain_keyword in active_title:
                    msg = "Sir, I'm already seeing that URL open, and should I use it like that? It might decrease the latency and saves time."
                    _announce(msg)
                    time.sleep(1.0)
                    return f"Focused existing {domain_keyword} tab in Edge."
            except Exception:
                pass

    if edge_hwnd:
        # Reuse existing Edge — open new tab and navigate
        try:
            from automation import force_foreground
            force_foreground(edge_hwnd)
        except Exception:
            try:
                win32gui.ShowWindow(edge_hwnd, win32con.SW_RESTORE)
                win32gui.SetForegroundWindow(edge_hwnd)
            except Exception:
                pass
        time.sleep(0.2)
        pyautogui.hotkey("ctrl", "t")   # new tab
        time.sleep(0.3)
    else:
        # No Edge open — launch it
        try:
            subprocess.Popen(["msedge.exe"])
            time.sleep(1.5)
        except Exception:
            import webbrowser
            webbrowser.open(url)
            return f"Opened {url} in default browser."

    # Navigate
    pyautogui.hotkey("ctrl", "l")
    time.sleep(0.2)
    pyautogui.hotkey("ctrl", "a")
    time.sleep(0.1)
    _type_or_paste_safely(url, interval=0.01)
    time.sleep(0.1)
    pyautogui.press("enter")
    return f"Opened {url} in active browser."


def skill_smart_open(args: str) -> str:
    """
    Intelligently open a website or URL in the currently active browser.
    Knows common sites by name (youtube, github, gmail, reddit, etc.).
    Detects the running browser first — avoids duplicate windows.
    args: site name or full URL
    """
    target = args.strip().lower().strip('"\'')
    if not target:
        return "No site or URL provided."

    # Resolve friendly name to URL
    url = _SITE_MAP.get(target)
    if url is None:
        # Try partial match
        for key, val in _SITE_MAP.items():
            if key in target or target in key:
                url = val
                break
    if url is None:
        # Treat as raw URL
        url = target if target.startswith(("http://", "https://")) else "https://" + target

    # Detect running browser first — opens as new tab, no duplicate window
    active_browser = _get_active_browser()
    browser_exe = _open_url_in_browser(url, browser_exe=active_browser)
    browser_label = os.path.basename(browser_exe).replace('.exe', '').replace('.', '').title()
    if browser_label.lower() in ("default browser", "default", ""):
        browser_label = "browser"
    site_label = target.title()
    return f"Opening {site_label} in {browser_label}."


def skill_browser_search(args: str) -> str:
    """
    Search something in the browser using the default search engine.
    args: search query
    """
    query = args.strip()
    if not query:
        return "No search query provided."
    try:
        import webbrowser
        url = "https://www.google.com/search?q=" + urlparse.quote_plus(query)
        webbrowser.open(url)
        return f"Searching for '{query}' in browser."
    except Exception as exc:
        return f"Could not open browser: {exc}"


def skill_youtube_search(args: str) -> str:
    """
    Search YouTube for a query, opening in the active browser.
    Tries to open the first video directly; falls back to the results page.
    args: search query (e.g. 'lofi music', 'python tutorial')
    """
    query = args.strip()
    if not query:
        return "No search query provided."

    results_url = "https://www.youtube.com/results?search_query=" + urlparse.quote_plus(query)

    # Try to fetch the first video URL from the results page
    video_url = None
    try:
        req = urlreq.Request(results_url, headers={"User-Agent": "Mozilla/5.0"})
        with urlreq.urlopen(req, timeout=8) as resp:
            html = resp.read().decode("utf-8", errors="replace")
        # Extract first video ID from the results page HTML
        vid_match = re.search(r'/watch\?v=([a-zA-Z0-9_-]{11})', html)
        if vid_match:
            video_url = f"https://www.youtube.com/watch?v={vid_match.group(1)}"
    except Exception:
        pass  # fall back to results page

    url_to_open = video_url or results_url
    browser = _open_url_in_browser(url_to_open)
    browser_name = os.path.basename(browser).replace(".exe", "").title()
    if video_url:
        return f"Playing top result for '{query}' in {browser_name}."
    return f"Searching YouTube for '{query}' in {browser_name}."


def skill_summarize_url(args: str) -> str:
    """Fetch website text and summarize it."""
    import urllib.request
    url = args.strip()
    if not url:
        return "No URL provided."
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read().decode("utf-8", errors="ignore")

        text = re.sub(r"<(script|style).*?>.*?</\1>", "", html, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<.*?>", "", text)
        text = re.sub(r"\s+", " ", text).strip()

        text = text[:4000]
        if not text:
            return "No readable text found on the page."
        return f"Fetched text from {url}:\n{text[:1000]}..."
    except Exception as exc:
        return f"Failed to fetch page content: {exc}"
