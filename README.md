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
