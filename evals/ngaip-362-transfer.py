#!/usr/bin/env python3
# ngaip-362-transfer.py
# Transfers NGAIP-362 gold corpus dataset files to the runtime machine.
# Idempotent: safe to run multiple times.
# Run from: ENCHS-PW-GenAI-Backend/ project root on the target machine.
# Do NOT commit this script.
# Cross-platform replacement for ngaip-362-transfer.sh

import ast
import subprocess
from pathlib import Path


BRANCH = "ngaip-362-corpus-gold-dataset"
COMMIT_MESSAGE = "NGAIP-362: Apply transfer script changes"
BASE_BRANCH = "main-backup-for-mac-claude-repo-04-07-2026"


def git(*args):
    subprocess.run(["git", *args], check=True)


def git_or(*args):
    return subprocess.run(["git", *args], check=False).returncode == 0


def current_branch() -> str:
    return subprocess.check_output(
        ["git", "branch", "--show-current"],
        text=True,
    ).strip()


def ensure_ticket_branch() -> None:
    """Ensure this transfer runs on its local ticket branch; never push/publish."""
    print(f"[362-transfer] Preparing branch: {BRANCH} from local {BASE_BRANCH}")
    if current_branch() == BRANCH:
        print(f"[362-transfer] Already on ticket branch: {BRANCH}")
        return
    if git_or("rev-parse", "--verify", f"refs/heads/{BRANCH}"):
        git("switch", BRANCH)
        return
    git("switch", BASE_BRANCH)
    git("switch", "-c", BRANCH)

# ---------------------------------------------------------------------------
# Local commit helper (no push/publish)
# ---------------------------------------------------------------------------

def _path_from_join_expr(node: ast.AST) -> str | None:
    parts: list[str] = []
    cur = node
    while isinstance(cur, ast.BinOp) and isinstance(cur.op, ast.Div):
        right = cur.right
        if isinstance(right, ast.Constant) and isinstance(right.value, str):
            parts.append(right.value)
        else:
            return None
        cur = cur.left
    if isinstance(cur, ast.Name) and cur.id in {"BACKEND", "ROOT"}:
        return "/".join(reversed(parts))
    return None


def _transfer_paths_from_this_script() -> list[str]:
    tree = ast.parse(Path(__file__).read_text(encoding="utf-8"), filename=__file__)
    targets: set[str] = set()
    assigned_paths: dict[str, str] = {}
    writer_calls = {"ensure", "touch", "append_if_missing", "patch"}

    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        path = _path_from_join_expr(node.value)
        if not path:
            continue
        for target in node.targets:
            if isinstance(target, ast.Name):
                assigned_paths[target.id] = path.replace("\\", "/")

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name) and node.args and func.id in writer_calls:
            first_arg = node.args[0]
            if isinstance(first_arg, ast.Name):
                path = assigned_paths.get(first_arg.id)
            else:
                path = _path_from_join_expr(first_arg)
            if path:
                targets.add(path.replace("\\", "/"))
        elif isinstance(func, ast.Attribute) and func.attr == "write_text":
            receiver = func.value
            if isinstance(receiver, ast.Name):
                path = assigned_paths.get(receiver.id)
            else:
                path = _path_from_join_expr(receiver)
            if path:
                targets.add(path.replace("\\", "/"))

    return sorted(targets)


def commit_transfer_changes() -> None:
    repo_root = globals().get("BACKEND", globals().get("ROOT", Path.cwd()))
    paths = _transfer_paths_from_this_script()
    if not paths:
        print("[transfer] No generated paths found to commit.")
        return

    existing_paths = [p for p in paths if (repo_root / p).exists()]
    if not existing_paths:
        print("[transfer] No generated files exist to commit.")
        return

    print(f"[transfer] Staging {len(existing_paths)} generated file(s) for local commit...")
    git("add", "--", *existing_paths)
    staged = subprocess.run(
        ["git", "diff", "--cached", "--quiet", "--", *existing_paths],
        cwd=repo_root,
        check=False,
    )
    if staged.returncode == 0:
        print("[transfer] No changes to commit.")
        return
    git("commit", "-m", COMMIT_MESSAGE, "--", *existing_paths)
    print(f"[transfer] Created local commit: {COMMIT_MESSAGE}")

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
# Resolve CWD — script must be run from the backend project root
# (where manage.py lives).
# ---------------------------------------------------------------------------
ROOT = Path.cwd()

print(f"[362-transfer] Starting transfer into: {ROOT}")
ensure_ticket_branch()

# ---------------------------------------------------------------------------
# Create directories
# ---------------------------------------------------------------------------
print("[362-transfer] Creating directories...")
(ROOT / "app_retrieval" / "evaluation" / "config").mkdir(parents=True, exist_ok=True)
(ROOT / "tests" / "app_retrieval").mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Package __init__ files (empty, idempotent)
# ---------------------------------------------------------------------------
touch(ROOT / "app_retrieval" / "evaluation" / "__init__.py")
touch(ROOT / "app_retrieval" / "evaluation" / "config" / "__init__.py")
touch(ROOT / "tests" / "app_retrieval" / "__init__.py")
print("[362-transfer] Ensured: __init__.py files")

# ---------------------------------------------------------------------------
# app_retrieval/evaluation/config/gold_schema.py
# ---------------------------------------------------------------------------
GOLD_SCHEMA_PY = """\
from pydantic import BaseModel, ConfigDict
from typing import Literal, Optional


class GoldRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question_id: str
    question: str
    gold_answer: str
    gold_doc_id: str                                    # asset_id from Pratt-Backend
    gold_span_start: Optional[int] = None               # char offset in content_item text
    gold_span_end: Optional[int] = None
    gold_chunk_ids: Optional[list[str]] = None          # LanceDB chunk row keys (alternative to char spans)
    difficulty: Optional[Literal["easy", "medium", "hard"]] = None
    tags: Optional[list[str]] = None
"""

ensure(ROOT / "app_retrieval" / "evaluation" / "config" / "gold_schema.py", GOLD_SCHEMA_PY)
print("[362-transfer] Created: app_retrieval/evaluation/config/gold_schema.py")

# ---------------------------------------------------------------------------
# app_retrieval/evaluation/config/gold_schema.md
# ---------------------------------------------------------------------------
GOLD_SCHEMA_MD = """\
# Gold Dataset CSV Schema

Column specification for the external gold Q/A CSV (stored in the private GitHub gold repo per NGAIP-362 ACs).

| Column | Type | Required | Example | Notes |
|--------|------|----------|---------|-------|
| `question_id` | string | YES | `q-001` | Unique identifier. Use stable slug format. |
| `question` | string | YES | `What is the maintenance interval for the HPT blade?` | Natural-language question answerable from the corpus. |
| `gold_answer` | string | YES | `The HPT blade requires inspection every 3,000 cycles.` | Complete, self-contained reference answer. |
| `gold_doc_id` | string | YES | `asset-0a1b2c3d` | `asset_id` from Pratt-Backend (stable across ingestion). |
| `gold_span_start` | int | NO | `1240` | Character offset (0-based) in the content_item's raw text where the answer span begins. Omit if using chunk IDs. |
| `gold_span_end` | int | NO | `1312` | Character offset where the answer span ends (exclusive). Omit if using chunk IDs. |
| `gold_chunk_ids` | string (JSON array) | NO | `["chunk-abc","chunk-def"]` | LanceDB row keys covering the answer. Alternative to char offsets. |
| `difficulty` | string | NO | `easy` | One of: `easy`, `medium`, `hard`. |
| `tags` | string (JSON array) | NO | `["maintenance","HPT"]` | Free-form topic tags for filtering. |

## Notes

- Either `gold_span_start`/`gold_span_end` OR `gold_chunk_ids` should be populated for citation scoring (NGAIP-364). Both may be populated for redundancy.
- `gold_doc_id` must match the `asset_id` as stored in Pratt-Backend after ingestion through the production pipeline.
- The JSONL variant (used by `gold_loader.py` and CI fixtures) encodes `gold_chunk_ids` and `tags` as native JSON arrays rather than serialized strings.
"""

ensure(ROOT / "app_retrieval" / "evaluation" / "config" / "gold_schema.md", GOLD_SCHEMA_MD)
print("[362-transfer] Created: app_retrieval/evaluation/config/gold_schema.md")

# ---------------------------------------------------------------------------
# app_retrieval/evaluation/config/ci_gold.jsonl
# ---------------------------------------------------------------------------
CI_GOLD_JSONL = (
    '{"question_id":"ci-001","question":"What is the maintenance interval for component X?",'
    '"gold_answer":"Component X requires maintenance every 500 flight hours.",'
    '"gold_doc_id":"ci-asset-001","difficulty":"easy","tags":["maintenance"]}\n'
    '{"question_id":"ci-002","question":"What materials are approved for repair of section Y?",'
    '"gold_answer":"Section Y repairs must use titanium alloy grade 5.",'
    '"gold_doc_id":"ci-asset-002","difficulty":"medium","tags":["materials","repair"]}\n'
)

ensure(ROOT / "app_retrieval" / "evaluation" / "config" / "ci_gold.jsonl", CI_GOLD_JSONL)
print("[362-transfer] Created: app_retrieval/evaluation/config/ci_gold.jsonl")

# ---------------------------------------------------------------------------
# app_retrieval/evaluation/gold_loader.py
# ---------------------------------------------------------------------------
GOLD_LOADER_PY = """\
from pathlib import Path

from app_retrieval.evaluation.config.gold_schema import GoldRow


def load_gold_file(path: str | Path) -> list[GoldRow]:
    \"\"\"Load and validate a gold JSONL file. Raises ValueError on bad rows.\"\"\"
    rows = []
    with open(path) as f:
        for i, line in enumerate(f):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(GoldRow.model_validate_json(line))
            except Exception as e:
                raise ValueError(f"Invalid gold row at line {i + 1}: {e}") from e
    return rows
"""

ensure(ROOT / "app_retrieval" / "evaluation" / "gold_loader.py", GOLD_LOADER_PY)
print("[362-transfer] Created: app_retrieval/evaluation/gold_loader.py")

# ---------------------------------------------------------------------------
# tests/app_retrieval/test_gold_loader.py
# ---------------------------------------------------------------------------
TEST_GOLD_LOADER_PY = """\
import json
import pytest
from pathlib import Path

from app_retrieval.evaluation.gold_loader import load_gold_file
from app_retrieval.evaluation.config.gold_schema import GoldRow

CI_GOLD = Path(__file__).parents[2] / "app_retrieval/evaluation/config/ci_gold.jsonl"


def test_load_ci_gold_returns_two_rows():
    rows = load_gold_file(CI_GOLD)
    assert len(rows) == 2


def test_load_ci_gold_row_types():
    rows = load_gold_file(CI_GOLD)
    for row in rows:
        assert isinstance(row, GoldRow)


def test_load_ci_gold_required_fields():
    rows = load_gold_file(CI_GOLD)
    assert rows[0].question_id == "ci-001"
    assert rows[0].gold_doc_id == "ci-asset-001"
    assert rows[0].difficulty == "easy"
    assert rows[1].question_id == "ci-002"
    assert rows[1].difficulty == "medium"


def test_load_gold_file_raises_on_missing_required_field(tmp_path):
    bad = tmp_path / "bad.jsonl"
    # Missing gold_answer -- required field
    bad.write_text(json.dumps({"question_id": "x", "question": "q", "gold_doc_id": "d"}) + "\\n")
    with pytest.raises(ValueError, match="Invalid gold row at line 1"):
        load_gold_file(bad)


def test_load_gold_file_skips_blank_lines(tmp_path):
    fixture = tmp_path / "fixture.jsonl"
    row = {"question_id": "t-001", "question": "Q?", "gold_answer": "A.", "gold_doc_id": "d-001"}
    fixture.write_text("\\n" + json.dumps(row) + "\\n\\n")
    rows = load_gold_file(fixture)
    assert len(rows) == 1


def test_load_gold_file_with_optional_span_and_chunk_fields(tmp_path):
    fixture = tmp_path / "full.jsonl"
    row = {
        "question_id": "t-002",
        "question": "Q?",
        "gold_answer": "A.",
        "gold_doc_id": "d-002",
        "gold_span_start": 100,
        "gold_span_end": 200,
        "gold_chunk_ids": ["chunk-abc", "chunk-def"],
        "difficulty": "hard",
        "tags": ["materials", "repair"],
    }
    fixture.write_text(json.dumps(row) + "\\n")
    rows = load_gold_file(fixture)
    assert len(rows) == 1
    r = rows[0]
    assert r.gold_span_start == 100
    assert r.gold_span_end == 200
    assert r.gold_chunk_ids == ["chunk-abc", "chunk-def"]
    assert r.difficulty == "hard"
    assert r.tags == ["materials", "repair"]


def test_load_gold_file_raises_on_invalid_json_line(tmp_path):
    bad = tmp_path / "bad_json.jsonl"
    bad.write_text("not valid json at all\\n")
    with pytest.raises(ValueError, match="Invalid gold row at line 1"):
        load_gold_file(bad)


def test_load_gold_file_raises_on_extra_field(tmp_path):
    # extra="forbid" on GoldRow should reject unknown fields
    bad = tmp_path / "extra.jsonl"
    row = {
        "question_id": "t-003",
        "question": "Q?",
        "gold_answer": "A.",
        "gold_doc_id": "d-003",
        "unknown_field": "should be rejected",
    }
    bad.write_text(json.dumps(row) + "\\n")
    with pytest.raises(ValueError, match="Invalid gold row at line 1"):
        load_gold_file(bad)
"""

ensure(ROOT / "tests" / "app_retrieval" / "test_gold_loader.py", TEST_GOLD_LOADER_PY)
print("[362-transfer] Created: tests/app_retrieval/test_gold_loader.py")

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
commit_transfer_changes()

print("")
print("[362-transfer] Complete. Verify with:")
print("  pytest tests/app_retrieval/test_gold_loader.py -v")
print("")
print("  # Confirm CI fixture validates cleanly:")
print('  python -c "')
print("  from app_retrieval.evaluation.gold_loader import load_gold_file")
print("  rows = load_gold_file('app_retrieval/evaluation/config/ci_gold.jsonl')")
print("  assert len(rows) == 2")
print("  print('OK:', [r.question_id for r in rows])")
print('  "')
