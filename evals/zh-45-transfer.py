#!/usr/bin/env python3
# zh-45-transfer.py
# ZH-45: Add xclass_level to Folder model + API
# Run from repo root on the runtime machine (ENCHS-PW-GenAI-Backend).
# Safe to run twice — writes are idempotent.
# Cross-platform replacement for zh-45-transfer.sh

import subprocess
import sys
import shutil
from pathlib import Path


def git(*args):
    subprocess.run(["git", *args], check=True)


def git_or(*args):
    return subprocess.run(["git", *args]).returncode == 0


def ensure(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def touch(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch()


def patch(path, old, new, label="patch"):
    src = path.read_text(encoding="utf-8")
    if old not in src:
        print(f"[SKIP] {label}")
        return
    path.write_text(src.replace(old, new, 1), encoding="utf-8")
    print(f"[OK] {label}")


def append_if_missing(path, line):
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    if line.strip() not in text:
        with path.open("a", encoding="utf-8") as f:
            f.write(line if line.endswith("\n") else line + "\n")
        print(f"[OK] Appended: {line.strip()}")
    else:
        print(f"[SKIP] Already present: {line.strip()}")


# ---------------------------------------------------------------------------
# Resolve source and destination directories.
# The bash script derives SCRIPT_DIR from the location of the .sh file,
# uses SRC = SCRIPT_DIR/backend, and DEST defaults to SRC unless overridden
# by the first positional argument ($1).
#
# Here we replicate that logic: SCRIPT_DIR is the directory of this .py file,
# SRC is SCRIPT_DIR/backend, and DEST defaults to SRC unless sys.argv[1] is given.
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
SRC = SCRIPT_DIR / "backend"
DEST = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else SRC

print(f"[ZH-45] Transferring xclass_level changes to: {DEST}")

# ---------------------------------------------------------------------------
# 1. Folder model — add xclass_level field
# ---------------------------------------------------------------------------
src_models = SRC / "app_retrieval" / "models.py"
dst_models = DEST / "app_retrieval" / "models.py"
dst_models.parent.mkdir(parents=True, exist_ok=True)
shutil.copy2(src_models, dst_models)

# ---------------------------------------------------------------------------
# 2. Migration
# ---------------------------------------------------------------------------
src_migration = SRC / "app_retrieval" / "migrations" / "0028_folder_xclass_level.py"
dst_migration = DEST / "app_retrieval" / "migrations" / "0028_folder_xclass_level.py"
dst_migration.parent.mkdir(parents=True, exist_ok=True)
shutil.copy2(src_migration, dst_migration)

# ---------------------------------------------------------------------------
# 3. FolderView — exposes xclass_level in GET /ws/folders/
# ---------------------------------------------------------------------------
src_folders = SRC / "app_retrieval" / "views" / "folders.py"
dst_folders = DEST / "app_retrieval" / "views" / "folders.py"
dst_folders.parent.mkdir(parents=True, exist_ok=True)
shutil.copy2(src_folders, dst_folders)

print("[ZH-45] Done. Verify with:")
print("  python manage.py migrate")
print("  python manage.py check")
print("  # GET /ws/folders/ should return xclass_level: null for existing folders")
