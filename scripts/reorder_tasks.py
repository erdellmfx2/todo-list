#!/usr/bin/env python3
"""
Ensure tasks.json is consistently ordered:
1) top-level keys in stable order
2) tasks.active first, tasks.completed second
3) tasks sorted by priority then due date then title
"""

import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TASKS_FILE = ROOT / "tasks.json"

PRIORITY_ORDER = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}


def due_key(value: str):
    if not value or value == "none":
        return (1, "9999-12-31T23:59")
    return (0, value)


def task_sort_key(task):
    p = task.get("priority", "Medium")
    return (
        PRIORITY_ORDER.get(p, 99),
        *due_key(task.get("date_due", "none")),
        task.get("title", "").lower(),
    )


def main():
    if not TASKS_FILE.exists():
        raise SystemExit(f"Missing {TASKS_FILE}")

    with open(TASKS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    tasks = data.setdefault("tasks", {})
    active = tasks.get("active", [])
    completed = tasks.get("completed", [])

    active = sorted(active, key=task_sort_key)
    completed = sorted(completed, key=task_sort_key)

    ordered = {
        "version": data.get("version", "1.0"),
        "description": data.get("description", "Task list with active tasks first and completed tasks below"),
        "updated_at": datetime.now().isoformat(),
        "tasks": {
            "active": active,
            "completed": completed,
        },
    }

    with open(TASKS_FILE, "w", encoding="utf-8") as f:
        json.dump(ordered, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"Reordered tasks.json | active={len(active)} completed={len(completed)}")


if __name__ == "__main__":
    main()
