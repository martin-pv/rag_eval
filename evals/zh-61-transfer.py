#!/usr/bin/env python3
"""
zh-61-transfer.py
Applies ZH-61: accept optional temperature on /streaming_response/
Run from inside ENCHS-PW-GenAI-Backend/ on the target machine.
Idempotent: safe to run twice.
Do NOT commit this script.

Cross-platform equivalent of zh-61-transfer.sh (Windows/macOS/Linux).
"""

import subprocess
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def patch(path: Path, old: str, new: str, label: str = "patch") -> None:
    """Replace first occurrence of old with new in path. Skip if old not found."""
    src = path.read_text(encoding="utf-8")
    if old not in src:
        print(f"[SKIP] {label}")
        return
    path.write_text(src.replace(old, new, 1), encoding="utf-8")
    print(f"[OK] {label}")


# ---------------------------------------------------------------------------
# Pre-flight: verify CWD contains the target file
# ---------------------------------------------------------------------------

REPO_ROOT = Path.cwd()
TARGET = REPO_ROOT / "app_chatbot" / "views" / "chatstream.py"

print(f"[zh-61] Starting transfer into: {REPO_ROOT}")

if not TARGET.is_file():
    print(f"[zh-61] ERROR: {TARGET} not found. Run from inside ENCHS-PW-GenAI-Backend/.")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Patch 1 — parse temperature after structured_output line
# ---------------------------------------------------------------------------

GUARD_1 = 'raw_temp = request.data.get("temperature", None)'
ANCHOR_1 = 'structured_output = bool(request.data.get("structured_output", False))'

src = TARGET.read_text(encoding="utf-8")

if GUARD_1 in src:
    print("[zh-61] Already applied: temperature parse block")
else:
    if ANCHOR_1 not in src:
        print(f"[zh-61] ERROR: anchor not found in {TARGET}")
        sys.exit(1)

    replacement_1 = ANCHOR_1 + """
            raw_temp = request.data.get("temperature", None)
            temperature = None
            if raw_temp is not None:
                try:
                    temperature = float(raw_temp)
                except (TypeError, ValueError):
                    temperature = None"""

    TARGET.write_text(src.replace(ANCHOR_1, replacement_1, 1), encoding="utf-8")
    print("[zh-61] Patched: temperature parse block inserted after structured_output")

# ---------------------------------------------------------------------------
# Patch 2 — clamp and apply temperature to data dict
# ---------------------------------------------------------------------------

GUARD_2 = 'data["temperature"] = max(0.0, min(2.0, temperature))'
ANCHOR_2 = "data = get_default_data(stream=True)"

src = TARGET.read_text(encoding="utf-8")

if GUARD_2 in src:
    print("[zh-61] Already applied: temperature clamp block")
else:
    if ANCHOR_2 not in src:
        print(f"[zh-61] ERROR: anchor not found in {TARGET}")
        sys.exit(1)

    replacement_2 = ANCHOR_2 + """
            if temperature is not None:
                data["temperature"] = max(0.0, min(2.0, temperature))"""

    TARGET.write_text(src.replace(ANCHOR_2, replacement_2, 1), encoding="utf-8")
    print("[zh-61] Patched: temperature clamp applied after get_default_data")

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------

print()
print("[zh-61] Complete. Verify:")
print("  python manage.py check")
print("  # POST /streaming_response/ with temperature=0.9 -> OpenAI receives temperature=0.9")
print("  # POST /streaming_response/ with temperature=5.0 -> clamped to 2.0")
print("  # POST /streaming_response/ without temperature -> existing behavior unchanged")
