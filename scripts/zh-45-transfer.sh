#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="$SCRIPT_DIR/backend"
DEST="${1:-$SCRIPT_DIR/backend}"

echo "[ZH-45] Transferring xclass_level changes to: $DEST"

# 1. Folder model — add xclass_level field
cp "$SRC/app_retrieval/models.py" \
   "$DEST/app_retrieval/models.py"

# 2. Migration
cp "$SRC/app_retrieval/migrations/0028_folder_xclass_level.py" \
   "$DEST/app_retrieval/migrations/0028_folder_xclass_level.py"

# 3. FolderView — exposes xclass_level in GET /ws/folders/
cp "$SRC/app_retrieval/views/folders.py" \
   "$DEST/app_retrieval/views/folders.py"

echo "[ZH-45] Done. Verify with:"
echo "  python manage.py migrate"
echo "  python manage.py check"
echo "  # GET /ws/folders/ should return xclass_level: null for existing folders"
