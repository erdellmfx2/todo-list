#!/usr/bin/env python3
import argparse
from task_lib import load_data, save_data, find_task, append_metadata


def main():
    p = argparse.ArgumentParser(description="Update task fields")
    p.add_argument("--title", required=True, help="Existing task title")
    p.add_argument("--new-title")
    p.add_argument("--status", choices=["Active", "Complete"])
    p.add_argument("--due", help="none | YYYY-MM-DD | YYYY-MM-DDTHH:MM")
    p.add_argument("--priority", choices=["Low", "Medium", "High", "Critical"])
    p.add_argument("--metadata-note", help="Append note to task_metadata")
    args = p.parse_args()

    data = load_data()
    active = data.setdefault("tasks", {}).setdefault("active", [])
    completed = data.setdefault("tasks", {}).setdefault("completed", [])

    bucket, task = find_task(active, completed, args.title)
    if not task:
        raise SystemExit(f"Task not found: {args.title}")

    if args.new_title:
        task["title"] = args.new_title
    if args.due:
        task["date_due"] = args.due
    if args.priority:
        task["priority"] = args.priority
    if args.metadata_note:
        append_metadata(task, args.metadata_note)

    # Handle status transitions
    if args.status and args.status != task.get("status"):
        task["status"] = args.status
        if args.status == "Complete" and bucket == "active":
            active.remove(task)
            completed.append(task)
        elif args.status == "Active" and bucket == "completed":
            completed.remove(task)
            active.append(task)

    save_data(data)
    print(f"Updated task: {task['title']}")


if __name__ == "__main__":
    main()
