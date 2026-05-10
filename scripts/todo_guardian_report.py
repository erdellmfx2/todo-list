#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from datetime import date, datetime, time
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

REPO_ROOT = Path(__file__).resolve().parents[1]
TASKS_FILE = REPO_ROOT / "tasks.json"
TIMEZONE = ZoneInfo("America/New_York")
VIEW_URL = "https://github.com/erdellmfx2/todo-list"
PRIORITY_ORDER = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
PRIORITY_EMOJI = {
    "Critical": "⚡️",
    "High": "🔴",
    "Medium": "🟡",
    "Low": "🔵",
}


@dataclass
class TaskView:
    raw: dict[str, Any]
    title: str
    status: str
    priority: str
    due_raw: str
    due_dt: datetime | None
    due_date_only: bool
    recurrence: dict[str, Any] | None


@dataclass
class DueInfo:
    due_dt: datetime | None
    due_date_only: bool


def load_tasks() -> dict[str, Any]:
    with TASKS_FILE.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def parse_due(value: str | None) -> DueInfo:
    if not value or str(value).strip().lower() == "none":
        return DueInfo(None, False)
    text = str(value).strip()
    if len(text) == 10 and text.count("-") == 2:
        dt = datetime.combine(date.fromisoformat(text), time.min, TIMEZONE)
        return DueInfo(dt, True)
    normalized = text.replace("Z", "+00:00")
    dt = datetime.fromisoformat(normalized)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=TIMEZONE)
    else:
        dt = dt.astimezone(TIMEZONE)
    return DueInfo(dt, False)


def parse_completion_date(task: dict[str, Any]) -> datetime | None:
    for key in ("completed_at", "date_completed"):
        value = task.get(key)
        if not value:
            continue
        try:
            info = parse_due(value)
            return info.due_dt
        except Exception:
            continue
    return None


def task_view(task: dict[str, Any]) -> TaskView:
    info = parse_due(task.get("date_due"))
    return TaskView(
        raw=task,
        title=task.get("title", "Untitled task"),
        status=task.get("status", "Active"),
        priority=task.get("priority", "Medium"),
        due_raw=str(task.get("date_due", "none")),
        due_dt=info.due_dt,
        due_date_only=info.due_date_only,
        recurrence=task.get("recurrence") if isinstance(task.get("recurrence"), dict) else None,
    )


def is_overdue(task: TaskView, now: datetime) -> bool:
    if task.due_dt is None:
        return False
    if task.due_date_only:
        return task.due_dt.date() < now.date()
    return task.due_dt.date() < now.date() or task.due_dt < now and task.due_dt.date() < now.date()


def is_due_today(task: TaskView, today: date) -> bool:
    return task.due_dt is not None and task.due_dt.date() == today


def format_due(task: TaskView, overdue: bool = False) -> str:
    if task.due_dt is None:
        return "No due date"
    dt = task.due_dt.astimezone(TIMEZONE)
    if task.due_date_only:
        if overdue:
            return f"Was due: {dt.strftime('%Y-%m-%d')}"
        return f"Due: {dt.strftime('%Y-%m-%d')}"
    if overdue:
        return f"Was due: {dt.strftime('%Y-%m-%d at %-I:%M %p')}"
    return f"Due: {dt.strftime('%Y-%m-%d at %-I:%M %p')}"


def deadline_label(task: TaskView) -> str:
    if task.due_dt is None:
        return "No due date"
    dt = task.due_dt.astimezone(TIMEZONE)
    if task.due_date_only:
        return dt.strftime("%Y-%m-%d")
    return dt.strftime("%-I:%M %p")


def sort_tasks(tasks: list[TaskView]) -> list[TaskView]:
    def key(task: TaskView):
        due_sort = task.due_dt.isoformat() if task.due_dt else "9999-12-31T23:59:59"
        return (PRIORITY_ORDER.get(task.priority, 99), due_sort, task.title.lower())

    return sorted(tasks, key=key)


def recurrence_pattern(rec: dict[str, Any]) -> str:
    rtype = rec.get("type", "monthly")
    interval = rec.get("interval", 1)
    if rtype == "monthly":
        return f"Every {interval} monthly(s)"
    if rtype == "weekly":
        return f"Every {interval} week(s)"
    if rtype == "daily":
        return f"Every {interval} day(s)"
    return f"Every {interval} {rtype}(s)"


def human_delta(target: datetime, now: datetime) -> str:
    if target <= now:
        return "now"
    total_seconds = int((target - now).total_seconds())
    days, rem = divmod(total_seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, _ = divmod(rem, 60)
    parts: list[str] = []
    if days:
        parts.append(f"{days}d")
    if hours or days:
        parts.append(f"{hours}h")
    if minutes and not days:
        parts.append(f"{minutes}m")
    return " ".join(parts) if parts else "<1m"


def git_sync_line() -> str:
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    if status.stdout.strip():
        return "⚠️ Git sync: local changes pending"
    return "☁️ GitHub Backup: ✅ Git sync: no changes to commit"


def main() -> None:
    data = load_tasks()
    now = datetime.now(TIMEZONE)
    today = now.date()

    active = [task_view(t) for t in data.get("tasks", {}).get("active", [])]
    completed = data.get("tasks", {}).get("completed", [])

    due_today = sort_tasks([t for t in active if is_due_today(t, today)])
    overdue = sort_tasks([t for t in active if is_overdue(t, now)])
    recurring = sort_tasks([t for t in active if t.recurrence and t.recurrence.get("enabled", False)])

    recurring_titles = {t.title for t in recurring}
    due_today_titles = {t.title for t in due_today}
    overdue_titles = {t.title for t in overdue}

    remaining = [
        t for t in active
        if t.title not in due_today_titles
        and t.title not in overdue_titles
        and t.title not in recurring_titles
    ]

    groups: dict[str, list[TaskView]] = {"Critical": [], "High": [], "Medium": [], "Low": []}
    for task in remaining:
        groups.setdefault(task.priority, []).append(task)
    for key in list(groups):
        groups[key] = sort_tasks(groups[key])

    completed_today = 0
    for task in completed:
        finished = parse_completion_date(task)
        if finished and finished.astimezone(TIMEZONE).date() == today:
            completed_today += 1

    lines: list[str] = []
    lines.append("📅 TODO GUARDIAN REPORT")
    lines.append(f"🗓  Date: {today.strftime('%Y-%m-%d')}")
    lines.append(f"⏰  Time: {now.strftime('%I:%M %p %Z')}")
    lines.append("")
    lines.append("📊 Task Summary:")
    lines.append(f"• Total Active Tasks: {len(active)}")
    lines.append(f"• Due Today: {len(due_today)}")
    lines.append(f"• Overdue: {len(overdue)}")
    lines.append(f"• Recurring: {len(recurring)}")
    lines.append(f"• Completed Today: {completed_today}")

    if due_today:
        lines.append("")
        lines.append("🚨 TODAY'S DEADLINES:")
        for task in due_today:
            lines.append(f"• {task.title} ({deadline_label(task)} • {task.priority.upper()})")

    if overdue:
        lines.append("")
        lines.append("⚠️ OVERDUE TASKS:")
        for task in overdue:
            lines.append(f"• {task.title} ({format_due(task, overdue=True)} • {task.priority.upper()})")

    for priority in ["Critical", "High", "Medium", "Low"]:
        items = groups.get(priority, [])
        if not items:
            continue
        lines.append("")
        lines.append(f"{PRIORITY_EMOJI.get(priority, '•')} {priority.upper()} PRIORITY:")
        for task in items:
            lines.append(f"• {task.title} ({format_due(task)}")
            lines[-1] += ")"

    if recurring:
        lines.append("")
        lines.append("🔄 RECURRING TASKS:")
        for task in recurring:
            rec = task.recurrence or {}
            next_info = parse_due(rec.get("next_due")).due_dt
            next_text = next_info.astimezone(TIMEZONE).strftime("%Y-%m-%d at %-I:%M %p") if next_info else "Unknown"
            delta_text = human_delta(next_info, now) if next_info else "Unknown"
            completed_occ = rec.get("completed_occurrences", 0)
            total_occ = rec.get("total_occurrences", "?")
            remaining_occ = rec.get("remaining_occurrences", "?")
            lines.append(f"• {task.title}")
            lines.append(f"⏰ Next: {next_text} ({delta_text})")
            lines.append(f"🔄 Pattern: {recurrence_pattern(rec)}")
            lines.append(f"📊 Progress: {completed_occ}/{total_occ} completed, {remaining_occ} remaining")

    lines.append("")
    lines.append("💡 Report Features:")
    lines.append("• Date and time clearly separated")
    lines.append("• Recurring task tracking with next occurrence")
    lines.append("• Today's deadlines highlighted")
    lines.append("• Overdue tasks flagged")
    lines.append("• Priority-based organization")
    lines.append("")
    lines.append(git_sync_line())
    lines.append(f"📋 View all tasks: {VIEW_URL}")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
