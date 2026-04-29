"""ngaip-412-transfer.py — cross-platform transfer script (Windows/macOS/Linux).
Run from repo root: python ngaip-412-transfer.py

Produces:
  ENCHS-PW-GenAI-Backend/docs/rag_eval_adr.md
  ENCHS-PW-GenAI-Backend/notebooks/rag_eval_poc/__init__.py
  ENCHS-PW-GenAI-Backend/notebooks/rag_eval_poc/poc.ipynb
  ENCHS-PW-GenAI-Backend/tests/app_retrieval/test_eval_overlap_poc.py

Idempotent: safe to run multiple times.
"""
import ast
import json
import subprocess
from pathlib import Path

BRANCH = "ngaip-412-rag-eval-harness-poc"
COMMIT_MESSAGE = "NGAIP-412: Apply transfer script changes"
BASE_BRANCH = "main"
BACKEND = Path.cwd()


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
    print(f"[412-transfer] Preparing branch: {BRANCH} from local {BASE_BRANCH}")
    if current_branch() == BRANCH:
        print(f"[412-transfer] Already on ticket branch: {BRANCH}")
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


print(f"[412-transfer] Starting transfer into: {BACKEND}")
ensure_ticket_branch()

# ---------------------------------------------------------------------------
# 1. docs/rag_eval_adr.md
# ---------------------------------------------------------------------------
RAG_EVAL_ADR_MD = """\
# ADR: RAG Evaluation Harness Architecture

**Ticket:** NGAIP-412 (Design POC) → superseded by NGAIP-363 (production harness)
**Status:** Accepted — POC complete, merged to NGAIP-363
**Date:** 2026-04-27

---

## Context

We need a repeatable evaluation harness to measure RAG retrieval and generation quality against a gold corpus (NGAIP-362). This ADR records the design decisions made during the POC spike (NGAIP-412) that inform the production implementation in NGAIP-363.

---

## Data Flow

```
corpus (NGAIP-362 gold JSONL: ci_gold.jsonl)
  │
  ├─ load_questions()
  │     ↓
  │  [ { question, gold_spans, folder_ids }, ... ]
  │
  ├─ retriever adapter
  │     ├─ semantic  → search_folder_index()         [app_retrieval/data_assets/utils.py]
  │     ├─ keyword   → keyword_search_folder()        [app_retrieval/views/search.py]
  │     └─ hybrid    → semantic + keyword, deduplicated
  │           ↓
  │     retrieved_chunks: list[dict]   (keys: context, score, asset_id)
  │
  ├─ metric modules (one per question)
  │     ├─ context_relevancy   → RAGAS ContextRelevancy   (NGAIP-365)
  │     ├─ citation_accuracy   → custom overlap scorer      (NGAIP-364)
  │     └─ response_accuracy   → RAGAS ResponseRelevancy   (NGAIP-366)
  │           ↓
  │     per_question_scores: dict[str, float]
  │
  └─ reporters
        ├─ json_reporter → /tmp/rag_eval_output/report.json
        └─ csv_reporter  → /tmp/rag_eval_output/report.csv
```

---

## Decisions

### 1. In-process vs HTTP

**Decision:** In-process (same Django process, no HTTP)

**Rationale:** An HTTP approach would require auth tokens, network routing, and a running server. Since the harness is a management command, running evaluation in-process is simpler, faster, and avoids auth complexity. There is no performance benefit to HTTP isolation for a batch eval job.

**Alternatives rejected:** HTTP sidecar (too much auth overhead), Celery task (async not needed for a CLI eval run).

---

### 2. Metrics framework: RAGAS vs custom

**Decision:** RAGAS >= 0.2 for generation metrics; custom token-overlap scorer for retrieval recall

**Rationale:** RAGAS provides battle-tested implementations of ContextRelevancy and ResponseRelevancy that align with the metric spec (NGAIP-415). Writing these from scratch would duplicate work. The retrieval overlap metric (citation_accuracy) is domain-specific enough to warrant a custom scorer — it compares gold spans to retrieved chunk content rather than relying on LLM-as-judge.

**Alternatives rejected:** All-custom metrics (too much maintenance); all-RAGAS (RAGAS does not have a token-overlap retrieval metric that matches our gold-span format).

---

### 3. Runner interface: management command vs CLI script

**Decision:** `python manage.py rag_eval run --config <path>`

**Rationale:** Django management commands integrate with the project's existing settings, database connections, and async infrastructure. A standalone script would require reimporting settings and recreating the app context. Consistency with other management commands in the project.

**Alternatives rejected:** Standalone script (settings re-init complexity), FastAPI endpoint (overkill for a batch job, security surface).

---

### 4. Threshold source

**Decision:** Thresholds read from `metrics_spec.yaml` (produced by NGAIP-415)

**Rationale:** Hardcoding thresholds in code makes them invisible to non-engineers and hard to tune. Externalizing to a YAML config allows the team to update pass/fail criteria without code changes.

**Never hardcode metric thresholds in Python.**

---

## POC Scope (NGAIP-412)

This branch produces only:
- This ADR (`docs/rag_eval_adr.md`)
- A proof-of-concept notebook (`notebooks/rag_eval_poc/poc.ipynb`) with a synthetic 3-chunk corpus and one gold question
- One extracted unit test (`tests/app_retrieval/test_eval_overlap_poc.py`) proving the overlap scorer works on synthetic data

The full harness skeleton is in NGAIP-363. This branch does **not** touch `app_retrieval` production code.

---

## Note: Merged to NGAIP-363

This branch is archived after PR merge. The production implementation lives in `ngaip-363-rag-evaluation-harness`. The overlap scorer extracted here (`overlap_score`) will be replaced by the proper `citation_accuracy` metric module in NGAIP-364.
"""

ensure(BACKEND / "docs" / "rag_eval_adr.md", RAG_EVAL_ADR_MD)
print("[412-transfer] Created: docs/rag_eval_adr.md")

# ---------------------------------------------------------------------------
# 2. notebooks/rag_eval_poc/__init__.py
# ---------------------------------------------------------------------------
touch(BACKEND / "notebooks" / "rag_eval_poc" / "__init__.py")
print("[412-transfer] Created: notebooks/rag_eval_poc/__init__.py")

# ---------------------------------------------------------------------------
# 3. notebooks/rag_eval_poc/poc.ipynb  (built as dict, serialized via json.dumps)
# ---------------------------------------------------------------------------
notebook = {
    "nbformat": 4,
    "nbformat_minor": 5,
    "metadata": {
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3",
        },
        "language_info": {
            "name": "python",
            "version": "3.12.0",
        },
    },
    "cells": [
        {
            "cell_type": "markdown",
            "id": "a1b2c3d4-0001",
            "metadata": {},
            "source": [
                "# RAG Eval POC — superseded by NGAIP-363\n",
                "\n",
                "**Ticket:** NGAIP-412 (design spike)  \n",
                "**Purpose:** Prove out the token-overlap retrieval scorer on synthetic data.  \n",
                "**Do not use in production** — see `app_retrieval/evaluation/` in NGAIP-363 for the real harness.\n",
                "\n",
                "No live API calls are made in this notebook.",
            ],
        },
        {
            "cell_type": "markdown",
            "id": "a1b2c3d4-0002",
            "metadata": {},
            "source": [
                "## Synthetic Corpus — 3 fake chunks",
            ],
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "id": "a1b2c3d4-0003",
            "metadata": {},
            "outputs": [],
            "source": [
                "CHUNKS = [\n",
                "    {\"chunk_id\": \"c1\", \"asset_id\": \"asset-001\", \"context\": \"the quick brown fox jumps over the lazy dog\", \"score\": 0.92},\n",
                "    {\"chunk_id\": \"c2\", \"asset_id\": \"asset-002\", \"context\": \"engine oil pressure must not exceed 120 psi during takeoff\", \"score\": 0.71},\n",
                "    {\"chunk_id\": \"c3\", \"asset_id\": \"asset-003\", \"context\": \"maintenance interval is every 3000 flight hours\", \"score\": 0.55},\n",
                "]",
            ],
        },
        {
            "cell_type": "markdown",
            "id": "a1b2c3d4-0004",
            "metadata": {},
            "source": [
                "## Gold Question",
            ],
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "id": "a1b2c3d4-0005",
            "metadata": {},
            "outputs": [],
            "source": [
                "GOLD_QUESTION = {\n",
                "    \"question\": \"What is the quick brown fox known for?\",\n",
                "    \"gold_spans\": [\"quick brown fox jumps\"],\n",
                "    \"folder_ids\": [],\n",
                "}",
            ],
        },
        {
            "cell_type": "markdown",
            "id": "a1b2c3d4-0006",
            "metadata": {},
            "source": [
                "## overlap_score() — POC retrieval metric",
            ],
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "id": "a1b2c3d4-0007",
            "metadata": {},
            "outputs": [],
            "source": [
                "def overlap_score(gold_spans: list[str], chunks: list[dict], k: int = 3) -> float:\n",
                "    \"\"\"Token overlap between gold spans and top-k retrieved chunk content.\n",
                "    Will be replaced by citation_accuracy metric module in NGAIP-364.\n",
                "    \"\"\"\n",
                "    top_chunks_text = \" \".join(c[\"context\"] for c in chunks[:k])\n",
                "    top_tokens = set(top_chunks_text.lower().split())\n",
                "    gold_tokens = set(\" \".join(gold_spans).lower().split())\n",
                "    if not gold_tokens:\n",
                "        return 0.0\n",
                "    return len(gold_tokens & top_tokens) / len(gold_tokens)",
            ],
        },
        {
            "cell_type": "markdown",
            "id": "a1b2c3d4-0008",
            "metadata": {},
            "source": [
                "## Run scorer on gold question",
            ],
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "id": "a1b2c3d4-0009",
            "metadata": {},
            "outputs": [],
            "source": [
                "score = overlap_score(GOLD_QUESTION[\"gold_spans\"], CHUNKS, k=3)\n",
                "print(f\"overlap_score = {score:.3f}\")",
            ],
        },
        {
            "cell_type": "markdown",
            "id": "a1b2c3d4-0010",
            "metadata": {},
            "source": [
                "## Assertions",
            ],
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "id": "a1b2c3d4-0011",
            "metadata": {},
            "outputs": [],
            "source": [
                "assert score > 0, f\"Expected score > 0 when gold span is in retrieved chunks, got {score}\"\n",
                "\n",
                "noise_chunks = [\n",
                "    {\"chunk_id\": \"n1\", \"asset_id\": \"asset-noise\", \"context\": \"completely unrelated content here\", \"score\": 0.3},\n",
                "]\n",
                "noise_score = overlap_score(GOLD_QUESTION[\"gold_spans\"], noise_chunks, k=3)\n",
                "assert noise_score == 0.0, f\"Expected 0.0 on all-noise chunks, got {noise_score}\"\n",
                "\n",
                "print(\"All assertions passed.\")",
            ],
        },
        {
            "cell_type": "markdown",
            "id": "a1b2c3d4-0012",
            "metadata": {},
            "source": [
                "## Conclusion\n",
                "\n",
                "The `overlap_score()` function correctly scores retrieval against gold spans.\n",
                "\n",
                "**Next steps:** Production harness is in NGAIP-363 (`app_retrieval/evaluation/`).  \n",
                "`overlap_score` will be replaced by `citation_accuracy` metric module (NGAIP-364).  \n",
                "RAGAS generation metrics are stubbed in NGAIP-365/366.",
            ],
        },
    ],
}

notebook_path = BACKEND / "notebooks" / "rag_eval_poc" / "poc.ipynb"
notebook_path.parent.mkdir(parents=True, exist_ok=True)
notebook_path.write_text(json.dumps(notebook, indent=1), encoding="utf-8")
print("[412-transfer] Created: notebooks/rag_eval_poc/poc.ipynb")

# ---------------------------------------------------------------------------
# 4. tests/app_retrieval/test_eval_overlap_poc.py
# ---------------------------------------------------------------------------
TEST_OVERLAP_POC_PY = '''\
"""
POC unit test for token-overlap retrieval scorer.
overlap_score() will be replaced by citation_accuracy metric module in NGAIP-364.
"""


def overlap_score(gold_spans: list[str], chunks: list[dict], k: int = 3) -> float:
    """Token overlap between gold spans and top-k retrieved chunk content."""
    top_chunks_text = " ".join(c["context"] for c in chunks[:k])
    top_tokens = set(top_chunks_text.lower().split())
    gold_tokens = set(" ".join(gold_spans).lower().split())
    if not gold_tokens:
        return 0.0
    return len(gold_tokens & top_tokens) / len(gold_tokens)


def test_overlap_score_exact_match():
    chunks = [{"context": "the quick brown fox jumps"}]
    gold = ["quick brown fox"]
    assert overlap_score(gold, chunks) > 0.8


def test_overlap_score_no_match():
    chunks = [{"context": "completely unrelated content here"}]
    gold = ["quick brown fox"]
    assert overlap_score(gold, chunks) == 0.0
'''

ensure(
    BACKEND / "tests" / "app_retrieval" / "test_eval_overlap_poc.py",
    TEST_OVERLAP_POC_PY,
)
print("[412-transfer] Created: tests/app_retrieval/test_eval_overlap_poc.py")

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
commit_transfer_changes()

print("")
print("[412-transfer] Complete. Verify with:")
print("  pytest tests/app_retrieval/test_eval_overlap_poc.py -v")
