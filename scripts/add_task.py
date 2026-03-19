#!/usr/bin/env python3
import argparse
from task_lib import load_data, save_data

VALID_PRIORITY = {"Low", "Medium", "High", "Critical"}


def main():
    p = argparse.ArgumentParser(description="Add a new active task")
    p.add_argument("--title", required=True)
    p.add_argument("--due", default="none", help="none | YYYY-MM-DD | YYYY-MM-DDTHH:MM")
    p.add_argument("--priority", default="Medium", choices=sorted(VALID_PRIORITY))
    p.add_argument("--metadata", default="")
    args = p.parse_args()

    data = load_data()
    active = data.setdefault("tasks", {}).setdefault("active", [])

    # prevent duplicate title in active list
    if any(t.get("title", "").strip().lower() == args.title.strip().lower() for t in active):
        raise SystemExit(f"Task already exists in active list: {args.title}")

    task = {
        "title": args.title,
        "status": "Active",
        "date_due": args.due,
        "priority": args.priority,
        "task_metadata": args.metadata,
    }
    active.append(task)
    save_data(data)
    print(f"Added task: {args.title}")


if __name__ == "__main__":
    main()
