"""
skills/volume.py — System volume control via Windows Core Audio COM API.
"""
from __future__ import annotations

import re
import subprocess


def _set_mute_explicit(mute: bool) -> str:
    """Explicitly set mute on/off via Windows Core Audio COM API.

    Uses IAudioEndpointVolume.SetMute(bool) instead of the VK_VOLUME_MUTE
    toggle key, so 'mute' always mutes and 'unmute' always unmutes
    regardless of the current state.
    Falls back to the toggle key if COM interop fails.
    """
    mute_ps = "$true" if mute else "$false"
    # PowerShell inline C# — defines the minimum Core Audio COM interfaces
    # needed to call SetMute() on the default audio endpoint.
    ps_script = (
        "Add-Type @'\n"
        "using System; using System.Runtime.InteropServices;\n"
        '[Guid("5CDF2C82-841E-4546-9722-0CF74078229A"), '
        "InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]\n"
        "interface IAudioEndpointVolume {\n"
        "  int _0(); int _1(); int _2(); int _3(); int _4();\n"
        "  int SetMasterVolumeLevelScalar(float f, Guid g);\n"
        "  int GetMasterVolumeLevelScalar(out float f);\n"
        "  int _7(); int _8(); int _9(); int _10();\n"
        "  int SetMute([MarshalAs(UnmanagedType.Bool)] bool b, Guid g);\n"
        "  int GetMute(out bool b);\n"
        "}\n"
        '[Guid("D666063F-1587-4E43-81F1-B948E807363F"), '
        "InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]\n"
        "interface IMMDevice {\n"
        "  int Activate(ref Guid iid, int c, IntPtr p, "
        "[MarshalAs(UnmanagedType.IUnknown)] out object o);\n"
        "}\n"
        '[Guid("A95664D2-9614-4F35-A746-DE8DB63617E6"), '
        "InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]\n"
        "interface IMMDeviceEnumerator {\n"
        "  int GetDefaultAudioEndpoint(int d, int r, out IMMDevice dev);\n"
        "}\n"
        '[ComImport, Guid("BCDE0395-E52F-467C-8E3D-C4579291692E")] '
        "class MMDeviceEnumerator {}\n"
        "'@\n"
        "$e = New-Object MMDeviceEnumerator; $d = $null\n"
        "$e.GetDefaultAudioEndpoint(0, 1, [ref]$d)\n"
        "$iid = [Guid]'5CDF2C82-841E-4546-9722-0CF74078229A'\n"
        "$o = $null; $d.Activate([ref]$iid, 1, [IntPtr]::Zero, [ref]$o)\n"
        f"([IAudioEndpointVolume]$o).SetMute({mute_ps}, [Guid]::Empty)\n"
    )
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_script],
            capture_output=True, text=True, timeout=5,
        )
        if r.returncode == 0:
            return "Volume muted." if mute else "Volume unmuted."
    except Exception:
        pass
    # Fallback: toggle key (may not match desired state)
    try:
        subprocess.run(
            ["powershell", "-Command",
             "(New-Object -ComObject WScript.Shell).SendKeys([char]173)"],
            timeout=5, capture_output=True,
        )
    except Exception:
        pass
    return "Volume muted." if mute else "Volume unmuted."


def _set_volume_scalar(level: float) -> str:
    """Set master volume level using Windows Core Audio COM API.
    level is a float between 0.0 and 1.0.
    """
    ps_script = (
        "Add-Type @'\n"
        "using System; using System.Runtime.InteropServices;\n"
        '[Guid("5CDF2C82-841E-4546-9722-0CF74078229A"), '
        "InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]\n"
        "interface IAudioEndpointVolume {\n"
        "  int _0(); int _1(); int _2(); int _3(); int _4();\n"
        "  int SetMasterVolumeLevelScalar(float f, Guid g);\n"
        "  int GetMasterVolumeLevelScalar(out float f);\n"
        "  int _7(); int _8(); int _9(); int _10();\n"
        "  int SetMute([MarshalAs(UnmanagedType.Bool)] bool b, Guid g);\n"
        "  int GetMute(out bool b);\n"
        "}\n"
        '[Guid("D666063F-1587-4E43-81F1-B948E807363F"), '
        "InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]\n"
        "interface IMMDevice {\n"
        "  int Activate(ref Guid iid, int c, IntPtr p, "
        "[MarshalAs(UnmanagedType.IUnknown)] out object o);\n"
        "}\n"
        '[Guid("A95664D2-9614-4F35-A746-DE8DB63617E6"), '
        "InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]\n"
        "interface IMMDeviceEnumerator {\n"
        "  int GetDefaultAudioEndpoint(int d, int r, out IMMDevice dev);\n"
        "}\n"
        '[ComImport, Guid("BCDE0395-E52F-467C-8E3D-C4579291692E")] '
        "class MMDeviceEnumerator {}\n"
        "'@\n"
        "$e = New-Object MMDeviceEnumerator; $d = $null\n"
        "$e.GetDefaultAudioEndpoint(0, 1, [ref]$d)\n"
        "$iid = [Guid]'5CDF2C82-841E-4546-9722-0CF74078229A'\n"
        "$o = $null; $d.Activate([ref]$iid, 1, [IntPtr]::Zero, [ref]$o)\n"
        f"([IAudioEndpointVolume]$o).SetMasterVolumeLevelScalar({level:.4f}, [Guid]::Empty)\n"
    )
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_script],
            capture_output=True, text=True, timeout=5,
        )
        if r.returncode == 0:
            return f"Volume set to {int(level * 100)}%."
    except Exception:
        pass
    return "Failed to set volume."


def skill_volume(args: str) -> str:
    """Control system volume using PowerShell/nircmd."""
    action = args.strip().lower()
    if not action:
        return "Specify: mute, unmute, up, down, or a number 0-100."

    # Strip prefixes like "volume " or "volume:" or trailing "%"
    action = re.sub(r"^(?:volume\s*[:\s]*|set\s+volume\s+(?:to\s+)?|turn\s+volume\s+(?:to\s+)?)", "", action)
    action = action.rstrip("%")

    # Spoken/string aliases
    aliases = {
        "max": 100,
        "maximum": 100,
        "full": 100,
        "high": 80,
        "medium": 50,
        "half": 50,
        "low": 20,
        "min": 0,
        "minimum": 0,
        "zero": 0,
        "off": 0,
    }

    if action in aliases:
        target_pct = aliases[action]
        return _set_volume_scalar(target_pct / 100.0)

    # Check if numeric digit exists
    digits = re.findall(r"\d+", action)
    if digits:
        try:
            val = int(digits[0])
            if 0 <= val <= 100:
                return _set_volume_scalar(val / 100.0)
        except ValueError:
            pass

    try:
        if action == "mute":
            return _set_mute_explicit(True)
        elif action == "unmute":
            return _set_mute_explicit(False)
        elif action in ("up", "louder"):
            for _ in range(5):
                subprocess.run(
                    ["powershell", "-Command",
                     "(New-Object -ComObject WScript.Shell).SendKeys([char]175)"],
                    timeout=5, capture_output=True,
                )
            return "Volume increased."
        elif action in ("down", "quieter", "lower"):
            for _ in range(5):
                subprocess.run(
                    ["powershell", "-Command",
                     "(New-Object -ComObject WScript.Shell).SendKeys([char]174)"],
                    timeout=5, capture_output=True,
                )
            return "Volume decreased."
        else:
            return f"Unknown volume command: {action}. Use mute, unmute, up, down, or a number 0-100."
    except Exception as exc:
        return f"Volume control failed: {exc}"
