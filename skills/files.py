"""
skills/files.py — File search, read, write, edit, open, rename, move, find-and-open.
"""
from __future__ import annotations

import os
import time

from ._constants import _BLOCKED_WRITE_DIRS, _SEARCH_ROOTS, _SKIP_DIRS
from ._utils import _truncate


def skill_file_search(args: str) -> str:
    """Search for files by name pattern on common locations."""
    pattern = args.strip().lower()
    if not pattern:
        return "Specify a filename or pattern to search for."

    search_dirs = [
        os.path.expanduser("~\\Desktop"),
        os.path.expanduser("~\\Documents"),
        os.path.expanduser("~\\Downloads"),
    ]

    found = []
    for root_dir in search_dirs:
        if not os.path.isdir(root_dir):
            continue
        try:
            for dirpath, dirnames, filenames in os.walk(root_dir):
                # Limit depth to 3 levels
                depth = dirpath.replace(root_dir, "").count(os.sep)
                if depth > 3:
                    dirnames.clear()
                    continue
                for fn in filenames:
                    if pattern in fn.lower():
                        found.append(os.path.join(dirpath, fn))
                        if len(found) >= 10:
                            break
                if len(found) >= 10:
                    break
        except PermissionError:
            continue

    if not found:
        return f"No files matching '{pattern}' found in Desktop, Documents, or Downloads."

    file_list = ", ".join(os.path.basename(f) for f in found[:5])
    return f"Found {len(found)} file{'s' if len(found) > 1 else ''}: {file_list}."


def skill_open_file(args: str) -> str:
    """Open a file using the operating system's default handler."""
    path = args.strip().strip('"\'')
    if not os.path.exists(path):
        return f"File does not exist: {path}"
    try:
        os.startfile(path)
        return f"Opened file: {path}"
    except Exception as exc:
        return f"Failed to open file: {exc}"


def skill_search_file(args: str) -> str:
    """Search for files in a directory using a glob pattern. Args: 'directory||pattern'."""
    import glob
    parts = args.split("||", 1)
    if len(parts) == 2:
        directory, pattern = parts[0].strip().strip('"\''), parts[1].strip().strip('"\'')
    else:
        directory = os.path.expanduser("~\\Documents")
        pattern = parts[0].strip().strip('"\'')

    if not os.path.exists(directory):
        return f"Directory does not exist: {directory}"

    try:
        search_path = os.path.join(directory, "**", pattern)
        matches = glob.glob(search_path, recursive=True)
        if not matches:
            return f"No matches found for '{pattern}' in '{directory}'."
        return f"Found matches:\n" + "\n".join(matches[:15])
    except Exception as exc:
        return f"Search failed: {exc}"


def skill_rename_file(args: str) -> str:
    """Rename a file or folder. Args: 'old_path||new_path'."""
    parts = args.split("||", 1)
    if len(parts) != 2:
        return "Arguments must be format: 'old_path||new_path'"
    old_path = parts[0].strip().strip('"\'')
    new_path = parts[1].strip().strip('"\'')

    if not os.path.exists(old_path):
        return f"Source path does not exist: {old_path}"
    try:
        os.rename(old_path, new_path)
        return f"Renamed to: {new_path}"
    except Exception as exc:
        return f"Rename failed: {exc}"


def skill_move_file(args: str) -> str:
    """Move a file or folder to a new location. Args: 'src_path||dst_dir'."""
    import shutil
    parts = args.split("||", 1)
    if len(parts) != 2:
        return "Arguments must be format: 'src_path||dst_dir'"
    src_path = parts[0].strip().strip('"\'')
    dst_dir = parts[1].strip().strip('"\'')

    if not os.path.exists(src_path):
        return f"Source path does not exist: {src_path}"
    try:
        shutil.move(src_path, dst_dir)
        return f"Moved to: {dst_dir}"
    except Exception as exc:
        return f"Move failed: {exc}"


def skill_find_and_open(args: str) -> str:
    """
    Find a file by name across common directories, then open it.
    args: filename or partial name (e.g. 'resume.pdf', 'budget')
    Searches Desktop, Documents, Downloads, then the full user profile.
    """
    query = args.strip().strip('"\'').lower()
    if not query:
        return "No filename provided."

    found: list[str] = []
    _search_deadline = time.monotonic() + 5.0  # 5s hard timeout

    for root in _SEARCH_ROOTS:
        if not os.path.exists(root):
            continue
        try:
            for dirpath, dirnames, filenames in os.walk(root):
                if time.monotonic() > _search_deadline:
                    break  # 5s hard timeout
                # Prune skip dirs in-place so os.walk doesn't descend into them
                dirnames[:] = [
                    d for d in dirnames
                    if d not in _SKIP_DIRS and not d.startswith(".")
                ]
                for fname in filenames:
                    if time.monotonic() > _search_deadline:
                        break
                    if query in fname.lower():
                        found.append(os.path.join(dirpath, fname))
                if len(found) >= 10 or time.monotonic() > _search_deadline:
                    break   # stop at 10 matches or timeout
        except PermissionError:
            continue
        if found:
            break   # found in first matching root — stop searching deeper

    if not found:
        return f"No file matching '{args.strip()}' found in your common folders."

    # Open the best match (first found)
    best = found[0]
    try:
        os.startfile(best)   # Windows: opens with default associated app
        extra = f" ({len(found)-1} more match{'es' if len(found)-1 != 1 else ''} found)" if len(found) > 1 else ""
        return f"Opening {os.path.basename(best)}{extra}."
    except Exception as exc:
        return f"Found {os.path.basename(best)} but couldn't open it: {exc}"


def skill_file_read(args: str) -> str:
    """
    Read a file and return its first 200 lines.
    args: file path (absolute or relative to user home)
    """
    path = args.strip().strip('"\'')
    if not path:
        return "No file path provided."

    # Expand ~ and env vars
    path = os.path.expandvars(os.path.expanduser(path))

    if not os.path.exists(path):
        return f"File not found: {path}"
    if os.path.isdir(path):
        items = os.listdir(path)[:20]
        return f"That's a directory. Contents: {', '.join(items)}"
    if not os.access(path, os.R_OK):
        return f"Permission denied: {path}"

    try:
        size_kb = os.path.getsize(path) / 1024
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        total = len(lines)
        preview = "".join(lines[:200])
        suffix = f"\n[{total} lines total, {size_kb:.1f} KB]" if total > 200 else f"\n[{total} lines, {size_kb:.1f} KB]"
        return _truncate(preview + suffix)
    except Exception as exc:
        return f"Error reading file: {exc}"


def skill_file_write(args: str) -> str:
    """
    Write content to a file.
    args: path||content   (pipe-delimited)
    Blocked: system directories (C:\\Windows, /etc, /usr, etc.)
    """
    if "||" not in args:
        return "Format: file_write:path||content"
    path, content = args.split("||", 1)
    path = os.path.expandvars(os.path.expanduser(path.strip().strip('"\'')))
    abs_path = os.path.abspath(path)

    # Security: block system directories
    for blocked in _BLOCKED_WRITE_DIRS:
        try:
            blocked_abs = os.path.abspath(blocked)
            if abs_path.startswith(blocked_abs):
                return f"Refused: writing to {blocked} is not allowed."
        except Exception:
            pass

    try:
        os.makedirs(os.path.dirname(abs_path) or ".", exist_ok=True)
        with open(abs_path, "w", encoding="utf-8") as f:
            f.write(content)
        lines_written = content.count("\n") + 1
        return f"Written {lines_written} line(s) to {abs_path}."
    except Exception as exc:
        return f"Error writing file: {exc}"


def skill_file_edit(args: str) -> str:
    """
    Surgical find-and-replace in a file.
    args: path||old_text||new_text
    Replaces the FIRST occurrence of old_text with new_text.
    Blocked: system directories (same as file_write).
    """
    parts = args.split("||", 2)
    if len(parts) != 3:
        return "Format: file_edit:path||old_text||new_text"
    path, old_text, new_text = parts
    path = os.path.expandvars(os.path.expanduser(path.strip().strip('"\'' )))
    abs_path = os.path.abspath(path)

    # Security: block system directories
    for blocked in _BLOCKED_WRITE_DIRS:
        try:
            blocked_abs = os.path.abspath(blocked)
            if abs_path.startswith(blocked_abs):
                return f"Refused: editing {blocked} is not allowed."
        except Exception:
            pass

    if not os.path.exists(abs_path):
        return f"File not found: {abs_path}"

    try:
        with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        if old_text not in content:
            return f"Text not found in {os.path.basename(abs_path)}. No changes made."

        new_content = content.replace(old_text, new_text, 1)

        with open(abs_path, "w", encoding="utf-8") as f:
            f.write(new_content)

        return (
            f"Edited {os.path.basename(abs_path)}: replaced "
            f"{len(old_text)} chars with {len(new_text)} chars."
        )
    except Exception as exc:
        return f"Edit failed: {exc}"
