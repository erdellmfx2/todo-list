#!/usr/bin/env python3
import json
import subprocess
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
TASKS_FILE = ROOT / "tasks.json"
SYNC_SCRIPT = ROOT / "scripts" / "sync_repo.sh"


def load_data():
    if not TASKS_FILE.exists():
        return {
            "version": "1.0",
            "description": "Task list with active tasks first and completed tasks below",
            "updated_at": datetime.now().isoformat(),
            "tasks": {"active": [], "completed": []},
        }
    with open(TASKS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_data(data):
    data["updated_at"] = datetime.now().isoformat()
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


def find_task(active_list, completed_list, title):
    for t in active_list:
        if t.get("title", "").strip().lower() == title.strip().lower():
            return "active", t
    for t in completed_list:
        if t.get("title", "").strip().lower() == title.strip().lower():
            return "completed", t
    return None, None


def append_metadata(task, note):
    existing = task.get("task_metadata", "")
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{ts}] {note}".strip()
    if existing:
        task["task_metadata"] = existing.rstrip() + "\n" + entry
    else:
        task["task_metadata"] = entry
