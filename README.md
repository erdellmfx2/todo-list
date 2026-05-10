# todo-list

JSON-based task repository.

## Task Structure
Each task includes:
1. `title` — description of the task to be done
2. `status` — `Active` or `Complete`
3. `date_due` — `none`, date, or date-time
4. `priority` — `Low`, `Medium`, `High`, `Critical`
5. `task_metadata` — text notes (search results, discussion history, updates, breakdowns, user input, etc.)

## Ordering
Tasks are stored in `tasks.json` with:
- `tasks.active` (top)
- `tasks.completed` (below)

## Migration
Active tasks were copied from:
- `erdellmfx2/todo-manager` → `tasks/active/*.json`

Initial migrated task count:
- Active: 1
- Completed: 0

## Helper Scripts
Located in `scripts/`:

- `add_task.py` — add a new active task
- `update_task.py` — edit title/status/due/priority and append metadata notes
- `complete_task.py` — mark a task complete and move it to completed list
- `append_metadata.py` — append notes to `task_metadata`
- `reorder_tasks.py` — enforce ordering: active first, completed second (with stable sort)
- `sync_repo.sh` — commit/push `tasks.json` updates
- `todo_guardian_report.py` — generate the Telegram-style Todo Guardian report
- `hermes_task_manager.py` — Hermes-facing task command handler for create/complete/move requests

### Examples
```bash
# Add task
python3 scripts/add_task.py --title "Prepare grant outline" --due 2026-03-25 --priority High --metadata "Initial draft requested by Erdell"

# Add note from discussion/web search
python3 scripts/append_metadata.py --title "Prepare grant outline" --note "Web search: found NSF template and timeline best practices"

# Update priority/due/status
python3 scripts/update_task.py --title "Prepare grant outline" --priority Critical --due 2026-03-23

# Complete task
python3 scripts/complete_task.py --title "Prepare grant outline" --note "Submitted final draft"

# Reorder tasks.json (active first, completed second)
python3 scripts/reorder_tasks.py

# Sync changes to GitHub
./scripts/sync_repo.sh

# Hermes-side shortcuts for natural task requests
python3 scripts/hermes_task_manager.py create --title "pick the kids up" --when "tomorrow at 3pm" --priority Critical
python3 scripts/hermes_task_manager.py complete --query "go to sleep"
python3 scripts/hermes_task_manager.py move --query "going home" --when "next wednesday at 4 pm"
```

## Todo Guardian Updates
Todo Guardian is now configured to read from `erdellmfx2/todo-list` (`tasks.json -> tasks.active`) and can write learned insights/discussion notes into task metadata via helper scripts.

### Auto-sync behavior
All task mutations performed through the helper scripts now call `scripts/sync_repo.sh` automatically after `tasks.json` is written, so task changes are committed and pushed to GitHub immediately.
