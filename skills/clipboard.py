"""
skills/clipboard.py — Clipboard read/write and history ring.
"""
from __future__ import annotations

import subprocess
import threading
import time


def skill_clipboard_read(args: str) -> str:
    """Read current clipboard contents."""
    try:
        import pyperclip
        try:
            content = pyperclip.paste()
        except Exception as e:
            raise ImportError(f"pyperclip locked: {e}")
        if content:
            # Truncate for voice
            if len(content) > 300:
                return f"Clipboard contains: {content[:300]}... (truncated)"
            return f"Clipboard contains: {content}"
        return "Clipboard is empty."
    except ImportError:
        # PowerShell fallback
        try:
            result = subprocess.run(
                ["powershell", "-Command", "Get-Clipboard"],
                capture_output=True, text=True, timeout=5,
            )
            content = result.stdout.strip()
            if content:
                if len(content) > 300:
                    return f"Clipboard contains: {content[:300]}... (truncated)"
                return f"Clipboard contains: {content}"
            return "Clipboard is empty."
        except Exception:
            return "Could not read clipboard."


def skill_clipboard_write(args: str) -> str:
    """Write text to clipboard."""
    text = args.strip()
    if not text:
        return "No text to copy."
    try:
        import pyperclip
        try:
            pyperclip.copy(text)
        except Exception as e:
            raise ImportError(f"pyperclip locked: {e}")
        return "Copied to clipboard."
    except ImportError:
        try:
            # Escape single quotes in powershell
            escaped = text.replace("'", "''")
            subprocess.run(
                ["powershell", "-Command", f"Set-Clipboard '{escaped}'"],
                timeout=5,
            )
            return "Copied to clipboard."
        except Exception:
            return "Could not write to clipboard."


class ClipboardRing:
    def __init__(self, max_size: int = 10):
        self.ring = []
        self.max_size = max_size
        self._last_copied = ""
        self._lock = threading.Lock()
        self._running = True
        self._thread = None

    def start(self):
        self._thread = threading.Thread(target=self._loop, daemon=True, name="clipboard-ring")
        self._thread.start()

    def check_clipboard(self):
        import pyperclip
        try:
            current = pyperclip.paste()
            if current and current != self._last_copied:
                with self._lock:
                    if current in self.ring:
                        self.ring.remove(current)
                    self.ring.append(current)
                    if len(self.ring) > self.max_size:
                        self.ring.pop(0)
                    self._last_copied = current
        except Exception:
            pass

    def _loop(self):
        while self._running:
            self.check_clipboard()
            time.sleep(1.0)

    def get_history(self) -> list:
        with self._lock:
            return list(self.ring)

    def get_previous(self) -> str:
        with self._lock:
            if len(self.ring) >= 2:
                return self.ring[-2]
            return ""


# Initialize and start the global clipboard ring
clipboard_ring = ClipboardRing()
clipboard_ring.start()


def skill_clipboard_history(args: str = "") -> str:
    """List the current clipboard history ring items."""
    history = clipboard_ring.get_history()
    if not history:
        return "Clipboard history ring is empty."
    return "Clipboard History Ring (newest last):\n" + "\n".join(f"{i+1}: {item[:80]}..." for i, item in enumerate(history))


def skill_clipboard_paste_previous(args: str = "") -> str:
    """Set the clipboard to the item copied before the current one."""
    import pyperclip
    prev = clipboard_ring.get_previous()
    if not prev:
        return "No previous clipboard item available in the history ring."
    try:
        pyperclip.copy(prev)
        return f"Restored previous item to clipboard: {prev[:80]}..."
    except Exception as exc:
        return f"Failed to restore clipboard: {exc}"
