#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

if ! git diff --quiet || ! git diff --cached --quiet; then
  git add tasks.json
  git commit -m "Update tasks.json via helper scripts" || true
fi

TOKEN="$(gh auth token)"
git push "https://erdellmfx2:${TOKEN}@github.com/erdellmfx2/todo-list.git" main

echo "Synced todo-list/tasks.json to GitHub."