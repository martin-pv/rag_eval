#!/usr/bin/env bash
# Thin wrapper — see update-main-sync.py (defaults: backup branch vs main)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
exec python3 "$ROOT/update-main-sync.py" diff "$@"
