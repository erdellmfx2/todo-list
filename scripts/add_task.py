#!/usr/bin/env python3
import argparse
from task_lib import find_task, load_data, new_task, refresh_repo_from_remote, repo_lock, save_data

VALID_PRIORITY = {"Low", "Medium", "High", "Critical"}


def main():
    p = argparse.ArgumentParser(description="Add a new active task")
    p.add_argument("--title", required=True)
    p.add_argument("--due", default="none", help="none | YYYY-MM-DD | YYYY-MM-DDTHH:MM")
    p.add_argument("--priority", default="Medium", choices=sorted(VALID_PRIORITY))
    p.add_argument("--metadata", default="")
    args = p.parse_args()

    with repo_lock():
        refresh_repo_from_remote()
        data = load_data()
        tasks = data.setdefault("tasks", {})
        active = tasks.setdefault("active", [])
        completed = tasks.setdefault("completed", [])

        _, existing = find_task(active, completed, args.title)
        if existing:
            raise SystemExit(f"Task already exists: {args.title}")

        metadata = args.metadata or "Created via add_task.py"
        task = new_task(args.title, due=args.due, priority=args.priority, metadata=metadata, by="helper-script")
        active.append(task)
        save_data(data)
        print(f"Added task: {args.title}")


if __name__ == "__main__":
    main()
