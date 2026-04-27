#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(pwd)"
echo "[362-transfer] Starting transfer into: $REPO_ROOT"

# ---------------------------------------------------------------------------
# Create directories
# ---------------------------------------------------------------------------
echo "[362-transfer] Creating directories..."
mkdir -p "$REPO_ROOT/app_retrieval/evaluation/config"
mkdir -p "$REPO_ROOT/tests/app_retrieval"

# ---------------------------------------------------------------------------
# Package __init__ files (empty, idempotent)
# ---------------------------------------------------------------------------
touch "$REPO_ROOT/app_retrieval/evaluation/__init__.py"
touch "$REPO_ROOT/app_retrieval/evaluation/config/__init__.py"
touch "$REPO_ROOT/tests/app_retrieval/__init__.py"
echo "[362-transfer] Ensured: __init__.py files"

# ---------------------------------------------------------------------------
# app_retrieval/evaluation/config/gold_schema.py
# ---------------------------------------------------------------------------
cat > "$REPO_ROOT/app_retrieval/evaluation/config/gold_schema.py" << 'PYEOF'
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
PYEOF
echo "[362-transfer] Created: app_retrieval/evaluation/config/gold_schema.py"

# ---------------------------------------------------------------------------
# app_retrieval/evaluation/config/gold_schema.md
# ---------------------------------------------------------------------------
cat > "$REPO_ROOT/app_retrieval/evaluation/config/gold_schema.md" << 'PYEOF'
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
PYEOF
echo "[362-transfer] Created: app_retrieval/evaluation/config/gold_schema.md"

# ---------------------------------------------------------------------------
# app_retrieval/evaluation/config/ci_gold.jsonl
# ---------------------------------------------------------------------------
cat > "$REPO_ROOT/app_retrieval/evaluation/config/ci_gold.jsonl" << 'PYEOF'
{"question_id":"ci-001","question":"What is the maintenance interval for component X?","gold_answer":"Component X requires maintenance every 500 flight hours.","gold_doc_id":"ci-asset-001","difficulty":"easy","tags":["maintenance"]}
{"question_id":"ci-002","question":"What materials are approved for repair of section Y?","gold_answer":"Section Y repairs must use titanium alloy grade 5.","gold_doc_id":"ci-asset-002","difficulty":"medium","tags":["materials","repair"]}
PYEOF
echo "[362-transfer] Created: app_retrieval/evaluation/config/ci_gold.jsonl"

# ---------------------------------------------------------------------------
# app_retrieval/evaluation/gold_loader.py
# ---------------------------------------------------------------------------
cat > "$REPO_ROOT/app_retrieval/evaluation/gold_loader.py" << 'PYEOF'
from pathlib import Path

from app_retrieval.evaluation.config.gold_schema import GoldRow


def load_gold_file(path: str | Path) -> list[GoldRow]:
    """Load and validate a gold JSONL file. Raises ValueError on bad rows."""
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
PYEOF
echo "[362-transfer] Created: app_retrieval/evaluation/gold_loader.py"

# ---------------------------------------------------------------------------
# tests/app_retrieval/test_gold_loader.py
# ---------------------------------------------------------------------------
cat > "$REPO_ROOT/tests/app_retrieval/test_gold_loader.py" << 'PYEOF'
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
    bad.write_text(json.dumps({"question_id": "x", "question": "q", "gold_doc_id": "d"}) + "\n")
    with pytest.raises(ValueError, match="Invalid gold row at line 1"):
        load_gold_file(bad)


def test_load_gold_file_skips_blank_lines(tmp_path):
    fixture = tmp_path / "fixture.jsonl"
    row = {"question_id": "t-001", "question": "Q?", "gold_answer": "A.", "gold_doc_id": "d-001"}
    fixture.write_text("\n" + json.dumps(row) + "\n\n")
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
    fixture.write_text(json.dumps(row) + "\n")
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
    bad.write_text("not valid json at all\n")
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
    bad.write_text(json.dumps(row) + "\n")
    with pytest.raises(ValueError, match="Invalid gold row at line 1"):
        load_gold_file(bad)
PYEOF
echo "[362-transfer] Created: tests/app_retrieval/test_gold_loader.py"

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
echo ""
echo "[362-transfer] Complete. Verify with:"
echo "  pytest tests/app_retrieval/test_gold_loader.py -v"
echo ""
echo "  # Confirm CI fixture validates cleanly:"
echo "  python -c \""
echo "  from app_retrieval.evaluation.gold_loader import load_gold_file"
echo "  rows = load_gold_file('app_retrieval/evaluation/config/ci_gold.jsonl')"
echo "  assert len(rows) == 2"
echo "  print('OK:', [r.question_id for r in rows])"
echo "  \""
