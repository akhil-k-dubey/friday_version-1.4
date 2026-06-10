"""
skills/memory_skills.py — Remember, recall, and memory explanation skills.
"""
from __future__ import annotations

import json
import os
import time


def skill_remember(args: str) -> str:
    """Save a note or fact to long-term memory. Format: 'key||value' or 'text'."""
    parts = args.split("||", 1)
    if len(parts) == 2:
        k, v = parts[0].strip(), parts[1].strip()
    else:
        k = "note_" + str(int(time.time()))
        v = parts[0].strip()

    path = os.path.join(os.path.expanduser("~"), ".friday", "memory.json")
    try:
        data = {}
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        notes = data.setdefault("notes", {})
        notes[k.lower()] = v
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return f"Remembered: {k} -> {v}"
    except Exception as exc:
        return f"Failed to remember: {exc}"


def skill_recall(args: str) -> str:
    """Recall a note or fact from long-term memory or session history by keyword/semantic search."""
    from memory import PersistentMemory

    query = args.strip().lower()
    path = os.path.join(os.path.expanduser("~"), ".friday", "memory.json")

    note_matches = []
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            notes = data.get("notes", {})
            if query:
                for k, v in notes.items():
                    if query in k or query in v.lower():
                        note_matches.append(f"Note - {k}: {v}")
            else:
                if notes:
                    note_matches.extend(f"Note - {k}: {v}" for k, v in notes.items())
        except Exception:
            pass

    # Dynamic semantic vector search over transcript logs
    semantic_matches = []
    if query:
        try:
            pm = PersistentMemory()
            matches = pm.semantic_search(query, limit=3)
            for m in matches:
                ts = m.get("timestamp", "")[:16].replace("T", " ")
                semantic_matches.append(f"[{ts}] User: {m.get('user', '')} -> Friday: {m.get('assistant', '')}")
        except Exception:
            pass

    # Combine results
    result_parts = []
    if note_matches:
        result_parts.append("Stored Notes:\n" + "\n".join(note_matches))
    if semantic_matches:
        result_parts.append("Semantic Session History Matches:\n" + "\n".join(semantic_matches))

    if result_parts:
        return "\n\n".join(result_parts)

    return f"No notes or session history matching '{query}' found."


def skill_memory_explain(args: str = "") -> str:
    """Explain Friday's memory architecture (short-term + long-term semantic) and demonstrate semantic recall."""
    from memory import PersistentMemory
    pm = PersistentMemory()

    explanation = (
        "I possess both short-term and long-term memory. "
        "My short-term memory maintains active conversation context in a rolling buffer. "
        "My long-term memory utilizes a lightweight local vector-based semantic search "
        "over our historical session transcripts, allowing me to recall past sessions "
        "without needing heavy external databases."
    )

    demo_query = "remember"
    try:
        matches = pm.semantic_search(demo_query, limit=2)
        if matches:
            recalled = []
            for m in matches:
                ts = m.get("timestamp", "")[:16].replace("T", " ")
                recalled.append(f"[{ts}] User: '{m.get('user', '')}' -> Friday: '{m.get('assistant', '')}'")
            explanation += "\n\nTo demonstrate my long-term memory, here is what I recalled semantically from our past sessions:\n" + "\n".join(recalled)
        else:
            facts_summary = pm.get_context_summary()
            if facts_summary:
                explanation += f"\n\nCurrently, I remember these facts about you: {facts_summary}"
            else:
                explanation += "\n\nI haven't recorded any persistent notes or long-term session logs yet."
    except Exception as e:
        explanation += f"\n\n(Memory search demo encountered an issue: {e})"

    return explanation
