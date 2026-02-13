#!/usr/bin/env bash
set -e

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

if [ ! -d "frontend/dist" ]; then
  echo "请先在 frontend 目录执行 npm install && npm run build"
  exit 1
fi

pyinstaller -F backend/run.py \
  --name support-mail-assistant \
  --add-data "frontend/dist:frontend/dist" \
  --hidden-import uvicorn.logging
