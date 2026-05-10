#!/usr/bin/env python3
import argparse
from task_lib import find_task, load_data, mark_complete, save_data


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

    if bucket == "completed":
        print(f"Task already completed: {task['title']}")
        return

    mark_complete(task, note=args.note, by="helper-script")
    active.remove(task)
    completed.append(task)

    save_data(data)
    print(f"Completed task: {task['title']}")


if __name__ == "__main__":
    main()
