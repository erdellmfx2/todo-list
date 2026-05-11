#!/usr/bin/env python3
"""
Ensure tasks.json is consistently ordered:
1) top-level keys in stable order
2) tasks.active first, tasks.completed second
3) tasks sorted by priority then due date then title
"""

import json

from task_lib import current_time, load_data, refresh_repo_from_remote, repo_lock, save_data

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
    with repo_lock():
        refresh_repo_from_remote()
        data = load_data()
        tasks = data.setdefault("tasks", {})
        active = sorted(tasks.get("active", []), key=task_sort_key)
        completed = sorted(tasks.get("completed", []), key=task_sort_key)

        ordered = {
            "version": data.get("version", "1.0"),
            "description": data.get("description", "Task list with active tasks first and completed tasks below"),
            "updated_at": current_time().isoformat(),
            "tasks": {
                "active": active,
                "completed": completed,
            },
        }

        save_data(ordered)
        print(f"Reordered tasks.json | active={len(active)} completed={len(completed)}")


if __name__ == "__main__":
    main()
