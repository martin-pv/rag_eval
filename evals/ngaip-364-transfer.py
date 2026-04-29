#!/usr/bin/env python3
"""NGAIP-364 Transfer Script -- cross-platform (Windows/macOS/Linux)
Usage: python ngaip-364-transfer.py  (run from repo root)

Produces 2 files:
  ENCHS-PW-GenAI-Backend/app_retrieval/evaluation/metrics/citation_accuracy.py  (replaces stub)
  ENCHS-PW-GenAI-Backend/tests/app_retrieval/test_metric_citation_accuracy.py   (new)

Safe to run twice -- all writes overwrite cleanly.
"""
import subprocess
from pathlib import Path

BRANCH = "ngaip-364-citation-accuracy-metric"
BASE_BRANCH = "main"
BACKEND = Path.cwd()


def git(*args):
    subprocess.run(["git", *args], check=True)


def git_or(*args):
    return subprocess.run(["git", *args], check=False).returncode == 0


def ensure_ticket_branch() -> None:
    """Create or switch to this ticket branch from current main."""
    print(f"[NGAIP-364] Preparing branch: {BRANCH}")
    git("fetch", "origin", BASE_BRANCH)
    git("switch", BASE_BRANCH)
    git("pull", "--ff-only", "origin", BASE_BRANCH)
    if not git_or("switch", "-c", BRANCH):
        git("switch", BRANCH)


def ensure(path: Path, content: str):
    """Write file, creating parent dirs. Idempotent -- overwrites if exists."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"  Created: {path}")


def touch(path: Path):
    """Create empty file (and parent dirs) if it does not exist."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.touch()
        print(f"  Touched: {path}")
    else:
        print(f"  Already exists: {path}")


def main():
    ensure_ticket_branch()

    print("[NGAIP-364] Creating directories...")
    for d in [
        BACKEND / "app_retrieval" / "evaluation" / "metrics",
        BACKEND / "tests" / "app_retrieval",
    ]:
        d.mkdir(parents=True, exist_ok=True)

    for init in [
        BACKEND / "app_retrieval" / "evaluation" / "__init__.py",
        BACKEND / "app_retrieval" / "evaluation" / "metrics" / "__init__.py",
        BACKEND / "tests" / "__init__.py",
        BACKEND / "tests" / "app_retrieval" / "__init__.py",
    ]:
        touch(init)

    # -------------------------------------------------------------------------
    # citation_accuracy.py  (replaces stub from NGAIP-363)
    # -------------------------------------------------------------------------
    ensure(
        BACKEND / "app_retrieval" / "evaluation" / "metrics" / "citation_accuracy.py",
        """\
from __future__ import annotations

from pathlib import Path

import yaml

from app_retrieval.evaluation.metrics.base import MetricModule

_spec_path = Path(__file__).parent.parent / "config" / "metrics_spec.yaml"

_DEFAULTS = {
    "precision": 0.8,
    "recall": 0.7,
    "hallucination_rate_max": 0.1,
}


def _load_thresholds() -> dict:
    \"\"\"Read citation thresholds from metrics_spec.yaml; fall back to defaults for TBD/missing values.\"\"\"
    try:
        spec = yaml.safe_load(_spec_path.read_text())
    except FileNotFoundError:
        return dict(_DEFAULTS)

    metrics_by_id = {m["id"]: m for m in spec.get("metrics", [])}

    def _float_or_default(metric_id: str, field: str, default: float) -> float:
        val = metrics_by_id.get(metric_id, {}).get("threshold", {}).get(field, "TBD")
        try:
            return float(val)
        except (ValueError, TypeError):
            return default

    return {
        "precision": _float_or_default("citation_precision", "pass", _DEFAULTS["precision"]),
        "recall": _float_or_default("citation_recall", "pass", _DEFAULTS["recall"]),
        "hallucination_rate_max": _float_or_default(
            "hallucination_rate", "pass", _DEFAULTS["hallucination_rate_max"]
        ),
    }


def _citation_overlap(
    model_asset_ids: list[str],
    gold_doc_ids: list[str],
    retrieved_asset_ids: list[str],
    tau: float = 0.5,
) -> tuple[float, float, float]:
    \"\"\"
    Returns (precision, recall, hallucination_rate).
    Hallucination: cited asset_id not in retrieved set AND not in gold.
    tau is reserved for future span-level overlap -- currently doc-level match.
    \"\"\"
    if not model_asset_ids:
        return 0.0, 0.0, 0.0

    gold_set = set(gold_doc_ids)
    retrieved_set = set(retrieved_asset_ids)

    tp = sum(1 for aid in model_asset_ids if aid in gold_set)
    precision = tp / len(model_asset_ids)
    recall = tp / len(gold_set) if gold_set else 0.0
    hallucinated = sum(
        1 for aid in model_asset_ids if aid not in retrieved_set and aid not in gold_set
    )
    hallucination_rate = hallucinated / len(model_asset_ids)

    return round(precision, 4), round(recall, 4), round(hallucination_rate, 4)


class CitationAccuracyMetric(MetricModule):
    name = "citation_accuracy"

    def __init__(self):
        thresholds = _load_thresholds()
        self.precision_threshold = thresholds["precision"]
        self.recall_threshold = thresholds["recall"]
        self.hallucination_rate_max = thresholds["hallucination_rate_max"]

    async def score(
        self,
        question: str,
        contexts: list[dict],
        answer: str,
        ground_truth: str | None = None,
        gold_doc_ids: list[str] | None = None,
        model_sources: list[dict] | None = None,
    ) -> dict:
        model_asset_ids = [s.get("asset_id", "") for s in (model_sources or [])]
        retrieved_asset_ids = [c.get("asset_id", "") for c in contexts]

        precision, recall, hallucination_rate = _citation_overlap(
            model_asset_ids=model_asset_ids,
            gold_doc_ids=gold_doc_ids or [],
            retrieved_asset_ids=retrieved_asset_ids,
        )

        return {
            "citation_precision": precision,
            "citation_recall": recall,
            "citation_hallucination_rate": hallucination_rate,
            "citation_precision_pass": precision >= self.precision_threshold,
            "citation_recall_pass": recall >= self.recall_threshold,
            "citation_hallucination_pass": hallucination_rate <= self.hallucination_rate_max,
            "metric_version": "1.0",
        }
""",
    )

    # -------------------------------------------------------------------------
    # test_metric_citation_accuracy.py
    # -------------------------------------------------------------------------
    ensure(
        BACKEND / "tests" / "app_retrieval" / "test_metric_citation_accuracy.py",
        """\
import pytest

from app_retrieval.evaluation.metrics.citation_accuracy import (
    CitationAccuracyMetric,
    _citation_overlap,
)


def test_precision_perfect():
    prec, _, _ = _citation_overlap(["a1"], ["a1"], ["a1"])
    assert prec == 1.0


def test_precision_wrong_page():
    # Model cites wrong page -- must fail precision (required by NGAIP-364 AC)
    prec, _, _ = _citation_overlap(["wrong_page"], ["correct_page"], ["correct_page"])
    assert prec == 0.0


def test_recall():
    _, recall, _ = _citation_overlap(["a1"], ["a1", "a2"], ["a1", "a2"])
    assert recall == 0.5  # found 1 of 2 gold docs


def test_hallucination_rate():
    _, _, hall = _citation_overlap(
        model_asset_ids=["ghost"],
        gold_doc_ids=["real"],
        retrieved_asset_ids=["real"],
    )
    assert hall == 1.0


def test_empty_model_sources():
    prec, recall, hall = _citation_overlap([], ["a1"], ["a1"])
    assert prec == recall == hall == 0.0


def test_no_hallucination_when_in_retrieved():
    # Asset is not in gold but IS in retrieved -- not a hallucination
    _, _, hall = _citation_overlap(
        model_asset_ids=["retrieved_only"],
        gold_doc_ids=["gold_doc"],
        retrieved_asset_ids=["retrieved_only"],
    )
    assert hall == 0.0


@pytest.mark.asyncio
async def test_metric_score_shape():
    metric = CitationAccuracyMetric()
    result = await metric.score(
        question="Where is X?",
        contexts=[{"asset_id": "doc1"}],
        answer="X is in doc1",
        gold_doc_ids=["doc1"],
        model_sources=[{"asset_id": "doc1"}],
    )
    assert "citation_precision" in result
    assert "citation_recall" in result
    assert "citation_hallucination_rate" in result
    assert "citation_precision_pass" in result
    assert "citation_recall_pass" in result
    assert "citation_hallucination_pass" in result
    assert result["metric_version"] == "1.0"
    assert result["citation_precision_pass"] is True


@pytest.mark.asyncio
async def test_metric_score_hallucination_fails():
    metric = CitationAccuracyMetric()
    result = await metric.score(
        question="Where is X?",
        contexts=[{"asset_id": "real_doc"}],
        answer="X is somewhere",
        gold_doc_ids=["real_doc"],
        model_sources=[{"asset_id": "made_up_doc"}],
    )
    assert result["citation_precision"] == 0.0
    assert result["citation_hallucination_rate"] == 1.0
    assert result["citation_precision_pass"] is False
    assert result["citation_hallucination_pass"] is False
""",
    )

    print("")
    print("[NGAIP-364] Done. Verify with:")
    print("  cd ENCHS-PW-GenAI-Backend")
    print("  pytest tests/app_retrieval/test_metric_citation_accuracy.py -v")
    print("  # Expect 8 tests passing, including test_precision_wrong_page (ticket AC)")


if __name__ == "__main__":
    main()
