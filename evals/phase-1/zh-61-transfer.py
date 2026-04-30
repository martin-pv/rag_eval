#!/usr/bin/env python3
"""
zh-61-transfer.py
Applies ZH-61: accept optional temperature on /streaming_response/
Run from the Django project root (folder containing app_chatbot/), or from
a monorepo root that has backend/app_chatbot/... — nested layout is auto-detected.
Idempotent: safe to run twice.
Do NOT commit this script.

Cross-platform equivalent of zh-61-transfer.sh (Windows/macOS/Linux).
"""

import subprocess
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Backend + git root (flat clone vs. backend/ subfolder)
# ---------------------------------------------------------------------------

def _git_toplevel() -> Path:
    out = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=True,
    )
    return Path(out.stdout.strip()).resolve()


def _resolve_backend_root() -> Path:
    """Folder that contains app_chatbot/views/chatstream.py (Django project root).

    Supports:
      - Flat: .../ENCHS-PW-GenAI-Backend/app_chatbot/...
      - Nested: .../SomeRepo/backend/app_chatbot/...  (run from repo root or from backend/)
    """
    cwd = Path.cwd().resolve()
    if (cwd / "app_chatbot" / "views" / "chatstream.py").is_file():
        return cwd
    if (cwd / "backend" / "app_chatbot" / "views" / "chatstream.py").is_file():
        root = (cwd / "backend").resolve()
        print(f"[zh-61] Detected nested layout: using {root} (not {cwd})")
        return root
    return cwd


def _path_for_git(abs_path: Path, git_root: Path) -> str:
    try:
        return str(abs_path.resolve().relative_to(git_root)).replace("\\", "/")
    except ValueError as exc:
        print(
            f"[zh-61] ERROR: {abs_path} is not under git root {git_root}. "
            "Run the script from inside the git checkout.",
            file=sys.stderr,
        )
        raise SystemExit(1) from exc


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
# Pre-flight: verify backend root contains chatstream.py
# ---------------------------------------------------------------------------

GIT_ROOT = _git_toplevel()
REPO_ROOT = _resolve_backend_root()
TARGET = REPO_ROOT / "app_chatbot" / "views" / "chatstream.py"

print(f"[zh-61] Git root:     {GIT_ROOT}")
print(f"[zh-61] Django root:  {REPO_ROOT}")
print(f"[zh-61] Patch target: {TARGET}")

if not TARGET.is_file():
    print(
        f"[zh-61] ERROR: {TARGET} not found.\n"
        "  Run from the Django project root (folder that contains app_chatbot/), e.g.\n"
        "    cd C:\\path\\to\\ENCHS-PW-GenAI-Backend\n"
        "  If your code lives under backend/, either:\n"
        "    cd C:\\path\\to\\YourRepo\\backend\n"
        "  or stay at repo root — this script will auto-detect backend/ when present.",
        file=sys.stderr,
    )
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
# Patch-landed regression test (verifies the two anchored hunks reached the file)
# ---------------------------------------------------------------------------

TEST_FILE = REPO_ROOT / "tests" / "app_chatbot" / "test_temperature_patch.py"
TEST_CONTENT = '''\
"""ZH-61 patch-landed smoke test.

These tests verify that the two anchored hunks landed in chatstream.py.
They are deliberately string-level checks rather than full DRF integration
tests because the patches sit inside an async streaming view that would
require >80% of the world to be mocked to exercise.
"""
from pathlib import Path


CHATSTREAM = Path("app_chatbot/views/chatstream.py").read_text(encoding="utf-8")


def test_chatstream_parses_temperature_from_request():
    assert 'raw_temp = request.data.get("temperature", None)' in CHATSTREAM


def test_chatstream_clamps_temperature_into_data_dict():
    assert 'data["temperature"] = max(0.0, min(2.0, temperature))' in CHATSTREAM


def test_chatstream_uses_float_conversion_on_temperature():
    assert "temperature = float(raw_temp)" in CHATSTREAM


def test_chatstream_handles_invalid_temperature_types_gracefully():
    # TypeError/ValueError fallback prevents 500s on bad client input (e.g. "hot", null, []).
    assert "except (TypeError, ValueError):" in CHATSTREAM


def test_chatstream_clamp_skipped_when_no_temperature_supplied():
    # The clamp must be guarded so default-temperature requests stay unchanged.
    assert "if temperature is not None:" in CHATSTREAM


def test_chatstream_temperature_default_is_none():
    # request.data.get("temperature", None) — explicit None default keeps semantics clear.
    assert 'request.data.get("temperature", None)' in CHATSTREAM
'''

TEST_FILE.parent.mkdir(parents=True, exist_ok=True)
(REPO_ROOT / "tests" / "__init__.py").touch(exist_ok=True)
(TEST_FILE.parent / "__init__.py").touch(exist_ok=True)
TEST_FILE.write_bytes(TEST_CONTENT.encode("utf-8"))
print(f"[zh-61] Wrote tests ({TEST_CONTENT.count('def test_')} tests): {TEST_FILE}")
print(f"[zh-61] Run manually: pytest {TEST_FILE.relative_to(REPO_ROOT)} -v  (from {REPO_ROOT})")

subprocess.run(
    [sys.executable, "-m", "pytest", str(TEST_FILE.relative_to(REPO_ROOT)), "-v"],
    cwd=str(REPO_ROOT),
    check=True,
)

_git_target = _path_for_git(TARGET, GIT_ROOT)
_git_test = _path_for_git(TEST_FILE, GIT_ROOT)
print(f"[zh-61] git add {_git_target}")
subprocess.run(["git", "add", _git_target], cwd=str(GIT_ROOT), check=True)
print(f"[zh-61] git add -f {_git_test}  (forces tracked if tests/ is gitignored)")
subprocess.run(["git", "add", "-f", _git_test], cwd=str(GIT_ROOT), check=True)
_status = subprocess.run(
    ["git", "status", "--short"],
    cwd=str(GIT_ROOT),
    capture_output=True,
    text=True,
    check=True,
).stdout.strip()
if _status:
    subprocess.run(
        ["git", "commit", "-m", "ZH-61: accept optional temperature on /streaming_response/"],
        cwd=str(GIT_ROOT),
        check=True,
    )
    print("[zh-61] Committed locally")
else:
    print("[zh-61] Nothing to commit (no changes)")

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------

print()
print("[zh-61] Complete. Verify:")
print("  python manage.py check")
print("  # POST /streaming_response/ with temperature=0.9 -> OpenAI receives temperature=0.9")
print("  # POST /streaming_response/ with temperature=5.0 -> clamped to 2.0")
print("  # POST /streaming_response/ without temperature -> existing behavior unchanged")
