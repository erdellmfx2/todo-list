#!/usr/bin/env python3
import argparse
import re
from datetime import datetime, timedelta
from dateutil import parser as date_parser

from task_lib import (
    LOCAL_TZ,
    add_history,
    append_metadata,
    current_time,
    find_task,
    load_data,
    mark_complete,
    move_task,
    new_task,
    refresh_repo_from_remote,
    repo_lock,
    reopen_task,
    resolve_task,
    save_data,
)

VALID_PRIORITY = {"Low", "Medium", "High", "Critical"}
WEEKDAYS = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}
TIME_RE = re.compile(r"\b(?:at\s+)?(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b", re.IGNORECASE)


def parse_due_text(text, reference=None):
    raw = (text or "").strip()
    if not raw:
        raise ValueError("Due text cannot be empty")

    lowered = raw.lower().strip()
    if lowered in {"none", "no due", "no due date"}:
        return "none"

    reference = reference or current_time()
    explicit_time = has_explicit_time(lowered)
    time_bits = extract_time_bits(lowered) if explicit_time else None

    relative_date = parse_relative_date(lowered, reference)
    if relative_date is not None:
        return format_due(relative_date, time_bits)

    cleaned = raw
    if lowered.startswith("on "):
        cleaned = raw[3:].strip()
    if lowered.startswith("for "):
        cleaned = raw[4:].strip()

    default_dt = reference.replace(hour=9, minute=0, second=0, microsecond=0)
    parsed = date_parser.parse(cleaned, fuzzy=True, default=default_dt)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=LOCAL_TZ)
    else:
        parsed = parsed.astimezone(LOCAL_TZ)

    if explicit_time:
        return parsed.isoformat(timespec="seconds")
    return parsed.date().isoformat()


def has_explicit_time(text):
    return bool(TIME_RE.search(text)) or "noon" in text or "midnight" in text


def extract_time_bits(text):
    lower = text.lower()
    if "noon" in lower:
        return 12, 0
    if "midnight" in lower:
        return 0, 0

    match = TIME_RE.search(text)
    if not match:
        return None

    hour = int(match.group(1))
    minute = int(match.group(2) or 0)
    suffix = (match.group(3) or "").lower()

    if suffix == "am":
        if hour == 12:
            hour = 0
    elif suffix == "pm":
        if hour != 12:
            hour += 12

    if not 0 <= hour <= 23 or not 0 <= minute <= 59:
        raise ValueError(f"Invalid time in due text: {text}")
    return hour, minute


def parse_relative_date(text, reference):
    date_part = strip_time_fragment(text).strip()
    if date_part.startswith("on "):
        date_part = date_part[3:].strip()
    if date_part.startswith("for "):
        date_part = date_part[4:].strip()

    if date_part == "today":
        return reference.date()
    if date_part == "tomorrow":
        return (reference + timedelta(days=1)).date()

    weekday_match = re.fullmatch(r"(?:next|this)?\s*(monday|tuesday|wednesday|thursday|friday|saturday|sunday)", date_part)
    if weekday_match:
        weekday_name = weekday_match.group(1)
        target = WEEKDAYS[weekday_name]
        prefix = date_part.replace(weekday_name, "").strip() or "plain"
        current = reference.weekday()
        delta = (target - current) % 7
        if prefix == "next" or delta == 0:
            delta = 7 if delta == 0 else delta
        elif prefix == "this":
            if delta == 0:
                delta = 0
        elif prefix == "plain" and delta == 0 and has_explicit_time(text):
            candidate = reference.replace(hour=extract_time_bits(text)[0], minute=extract_time_bits(text)[1], second=0, microsecond=0)
            if candidate <= reference:
                delta = 7
        return (reference + timedelta(days=delta)).date()

    return None


def strip_time_fragment(text):
    text = re.sub(r"\bnoon\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\bmidnight\b", "", text, flags=re.IGNORECASE)
    text = TIME_RE.sub("", text)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\bat\b", "", text)
    return text.strip()


def format_due(date_value, time_bits=None):
    if time_bits is None:
        return date_value.isoformat()
    hour, minute = time_bits
    dt = datetime(
        date_value.year,
        date_value.month,
        date_value.day,
        hour,
        minute,
        tzinfo=LOCAL_TZ,
    )
    return dt.isoformat(timespec="seconds")


def format_resolution_error(query, candidates):
    if not candidates:
        return f"Task not found: {query}"
    lines = [f"Task match for '{query}' is ambiguous. Top candidates:"]
    for score, bucket, task in candidates[:5]:
        due = task.get("date_due", "none")
        lines.append(f"- [{bucket}] {task.get('title', '<untitled>')} (due: {due}, priority: {task.get('priority', 'n/a')}, score: {score:.2f})")
    return "\n".join(lines)


def create_task(args):
    data = load_data()
    active = data.setdefault("tasks", {}).setdefault("active", [])

    _, existing = find_task(active, data.setdefault("tasks", {}).setdefault("completed", []), args.title)
    if existing:
        raise SystemExit(f"Task already exists: {args.title}")

    due_value = parse_due_text(args.when) if args.when else "none"
    metadata = args.note or "Created via Hermes task manager."
    task = new_task(args.title, due=due_value, priority=args.priority, metadata=metadata, by=args.by)
    add_history(task, "create_request", f"Original due text: {args.when or 'none'}", by=args.by)
    active.append(task)
    save_data(data)
    print(f"Created task: {task['title']} | due={task['date_due']} | priority={task['priority']} | id={task['id']}")


def complete_task(args):
    data = load_data()
    tasks = data.setdefault("tasks", {})
    active = tasks.setdefault("active", [])
    completed = tasks.setdefault("completed", [])

    resolved, candidates = resolve_task(active, completed, args.query, include_completed=True)
    if not resolved:
        raise SystemExit(format_resolution_error(args.query, candidates))

    bucket, task = resolved
    if bucket == "completed":
        print(f"Task already completed: {task['title']}")
        return

    note = args.note or "Marked complete via Hermes task manager."
    mark_complete(task, note=note, by=args.by)
    active.remove(task)
    completed.append(task)
    save_data(data)
    print(f"Completed task: {task['title']} | completed_at={task.get('completed_at')}")


def move_task_command(args):
    data = load_data()
    tasks = data.setdefault("tasks", {})
    active = tasks.setdefault("active", [])
    completed = tasks.setdefault("completed", [])

    resolved, candidates = resolve_task(active, completed, args.query, include_completed=True)
    if not resolved:
        raise SystemExit(format_resolution_error(args.query, candidates))

    bucket, task = resolved
    due_value = parse_due_text(args.when)
    note = args.note or f"Due date moved to {args.when} via Hermes task manager."

    if bucket == "completed":
        completed.remove(task)
        reopen_task(task, note="Reopened task because a new due date was assigned.", by=args.by)
        active.append(task)

    move_task(task, due_value, note=note, by=args.by)
    if args.priority:
        task["priority"] = args.priority
        append_metadata(task, f"Priority updated to {args.priority} during move.")
        add_history(task, "priority_update", f"Priority updated to {args.priority}", by=args.by)

    save_data(data)
    print(f"Moved task: {task['title']} | due={task['date_due']} | status={task['status']}")


def build_parser():
    parser = argparse.ArgumentParser(description="Hermes task manager for the GitHub-backed todo list")
    parser.add_argument("--by", default="hermes", help="Actor label to write into task history")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create = subparsers.add_parser("create", help="Create a task")
    create.add_argument("--title", required=True)
    create.add_argument("--when", help="Natural due text such as 'tomorrow at 3pm' or 'next Wednesday at 4 pm'")
    create.add_argument("--priority", default="Medium", choices=sorted(VALID_PRIORITY))
    create.add_argument("--note", help="Optional metadata note")
    create.set_defaults(func=create_task)

    complete = subparsers.add_parser("complete", help="Complete a task")
    complete.add_argument("--query", required=True, help="Task title or distinctive fragment")
    complete.add_argument("--note", help="Optional completion note")
    complete.set_defaults(func=complete_task)

    move = subparsers.add_parser("move", help="Move/reschedule a task")
    move.add_argument("--query", required=True, help="Task title or distinctive fragment")
    move.add_argument("--when", required=True, help="Natural due text such as 'next Wednesday at 4 pm'")
    move.add_argument("--priority", choices=sorted(VALID_PRIORITY))
    move.add_argument("--note", help="Optional reschedule note")
    move.set_defaults(func=move_task_command)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    with repo_lock():
        refresh_repo_from_remote()
        args.func(args)


if __name__ == "__main__":
    main()
