"""
ngaip-365-transfer.py
Transfers NGAIP-365 context relevancy metric to the runtime machine.
Idempotent: safe to run multiple times.
Run from: backend/ project root on the target machine (same CWD as the .sh).
Cross-platform: Windows cmd.exe, macOS, Linux.
"""
import subprocess
from pathlib import Path


BRANCH = "ngaip-365-context-relevancy-metric"
BASE_BRANCH = "main"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def git(*args: str) -> None:
    subprocess.run(["git", *args], check=True)


def git_or(*args: str) -> bool:
    return subprocess.run(["git", *args], check=False).returncode == 0


def ensure_ticket_branch() -> None:
    """Create or switch to this ticket branch from current main."""
    print(f"[365-transfer] Preparing branch: {BRANCH}")
    git("fetch", "origin", BASE_BRANCH)
    git("switch", BASE_BRANCH)
    git("pull", "--ff-only", "origin", BASE_BRANCH)
    if not git_or("switch", "-c", BRANCH):
        git("switch", BRANCH)


def ensure(path: Path, content: str) -> None:
    """Write content to path, creating parent dirs as needed. Always overwrites."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def touch(path: Path) -> None:
    """Create an empty file (and parent dirs) if it does not exist."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text("", encoding="utf-8")


# ---------------------------------------------------------------------------
# Embedded file content
# ---------------------------------------------------------------------------

BASE_PY = '''\
from __future__ import annotations

from abc import ABC, abstractmethod


class MetricModule(ABC):
    name: str

    @abstractmethod
    async def score(
        self,
        question: str,
        contexts: list[str],
        answer: str,
        ground_truth: str | None = None,
    ) -> dict:
        """Return a dict mapping metric name(s) to float scores."""
        ...
'''

METRICS_SPEC_YAML = '''\
# metrics_spec.yaml — threshold stub pending NGAIP-415 sign-off
# Values here are placeholders based on the design spike (NGAIP-412 ADR).
# NGAIP-415 will replace these with calibrated, stakeholder-approved thresholds.
metrics:
  context_relevancy:
    threshold: 0.7
    description: "Fraction of gold-span tokens covered by top-k retrieved chunks"
    ticket: NGAIP-365
  citation_accuracy:
    threshold: 0.6
    description: "Token overlap between cited sources and gold answer spans"
    ticket: NGAIP-364
  response_accuracy:
    threshold: 0.7
    description: "Semantic similarity between generated answer and gold answer"
    ticket: NGAIP-366
'''

CONTEXT_RELEVANCY_PY = '''\
"""
Context relevancy metric — NGAIP-365.

Replaces the stub scaffolded by NGAIP-363. Uses token overlap between
gold spans and top-k retrieved chunk text as a fast, no-API retrieval
quality signal. Threshold loaded from metrics_spec.yaml (NGAIP-415).
"""
from __future__ import annotations

from pathlib import Path

import yaml

from app_retrieval.evaluation.metrics.base import MetricModule

_SPEC_PATH = Path(__file__).parent.parent / "config" / "metrics_spec.yaml"


def _load_threshold() -> float:
    """Read threshold from metrics_spec.yaml.

    Handles both formats:
      - List format (NGAIP-415): metrics is a list of dicts with \'id\' keys
      - Dict format (legacy stub): metrics is keyed by metric name
    Falls back to 0.7 when value is TBD or missing.
    """
    import re as _re
    try:
        spec = yaml.safe_load(_SPEC_PATH.read_text())
    except FileNotFoundError:
        return 0.7
    metrics = spec.get("metrics", {})
    if isinstance(metrics, list):
        for entry in metrics:
            if entry.get("id") in ("context_relevancy_at_k", "context_relevancy"):
                val = str(entry.get("threshold", {}).get("pass", "TBD"))
                m = _re.search(r"[\\d.]+", val)
                return float(m.group()) if m else 0.7
        return 0.7
    try:
        return float(metrics.get("context_relevancy", {}).get("threshold", 0.7))
    except (ValueError, TypeError):
        return 0.7


def _token_overlap(gold_spans: list[str], chunks: list[dict], k: int) -> float:
    """Fraction of gold-span tokens covered by top-k retrieved chunk text."""
    top_text = " ".join(c.get("context", "") for c in chunks[:k])
    top_tokens = set(top_text.lower().split())
    gold_tokens = set(" ".join(gold_spans).lower().split())
    if not gold_tokens:
        return 0.0
    return len(gold_tokens & top_tokens) / len(gold_tokens)


class ContextRelevancyMetric(MetricModule):
    name = "context_relevancy"

    def __init__(self, k: int = 5) -> None:
        self.k = k
        self.threshold = _load_threshold()

    async def score(
        self,
        question: str,
        contexts: list[dict],  # raw chunk dicts: {context, score, asset_id, ...}
        answer: str,
        ground_truth: str | None = None,
        gold_spans: list[str] | None = None,
    ) -> dict:
        """Score retrieval quality as token overlap between gold spans and retrieved chunks.

        Overrides base-class signature to accept list[dict] instead of list[str]
        so the harness can pass raw retriever output without an intermediate reshape.
        gold_spans come from the gold JSONL (NGAIP-362); answer/ground_truth are
        unused by this metric but kept for interface consistency.
        """
        overlap = _token_overlap(gold_spans or [], contexts, self.k)
        return {
            "context_relevancy": round(overlap, 4),
            "context_relevancy_threshold": self.threshold,
            "context_relevancy_pass": overlap >= self.threshold,
            "metric_version": "1.0",
        }
'''

TEST_CONTEXT_RELEVANCY_PY = '''\
"""
Tests for ContextRelevancyMetric and _token_overlap helper — NGAIP-365.

Validation is agent-only (no live Django/DB setup needed).
All tests use in-process synthetic data; no API calls made.
"""
import pytest

from app_retrieval.evaluation.metrics.context_relevancy import (
    ContextRelevancyMetric,
    _token_overlap,
)


# ---------------------------------------------------------------------------
# _token_overlap — unit tests
# ---------------------------------------------------------------------------

def test_token_overlap_exact_match():
    gold = ["quick brown fox jumps"]
    chunks = [{"context": "the quick brown fox jumps over the lazy dog"}]
    assert _token_overlap(gold, chunks, k=1) > 0.8


def test_token_overlap_no_match():
    gold = ["quick brown fox"]
    chunks = [{"context": "completely unrelated content"}]
    assert _token_overlap(gold, chunks, k=1) == 0.0


def test_token_overlap_empty_gold():
    assert _token_overlap([], [{"context": "anything here"}], k=1) == 0.0


def test_token_overlap_empty_chunks():
    assert _token_overlap(["quick brown fox"], [], k=3) == 0.0


def test_token_overlap_top_k_respected():
    """k=1 misses the match in chunk[1]; k=2 finds it."""
    gold = ["token_a"]
    chunks = [
        {"context": "noise noise noise"},
        {"context": "token_a is here"},
    ]
    assert _token_overlap(gold, chunks, k=1) == 0.0
    assert _token_overlap(gold, chunks, k=2) > 0.0


def test_token_overlap_case_insensitive():
    gold = ["Quick Brown Fox"]
    chunks = [{"context": "quick brown fox"}]
    assert _token_overlap(gold, chunks, k=1) == 1.0


def test_token_overlap_multiple_gold_spans():
    gold = ["fox jumps", "over dog"]
    chunks = [{"context": "fox jumps over dog"}]
    assert _token_overlap(gold, chunks, k=1) == 1.0


def test_token_overlap_partial():
    gold = ["quick brown elephant"]   # "elephant" not in chunk
    chunks = [{"context": "the quick brown fox"}]
    score = _token_overlap(gold, chunks, k=1)
    assert 0.0 < score < 1.0


def test_token_overlap_missing_context_key():
    """Chunks without \'context\' key are treated as empty string — no crash."""
    gold = ["quick brown fox"]
    chunks = [{"score": 0.9, "asset_id": "a1"}]
    assert _token_overlap(gold, chunks, k=1) == 0.0


# ---------------------------------------------------------------------------
# ContextRelevancyMetric — integration-style tests (no live API)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_metric_score_returns_required_keys():
    metric = ContextRelevancyMetric(k=3)
    result = await metric.score(
        question="What is X?",
        contexts=[{"context": "X is a thing"}],
        answer="X is a thing",
        gold_spans=["X is"],
    )
    assert "context_relevancy" in result
    assert "context_relevancy_threshold" in result
    assert "context_relevancy_pass" in result
    assert "metric_version" in result


@pytest.mark.asyncio
async def test_metric_score_pass_when_above_threshold():
    metric = ContextRelevancyMetric(k=3)
    result = await metric.score(
        question="Q",
        contexts=[{"context": "engine oil pressure limit takeoff"}],
        answer="A",
        gold_spans=["engine oil pressure limit takeoff"],
    )
    assert result["context_relevancy"] == 1.0
    assert result["context_relevancy_pass"] is True


@pytest.mark.asyncio
async def test_metric_score_fail_when_below_threshold():
    metric = ContextRelevancyMetric(k=3)
    result = await metric.score(
        question="Q",
        contexts=[{"context": "completely unrelated text"}],
        answer="A",
        gold_spans=["engine oil pressure limit takeoff"],
    )
    assert result["context_relevancy"] == 0.0
    assert result["context_relevancy_pass"] is False


@pytest.mark.asyncio
async def test_metric_score_none_gold_spans():
    """gold_spans=None defaults to empty list -> score 0.0."""
    metric = ContextRelevancyMetric(k=3)
    result = await metric.score(
        question="Q",
        contexts=[{"context": "anything"}],
        answer="A",
        gold_spans=None,
    )
    assert result["context_relevancy"] == 0.0


@pytest.mark.asyncio
async def test_metric_name():
    assert ContextRelevancyMetric.name == "context_relevancy"


@pytest.mark.asyncio
async def test_metric_threshold_loaded():
    """Threshold should be the value from metrics_spec.yaml (0.7)."""
    metric = ContextRelevancyMetric()
    assert metric.threshold == pytest.approx(0.7)


@pytest.mark.asyncio
async def test_metric_score_is_rounded():
    """Score is rounded to 4 decimal places."""
    metric = ContextRelevancyMetric(k=1)
    result = await metric.score(
        question="Q",
        contexts=[{"context": "a b c d e"}],
        answer="A",
        gold_spans=["a b c"],
    )
    assert isinstance(result["context_relevancy"], float)
    assert len(str(result["context_relevancy"]).split(".")[-1]) <= 4
'''


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    # The bash script sets REPO_ROOT="$(pwd)" and expects to be run from
    # inside the backend/ directory (same as manage.py lives).
    BACKEND = Path.cwd()
    print(f"[365-transfer] Starting transfer into: {BACKEND}")
    ensure_ticket_branch()

    # -----------------------------------------------------------------------
    # Directories
    # -----------------------------------------------------------------------
    (BACKEND / "app_retrieval" / "evaluation" / "metrics").mkdir(parents=True, exist_ok=True)
    (BACKEND / "app_retrieval" / "evaluation" / "config").mkdir(parents=True, exist_ok=True)
    (BACKEND / "tests" / "app_retrieval").mkdir(parents=True, exist_ok=True)

    # -----------------------------------------------------------------------
    # 1. app_retrieval/evaluation/__init__.py
    # -----------------------------------------------------------------------
    touch(BACKEND / "app_retrieval" / "evaluation" / "__init__.py")
    print("[365-transfer] Ensured: app_retrieval/evaluation/__init__.py")

    # -----------------------------------------------------------------------
    # 2. app_retrieval/evaluation/metrics/__init__.py
    # -----------------------------------------------------------------------
    touch(BACKEND / "app_retrieval" / "evaluation" / "metrics" / "__init__.py")
    print("[365-transfer] Ensured: app_retrieval/evaluation/metrics/__init__.py")

    # -----------------------------------------------------------------------
    # 3. app_retrieval/evaluation/metrics/base.py
    #    (Skip if 363 harness already wrote it)
    # -----------------------------------------------------------------------
    base_path = BACKEND / "app_retrieval" / "evaluation" / "metrics" / "base.py"
    if not base_path.exists():
        ensure(base_path, BASE_PY)
        print("[365-transfer] Created: app_retrieval/evaluation/metrics/base.py")
    else:
        print("[365-transfer] Skipped: base.py already exists (from 363)")

    # -----------------------------------------------------------------------
    # 4. app_retrieval/evaluation/config/metrics_spec.yaml
    #    (Skip if 415 already wrote it)
    # -----------------------------------------------------------------------
    spec_path = BACKEND / "app_retrieval" / "evaluation" / "config" / "metrics_spec.yaml"
    if not spec_path.exists():
        ensure(spec_path, METRICS_SPEC_YAML)
        print("[365-transfer] Created: app_retrieval/evaluation/config/metrics_spec.yaml")
    else:
        print("[365-transfer] Skipped: metrics_spec.yaml already exists (from 415)")

    # -----------------------------------------------------------------------
    # 5. app_retrieval/evaluation/metrics/context_relevancy.py  (always write)
    # -----------------------------------------------------------------------
    ensure(
        BACKEND / "app_retrieval" / "evaluation" / "metrics" / "context_relevancy.py",
        CONTEXT_RELEVANCY_PY,
    )
    print("[365-transfer] Created: app_retrieval/evaluation/metrics/context_relevancy.py")

    # -----------------------------------------------------------------------
    # 6. tests/app_retrieval/__init__.py
    # -----------------------------------------------------------------------
    touch(BACKEND / "tests" / "app_retrieval" / "__init__.py")
    print("[365-transfer] Ensured: tests/app_retrieval/__init__.py")

    # -----------------------------------------------------------------------
    # 7. tests/app_retrieval/test_metric_context_relevancy.py  (always write)
    # -----------------------------------------------------------------------
    ensure(
        BACKEND / "tests" / "app_retrieval" / "test_metric_context_relevancy.py",
        TEST_CONTEXT_RELEVANCY_PY,
    )
    print("[365-transfer] Created: tests/app_retrieval/test_metric_context_relevancy.py")

    # -----------------------------------------------------------------------
    # Done
    # -----------------------------------------------------------------------
    print()
    print("[365-transfer] Complete. Verify with:")
    print("  cd backend")
    print("  pytest tests/app_retrieval/test_metric_context_relevancy.py -v")
    print(
        "  python -c \"from app_retrieval.evaluation.metrics.context_relevancy import "
        "ContextRelevancyMetric; m = ContextRelevancyMetric(); "
        "print('threshold:', m.threshold); assert m.name == 'context_relevancy'; print('OK')\""
    )


if __name__ == "__main__":
    main()
