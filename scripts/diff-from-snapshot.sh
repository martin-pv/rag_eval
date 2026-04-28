#!/usr/bin/env bash
# Thin wrapper — see update-main-sync.py
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
exec python3 "$ROOT/update-main-sync.py" diff "${1:-8115d83}"
