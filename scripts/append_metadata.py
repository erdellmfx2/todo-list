#!/usr/bin/env python3
import argparse
from task_lib import append_metadata, find_task, load_data, refresh_repo_from_remote, repo_lock, save_data


def main():
    p = argparse.ArgumentParser(description="Append metadata note to a task")
    p.add_argument("--title", required=True)
    p.add_argument("--note", required=True)
    args = p.parse_args()

    with repo_lock():
        refresh_repo_from_remote()
        data = load_data()
        active = data.setdefault("tasks", {}).setdefault("active", [])
        completed = data.setdefault("tasks", {}).setdefault("completed", [])

        _, task = find_task(active, completed, args.title)
        if not task:
            raise SystemExit(f"Task not found: {args.title}")

        append_metadata(task, args.note)
        save_data(data)
        print(f"Appended metadata for: {task['title']}")


if __name__ == "__main__":
    main()
