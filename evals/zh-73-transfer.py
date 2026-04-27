#!/usr/bin/env python3
"""
ZH-73: Document Builder Assistant -- System Instructions
Run from repo root on the runtime machine (ENCHS-PW-GenAI-Backend).
Safe to run twice -- create_doc_builder_assistant uses update_or_create.

Cross-platform equivalent of zh-73-transfer.sh (Windows/macOS/Linux).
"""

import subprocess
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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
# Main
# ---------------------------------------------------------------------------

def main():
    script_dir = Path(__file__).resolve().parent
    src = script_dir / "backend"

    # Optional positional arg: destination directory (defaults to script_dir/backend)
    dest = Path(sys.argv[1]) if len(sys.argv) > 1 else src

    print(f"[ZH-73] Transferring Document Builder management command to: {dest}")

    # Ensure target directory exists
    (dest / "app_chatbot" / "management" / "commands").mkdir(parents=True, exist_ok=True)

    # Copy __init__.py files and the management command
    files_to_copy = [
        (
            src / "app_chatbot" / "management" / "__init__.py",
            dest / "app_chatbot" / "management" / "__init__.py",
        ),
        (
            src / "app_chatbot" / "management" / "commands" / "__init__.py",
            dest / "app_chatbot" / "management" / "commands" / "__init__.py",
        ),
        (
            src / "app_chatbot" / "management" / "commands" / "create_doc_builder_assistant.py",
            dest / "app_chatbot" / "management" / "commands" / "create_doc_builder_assistant.py",
        ),
    ]

    for src_file, dest_file in files_to_copy:
        dest_file.parent.mkdir(parents=True, exist_ok=True)
        dest_file.write_bytes(src_file.read_bytes())
        print(f"[ZH-73] Copied: {dest_file}")

    print("[ZH-73] Done. Run on the target machine:")
    print("  python manage.py create_doc_builder_assistant")
    print("")
    print("  Verify:")
    print("  python manage.py shell -c \\")
    print(
        "    \"from app_chatbot.models import ChatAssistant; "
        "a = ChatAssistant.objects.get(name='Document Builder'); "
        "print(a.pk, a.description)\""
    )


if __name__ == "__main__":
    main()
