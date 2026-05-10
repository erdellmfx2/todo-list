#!/usr/bin/env python3
import json
import secrets
import subprocess
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
TASKS_FILE = ROOT / "tasks.json"
SYNC_SCRIPT = ROOT / "scripts" / "sync_repo.sh"
TZ_NAME = "America/New_York"
LOCAL_TZ = ZoneInfo(TZ_NAME)


def current_time():
    return datetime.now(LOCAL_TZ)


def normalize_title(value):
    return " ".join((value or "").strip().lower().split())


def load_data():
    if not TASKS_FILE.exists():
        return {
            "version": "1.0",
            "description": "Task list with active tasks first and completed tasks below",
            "updated_at": current_time().isoformat(),
            "tasks": {"active": [], "completed": []},
        }
    with open(TASKS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_data(data):
    data["updated_at"] = current_time().isoformat()
    with open(TASKS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    auto_sync_repo()


def auto_sync_repo():
    if not SYNC_SCRIPT.exists():
        return
    try:
        subprocess.run([str(SYNC_SCRIPT)], cwd=ROOT, check=True)
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"Auto-sync failed: {exc}") from exc


def generate_task_id():
    return secrets.token_hex(4)


def ensure_history(task):
    history = task.get("history")
    if not isinstance(history, list):
        history = []
        task["history"] = history
    return history


def add_history(task, action, notes, by="hermes"):
    ensure_history(task).append(
        {
            "action": action,
            "by": by,
            "at": current_time().isoformat(),
            "notes": notes,
        }
    )


def append_metadata(task, note):
    existing = task.get("task_metadata", "")
    ts = current_time().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{ts}] {note}".strip()
    if existing:
        task["task_metadata"] = existing.rstrip() + "\n" + entry
    else:
        task["task_metadata"] = entry


def new_task(title, due="none", priority="Medium", metadata="", by="hermes"):
    task = {
        "id": generate_task_id(),
        "title": title.strip(),
        "status": "Active",
        "date_due": due,
        "priority": priority,
        "task_metadata": metadata.strip(),
    }
    add_history(task, "create", "Created via Hermes task workflow", by=by)
    return task


def find_task(active_list, completed_list, title):
    target = normalize_title(title)
    for t in active_list:
        if normalize_title(t.get("title")) == target:
            return "active", t
    for t in completed_list:
        if normalize_title(t.get("title")) == target:
            return "completed", t
    return None, None


def find_task_candidates(active_list, completed_list, query, include_completed=True, limit=5):
    needle = normalize_title(query)
    scored = []
    for bucket_name, tasks in (("active", active_list), ("completed", completed_list)):
        if bucket_name == "completed" and not include_completed:
            continue
        for task in tasks:
            title = task.get("title", "")
            normalized = normalize_title(title)
            if not normalized:
                continue
            if normalized == needle:
                score = 10.0
            elif needle and needle in normalized:
                score = 5.0 + (len(needle) / max(len(normalized), 1))
            else:
                score = SequenceMatcher(None, needle, normalized).ratio()
            scored.append((score, bucket_name, task))

    scored.sort(key=lambda item: (-item[0], item[2].get("title", "").lower()))
    return scored[:limit]


def resolve_task(active_list, completed_list, query, include_completed=True):
    candidates = find_task_candidates(active_list, completed_list, query, include_completed=include_completed, limit=5)
    if not candidates:
        return None, []

    top_score = candidates[0][0]
    top = [item for item in candidates if abs(item[0] - top_score) < 1e-9]

    if top_score >= 10.0 and len(top) == 1:
        _, bucket, task = top[0]
        return (bucket, task), candidates

    if top_score >= 5.0 and len(top) == 1:
        _, bucket, task = top[0]
        return (bucket, task), candidates

    return None, candidates


def mark_complete(task, note="Marked complete", by="hermes"):
    task["status"] = "Complete"
    completed_at = current_time().isoformat()
    task["completed_at"] = completed_at
    task["date_completed"] = completed_at
    append_metadata(task, note)
    add_history(task, "complete", note, by=by)


def reopen_task(task, note="Reopened task", by="hermes"):
    task["status"] = "Active"
    task.pop("completed_at", None)
    task.pop("date_completed", None)
    append_metadata(task, note)
    add_history(task, "reopen", note, by=by)


def move_task(task, due_value, note, by="hermes"):
    task["date_due"] = due_value
    append_metadata(task, note)
    add_history(task, "reschedule", note, by=by)
