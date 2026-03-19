#!/usr/bin/env python3
import argparse
from task_lib import load_data, save_data, find_task, append_metadata


def main():
    p = argparse.ArgumentParser(description="Mark task complete and move to completed list")
    p.add_argument("--title", required=True)
    p.add_argument("--note", default="Marked complete")
    args = p.parse_args()

    data = load_data()
    active = data.setdefault("tasks", {}).setdefault("active", [])
    completed = data.setdefault("tasks", {}).setdefault("completed", [])

    bucket, task = find_task(active, completed, args.title)
    if not task:
        raise SystemExit(f"Task not found: {args.title}")

    task["status"] = "Complete"
    append_metadata(task, args.note)

    if bucket == "active":
        active.remove(task)
        completed.append(task)

    save_data(data)
    print(f"Completed task: {task['title']}")


if __name__ == "__main__":
    main()
