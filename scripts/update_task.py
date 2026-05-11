#!/usr/bin/env python3
import argparse
from task_lib import add_history, append_metadata, find_task, load_data, refresh_repo_from_remote, reopen_task, repo_lock, save_data


def main():
    p = argparse.ArgumentParser(description="Update task fields")
    p.add_argument("--title", required=True, help="Existing task title")
    p.add_argument("--new-title")
    p.add_argument("--status", choices=["Active", "Complete"])
    p.add_argument("--due", help="none | YYYY-MM-DD | YYYY-MM-DDTHH:MM")
    p.add_argument("--priority", choices=["Low", "Medium", "High", "Critical"])
    p.add_argument("--metadata-note", help="Append note to task_metadata")
    args = p.parse_args()

    with repo_lock():
        refresh_repo_from_remote()
        data = load_data()
        active = data.setdefault("tasks", {}).setdefault("active", [])
        completed = data.setdefault("tasks", {}).setdefault("completed", [])

        bucket, task = find_task(active, completed, args.title)
        if not task:
            raise SystemExit(f"Task not found: {args.title}")

        if args.new_title:
            old_title = task.get("title", "")
            task["title"] = args.new_title
            add_history(task, "rename", f"Renamed from '{old_title}' to '{args.new_title}'", by="helper-script")
        if args.due:
            task["date_due"] = args.due
            add_history(task, "reschedule", f"Due date updated to {args.due}", by="helper-script")
        if args.priority:
            task["priority"] = args.priority
            add_history(task, "priority_update", f"Priority updated to {args.priority}", by="helper-script")
        if args.metadata_note:
            append_metadata(task, args.metadata_note)

        if args.status and args.status != task.get("status"):
            task["status"] = args.status
            if args.status == "Complete" and bucket == "active":
                active.remove(task)
                completed.append(task)
                add_history(task, "complete", "Marked complete via update_task.py", by="helper-script")
            elif args.status == "Active" and bucket == "completed":
                completed.remove(task)
                active.append(task)
                reopen_task(task, note="Reopened via update_task.py", by="helper-script")

        save_data(data)
        print(f"Updated task: {task['title']}")


if __name__ == "__main__":
    main()
