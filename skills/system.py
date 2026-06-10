"""
skills/system.py — System info, diagnostics, screenshot, and screen reading.
"""
from __future__ import annotations

import datetime
import os
import platform
import subprocess
import threading

from ._utils import _collect_text


def skill_system_info(args: str) -> str:
    """Get system information: CPU, RAM, disk, battery."""
    try:
        import psutil
    except ImportError:
        return _system_info_basic()

    parts = []
    cpu_pct = psutil.cpu_percent(interval=0.5)
    parts.append(f"CPU usage is {cpu_pct} percent")

    mem = psutil.virtual_memory()
    used_gb = mem.used / (1024 ** 3)
    total_gb = mem.total / (1024 ** 3)
    parts.append(f"RAM: {used_gb:.1f} of {total_gb:.1f} GB used ({mem.percent} percent)")

    disk = psutil.disk_usage("C:\\")
    free_gb = disk.free / (1024 ** 3)
    parts.append(f"C drive: {free_gb:.0f} GB free")

    bat = psutil.sensors_battery()
    if bat:
        plug = "plugged in" if bat.power_plugged else "on battery"
        parts.append(f"Battery: {bat.percent} percent, {plug}")

    # GPU / VRAM via nvidia-smi (graceful fallback if unavailable)
    try:
        nv = subprocess.run(
            ["nvidia-smi",
             "--query-gpu=name,memory.used,memory.total,utilization.gpu",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5,
        )
        if nv.returncode == 0 and nv.stdout.strip():
            gpu_line = nv.stdout.strip().split("\n")[0]
            gpu_parts = [p.strip() for p in gpu_line.split(",")]
            if len(gpu_parts) >= 4:
                parts.append(
                    f"GPU: {gpu_parts[0]}, VRAM {gpu_parts[1]} of "
                    f"{gpu_parts[2]} MB used, utilization {gpu_parts[3]} percent"
                )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass  # nvidia-smi not installed or failed — skip GPU info

    return ". ".join(parts) + "."


def _system_info_basic() -> str:
    """Fallback system info without psutil."""
    info = platform.uname()
    return (
        f"System: {info.system} {info.release}, "
        f"Machine: {info.machine}, "
        f"Processor: {info.processor}."
    )


def skill_system_diagnostics(args: str = "") -> str:
    """Check system health, including CPU, RAM, Disk, Battery, and GPU usage."""
    import psutil
    import shutil

    try:
        cpu = psutil.cpu_percent(interval=0.1)
        ram = psutil.virtual_memory()
        disk = shutil.disk_usage("C:\\")

        battery_str = "N/A"
        if hasattr(psutil, "sensors_battery"):
            bat = psutil.sensors_battery()
            if bat:
                battery_str = f"{bat.percent}% ({'Plugged In' if bat.power_plugged else 'Discharging'})"

        gpu_str = "N/A"
        try:
            res = subprocess.run(["nvidia-smi", "--query-gpu=utilization.gpu,temperature.gpu", "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=1)
            if res.returncode == 0:
                parts = res.stdout.strip().split(",")
                if len(parts) == 2:
                    gpu_str = f"{parts[0]}% Utilization, Temp: {parts[1]}°C"
        except Exception:
            pass

        return (
            f"System Diagnostics:\n"
            f"- CPU: {cpu}%\n"
            f"- RAM: {ram.percent}% (Used: {ram.used // (1024**2)}MB, Free: {ram.available // (1024**2)}MB)\n"
            f"- Disk C:: {disk.used // (1024**3)}GB / {disk.total // (1024**3)}GB used ({100 - int(disk.free/disk.total*100)}%)\n"
            f"- Battery: {battery_str}\n"
            f"- GPU: {gpu_str}"
        )
    except Exception as exc:
        return f"Diagnostics failed: {exc}"


def skill_screenshot(args: str) -> str:
    """Take a screenshot and save it to Desktop."""
    try:
        from PIL import ImageGrab
    except ImportError:
        # Fallback: use PowerShell/Snipping Tool
        try:
            subprocess.Popen(["snippingtool", "/clip"], shell=True)
            return "Opened Snipping Tool for screenshot."
        except Exception:
            return "Screenshot requires Pillow: pip install Pillow"

    try:
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(desktop, f"screenshot_{ts}.png")
        img = ImageGrab.grab()
        img.save(path)
        return f"Screenshot saved to Desktop as screenshot_{ts}.png."
    except Exception as exc:
        return f"Screenshot failed: {exc}"


def skill_read_screen(args: str = "") -> str:
    """Reads visible text content from the currently focused window
    using Windows UI Automation. No GPU, no screenshot needed.
    """
    import uiautomation as auto
    import win32gui

    try:
        hwnd = win32gui.GetForegroundWindow()
        if not hwnd:
            return "No focused window active."
        title = win32gui.GetWindowText(hwnd)
        ctrl = auto.ControlFromHandle(hwnd)
        if not ctrl:
            return f"Could not read screen: Unable to bind to '{title}'."

        texts = []
        # Walk descendant nodes on a separate thread to handle heavy layouts and enforce timeout
        def _worker():
            try:
                for c in ctrl.GetChildren():
                    _collect_text(c, texts, depth=0, max_depth=4)
            except Exception:
                pass

        t = threading.Thread(target=_worker)
        t.daemon = True
        t.start()
        t.join(timeout=0.15)  # 150ms strict hardware-friendly watchdog timeout

        # Clean duplicates and empty spaces
        seen = set()
        unique_texts = []
        for text in texts:
            cleaned = text.strip()
            if cleaned and cleaned not in seen:
                seen.add(cleaned)
                unique_texts.append(cleaned)

        combined = "\n".join(unique_texts)
        if not combined:
            return f"No readable text found in '{title}'."
        # Truncate to avoid overwhelming LLM context
        if len(combined) > 2000:
            combined = combined[:2000] + "\n... (truncated)"
        return f"Screen content from '{title}':\n{combined}"
    except Exception as e:
        return f"Could not read screen: {e}"
