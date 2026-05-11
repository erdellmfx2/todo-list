#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

# Refresh remote refs so we can verify local vs remote state.
git fetch origin main

# Stage the canonical task file.
git add tasks.json

# Only commit if there are actual staged changes.
if ! git diff --cached --quiet; then
  git commit -m "Update tasks.json via helper scripts"

  if ! git push origin main; then
    echo "Push rejected: origin/main changed during this task update. Re-run the task command so it can refresh, reapply the change, and push cleanly." >&2
    exit 1
  fi
else
  read -r ahead_count behind_count < <(git rev-list --left-right --count HEAD...origin/main)
  if [[ "$ahead_count" == "0" && "$behind_count" != "0" ]]; then
    git reset --hard origin/main >/dev/null
  elif [[ "$ahead_count" != "0" && "$behind_count" != "0" ]]; then
    echo "Sync verification failed: local repo has diverged from origin/main." >&2
    exit 1
  fi
fi

git fetch origin main >/dev/null 2>&1
read -r ahead_count behind_count < <(git rev-list --left-right --count HEAD...origin/main)
if [[ "$ahead_count" != "0" || "$behind_count" != "0" ]]; then
  echo "Sync verification failed: local repo does not match origin/main (ahead=$ahead_count behind=$behind_count)." >&2
  exit 1
fi

echo "Synced todo-list/tasks.json to GitHub."
