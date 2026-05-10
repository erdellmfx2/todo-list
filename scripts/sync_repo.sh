#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

# Stage the canonical task file.
git add tasks.json

# Only commit if there are actual staged changes.
if ! git diff --cached --quiet; then
  git commit -m "Update tasks.json via helper scripts"
fi

# Rebase onto the remote in case tasks were changed elsewhere.
git pull --rebase origin main

git push origin main

echo "Synced todo-list/tasks.json to GitHub."
