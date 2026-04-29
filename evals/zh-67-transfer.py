#!/usr/bin/env python3
"""
zh-67-transfer.py -- ZH-67 Transfer Script
Usage: python zh-67-transfer.py from the root of ENCHS-PW-GenAI-Backend

What this does:
  1. Checks out (or creates) branch zh-67-structured-json-streaming
  2. Applies one-line fix: passes structured_output to get_default_data in chatstream.py
  3. Adds regression tests for get_default_data structured_output behavior

Safe to run twice -- patch is idempotent (only changes the line if it matches).

Cross-platform equivalent of zh-67-transfer.sh (Windows/macOS/Linux).
"""

import subprocess
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def git(*args: str) -> None:
    """Run a git command, raising on non-zero exit."""
    subprocess.run(["git", *args], check=True)


def git_or(*args: str) -> bool:
    """Run a git command, returning True on success."""
    return subprocess.run(["git", *args]).returncode == 0


def touch(path: Path) -> None:
    """Create path (and parents) if it doesn't exist."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch()


def ensure(path: Path, content: str) -> None:
    """Write content to path, creating parent directories as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def patch(path: Path, old: str, new: str, label: str = "patch") -> None:
    """Replace first occurrence of old with new in path. Skip if old not found."""
    src = path.read_text(encoding="utf-8")
    if old not in src:
        print(f"[SKIP] {label}")
        return
    path.write_text(src.replace(old, new, 1), encoding="utf-8")
    print(f"[OK] {label}")


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BRANCH = "zh-67-structured-json-streaming"
TARGET = Path("app_chatbot/views/chatstream.py")

OLD_LINE = "data = get_default_data(stream=True)"
NEW_LINE = "data = get_default_data(stream=True, structured_output=structured_output)"

# ---------------------------------------------------------------------------
# Guard: require a clean working tree before touching git state
# ---------------------------------------------------------------------------

result = subprocess.run(["git", "diff-index", "--quiet", "HEAD", "--"])
if result.returncode != 0:
    print(
        "[ZH-67] ERROR: working tree is dirty. Commit or stash changes first.",
        file=sys.stderr,
    )
    sys.exit(1)

# ---------------------------------------------------------------------------
# Step 1: Checkout (or create) branch
# ---------------------------------------------------------------------------

print(f"[ZH-67] Checking out branch {BRANCH}...")
git("checkout", "main")
git("pull", "origin", "main")

# Try to create; fall back to checkout if it already exists
if not git_or("checkout", "-b", BRANCH):
    git("checkout", BRANCH)

# ---------------------------------------------------------------------------
# Step 2: One-line fix in app_chatbot/views/chatstream.py
# ---------------------------------------------------------------------------

print("[ZH-67] Patching chatstream.py...")

src = TARGET.read_text(encoding="utf-8")

if OLD_LINE not in src:
    print(
        f"[ZH-67] WARNING: expected pattern not found in {TARGET} -- "
        "already patched or file changed.",
        file=sys.stderr,
    )
else:
    TARGET.write_text(src.replace(OLD_LINE, NEW_LINE, 1), encoding="utf-8")
    print("[ZH-67] Patched: get_default_data now receives structured_output=structured_output")

# Verify patch landed
patched_src = TARGET.read_text(encoding="utf-8")
verified = any(
    "get_default_data" in line and "structured_output" in line
    for line in patched_src.splitlines()
)
if verified:
    print("[ZH-67] Patch verified.")
else:
    print("[ZH-67] ERROR: patch did not apply.", file=sys.stderr)
    sys.exit(1)

# ---------------------------------------------------------------------------
# Step 3: Regression tests
# ---------------------------------------------------------------------------

print("[ZH-67] Writing tests...")

Path("tests/app_chatbot").mkdir(parents=True, exist_ok=True)
touch(Path("tests/app_chatbot/__init__.py"))

TEST_FILE = Path("tests/app_chatbot/test_utils.py")

TEST_CONTENT = '''\
"""
Unit tests for app_chatbot.utils.get_default_data.

Regression coverage for ZH-67: structured_output must propagate to
response_format in the OpenAI payload when requested.
"""
import pytest

from app_chatbot.utils import get_default_data


class TestGetDefaultDataStructuredOutput:
    def test_structured_output_true_sets_json_object_format(self):
        data = get_default_data(stream=True, structured_output=True)
        assert data["response_format"] == {"type": "json_object"}

    def test_structured_output_false_omits_response_format(self):
        data = get_default_data(stream=True, structured_output=False)
        assert "response_format" not in data

    def test_structured_output_default_omits_response_format(self):
        data = get_default_data(stream=True)
        assert "response_format" not in data

    def test_stream_flag_preserved_when_structured_output_true(self):
        data = get_default_data(stream=True, structured_output=True)
        assert data["stream"] is True

    def test_stream_false_preserved_when_structured_output_true(self):
        data = get_default_data(stream=False, structured_output=True)
        assert data["stream"] is False
        assert data["response_format"] == {"type": "json_object"}

    def test_required_openai_keys_present(self):
        data = get_default_data(stream=True)
        for key in ("messages", "max_tokens", "temperature", "stream"):
            assert key in data
'''

if TEST_FILE.exists():
    print(f"[ZH-67] {TEST_FILE} already exists, skipping.")
else:
    TEST_FILE.write_text(TEST_CONTENT, encoding="utf-8")
    print(f"[ZH-67] Wrote: {TEST_FILE}")


def run_pytest() -> None:
    """Run generated ZH-67 tests before staging."""
    subprocess.run([sys.executable, "-m", "pytest", "tests/app_chatbot/test_utils.py", "-v"], check=True)


def stage_changes() -> None:
    """Stage source changes and force-add generated tests."""
    git("add", str(TARGET))
    git("add", "-f", str(TEST_FILE))
    print("[ZH-67] Staged chatstream.py and force-added generated tests")

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------

run_pytest()
stage_changes()

print("[ZH-67] Done. Verify with:")
print("  pytest tests/app_chatbot/test_utils.py -v")
print()
print("  # Manual smoke test (structured_output=true -> response_format in payload):")
print("  # POST to /api/chatbot/stream/ with structured_output=true and check OpenAI payload")
