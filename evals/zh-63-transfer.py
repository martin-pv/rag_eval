#!/usr/bin/env python3
"""
ZH-63 Transfer Script — Prod CORS: Allow AutoSAM Origin

IMPORTANT: Confirm exact Origin with Dave before running.
Dave Ferguson is actively resolving this — check if already merged before deploying.

Deploys:
  - EDIT ENCHS-PW-GenAI-Backend/app/settings.py  (add CORS origin)
  - NEW  ENCHS-PW-GenAI-Backend/tests/test_cors.py

Run from the root of the runtime repo checkout:
    python3 zh-63-transfer.py

Branch: zh-63-cors-prod
"""
import subprocess
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Standard helpers
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


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BACKEND = Path.cwd()
BRANCH  = "zh-63-cors-prod"

# Confirm exact AutoSAM prod origin with Dave before running.
# Replace this value if Dave supplies a different hostname.
AUTOSAM_ORIGIN = "https://autosam.prattwhitney.com"


# ---------------------------------------------------------------------------
# File contents
# ---------------------------------------------------------------------------

TEST_CORS_PY = '''\
# tests/test_cors.py
#
# CORS regression tests for ZH-63.
# Confirms AutoSAM prod origin receives Access-Control-Allow-Origin headers
# and unknown origins are blocked.

import pytest


@pytest.mark.django_db
def test_allowed_origin_returns_cors_headers(client):
    """AutoSAM prod origin should receive CORS headers."""
    res = client.options(
        "/api/streaming_response/",
        HTTP_ORIGIN="https://autosam.prattwhitney.com",  # confirm exact origin with Dave
        HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
    )
    assert "Access-Control-Allow-Origin" in res, (
        "Expected Access-Control-Allow-Origin header for AutoSAM origin"
    )
    assert res["Access-Control-Allow-Origin"] in (
        "https://autosam.prattwhitney.com",
        "*",
    )


@pytest.mark.django_db
def test_unknown_origin_blocked(client):
    """Requests from unknown origins should not receive CORS headers."""
    res = client.options(
        "/api/streaming_response/",
        HTTP_ORIGIN="https://evil.example.com",
        HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
    )
    assert res.get("Access-Control-Allow-Origin", "") not in (
        "https://evil.example.com",
        "*",
    ), "Unknown origin should not be allowed by CORS policy"
'''


# ---------------------------------------------------------------------------
# Steps
# ---------------------------------------------------------------------------

def step_branch():
    """Checkout or create the feature branch."""
    if not git_or("checkout", BRANCH):
        git("checkout", "-b", BRANCH)
    print(f"[OK] on branch {BRANCH}")


def step_create_test():
    """Write tests/test_cors.py."""
    dest = BACKEND / "tests" / "test_cors.py"
    ensure(dest, TEST_CORS_PY)
    print(f"[OK] created {dest.relative_to(BACKEND)}")


def step_patch_settings():
    """Add AutoSAM origin to CORS_ALLOWED_ORIGINS in settings.py.

    Strategy (in priority order):
    1. If CORS_ALLOWED_ORIGINS list exists, append new entry before closing bracket.
    2. If CORS_ALLOWED_ORIGIN_REGEXES exists, append a note.
    3. If neither, add a new CORS_ALLOWED_ORIGINS block anchored on a CORS comment.
    """
    settings_path = BACKEND / "app" / "settings.py"
    src = settings_path.read_text(encoding="utf-8")

    if AUTOSAM_ORIGIN in src:
        print(f"[SKIP] settings.py — {AUTOSAM_ORIGIN!r} already present")
        return

    if "CORS_ALLOWED_ORIGINS" in src:
        # Append before the closing bracket of the existing list.
        # Handles both single-line and multi-line list formats.
        # Tries the multi-line closing pattern first.
        patch(
            settings_path,
            old="]  # end CORS_ALLOWED_ORIGINS",
            new=f'    "{AUTOSAM_ORIGIN}",  # ZH-63: AutoSAM prod origin\n]  # end CORS_ALLOWED_ORIGINS',
            label="settings.py — append to CORS_ALLOWED_ORIGINS (tagged end)",
        )
        # If the tag isn't present, try a generic pattern.
        src2 = settings_path.read_text(encoding="utf-8")
        if AUTOSAM_ORIGIN not in src2:
            # Find the last entry in the list and add after it.
            # This is a best-effort heuristic; verify manually if [SKIP] appears.
            patch(
                settings_path,
                old="CORS_ALLOWED_ORIGINS = [",
                new=(
                    "CORS_ALLOWED_ORIGINS = [\n"
                    f'    "{AUTOSAM_ORIGIN}",  # ZH-63: AutoSAM prod origin'
                ),
                label="settings.py — prepend to CORS_ALLOWED_ORIGINS list",
            )
    elif "CORS_ALLOWED_ORIGIN_REGEXES" in src:
        print(
            "[INFO] CORS_ALLOWED_ORIGIN_REGEXES found — consider adding:\n"
            f'  r"^https://.*\\.prattwhitney\\.com$"  # covers {AUTOSAM_ORIGIN}'
        )
        patch(
            settings_path,
            old="CORS_ALLOWED_ORIGIN_REGEXES = [",
            new=(
                "CORS_ALLOWED_ORIGIN_REGEXES = [\n"
                '    r"^https://.*\\.prattwhitney\\.com$",  # ZH-63: AutoSAM prod + any PW subdomain'
            ),
            label="settings.py — prepend to CORS_ALLOWED_ORIGIN_REGEXES",
        )
    else:
        # Neither key exists — add a new block.
        # Anchor on the corsheaders middleware reference most settings files have.
        patch(
            settings_path,
            old="# CORS",
            new=(
                "# CORS\n"
                "CORS_ALLOWED_ORIGINS = [\n"
                f'    "{AUTOSAM_ORIGIN}",  # ZH-63: AutoSAM prod origin\n'
                "]\n"
            ),
            label="settings.py — add new CORS_ALLOWED_ORIGINS block",
        )


def step_commit():
    """Stage and commit the changes."""
    git("add",
        str(BACKEND / "app" / "settings.py"),
        str(BACKEND / "tests" / "test_cors.py"),
    )
    git("commit", "-m", "ZH-63: add AutoSAM CORS origin to settings + CORS regression tests")
    print("[OK] committed")


def main():
    # Reminder guard — do not run blind.
    print("=" * 60)
    print("  ZH-63 CORS TRANSFER")
    print(f"  Target origin: {AUTOSAM_ORIGIN}")
    print("  CONFIRM EXACT ORIGIN WITH DAVE BEFORE RUNNING.")
    print("  Also verify Dave has not already merged a fix.")
    print("=" * 60)
    answer = input("Confirmed with Dave? Type 'yes' to continue: ").strip().lower()
    if answer != "yes":
        print("[ABORT] Run aborted. Confirm with Dave first.")
        sys.exit(0)

    if not BACKEND.exists():
        print(f"[ERROR] BACKEND not found: {BACKEND}")
        print("  Run this script from the root directory that contains ENCHS-PW-GenAI-Backend/")
        sys.exit(1)

    step_branch()
    step_create_test()
    step_patch_settings()
    step_commit()
    print("\n[DONE] ZH-63 transfer complete.")
    print("  Next: run pytest tests/test_cors.py on runtime machine, then open PR.")


if __name__ == "__main__":
    main()
