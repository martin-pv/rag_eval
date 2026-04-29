#!/usr/bin/env python3
"""NGAIP-363 Transfer Script — cross-platform (Windows/macOS/Linux)
Usage: python ngaip-363-transfer.py  (run from repo root)
"""
import ast
import subprocess
from pathlib import Path

BRANCH = "ngaip-363-rag-evaluation-harness"
BASE_BRANCH = "main-backup-for-mac-claude-repo-04-07-2026"
BACKEND = Path.cwd()


def read_text_compat(path: Path) -> str:
    """Read text from disk; supports UTF-8, BOM, and UTF-16 (common for Windows-saved files).

    requirements.txt saved as \"Unicode\" in Notepad is often UTF-16 LE with BOM (starts with 0xFF 0xFE).
    """
    if not path.exists():
        return ""
    raw = path.read_bytes()
    if not raw:
        return ""
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        return raw.decode("utf-16")
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw.decode("utf-8-sig")
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        try:
            return raw.decode("utf-16-le")
        except UnicodeDecodeError:
            try:
                return raw.decode("cp1252")
            except UnicodeDecodeError:
                return raw.decode("latin-1")


def git(*args):
    subprocess.run(["git", *args], check=True)


def git_or(*args):
    return subprocess.run(["git", *args], check=False).returncode == 0


def ensure_ticket_branch() -> None:
    """Create or switch to this ticket branch from the local backup branch."""
    print(f"[363-transfer] Preparing branch: {BRANCH} from local {BASE_BRANCH}")
    if git_or("switch", BRANCH):
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
    paths = _transfer_paths_from_this_script()
    if not paths:
        print("[transfer] No generated paths found to commit.")
        return

    existing_paths = [p for p in paths if (BACKEND / p).exists()]
    if not existing_paths:
        print("[transfer] No generated files exist to commit.")
        return

    print(f"[transfer] Staging {len(existing_paths)} generated file(s) for local commit...")
    git("add", "--", *existing_paths)
    staged = subprocess.run(
        ["git", "diff", "--cached", "--quiet", "--", *existing_paths],
        cwd=BACKEND,
        check=False,
    )
    if staged.returncode == 0:
        print("[transfer] No changes to commit.")
        return

    message = f"{BRANCH}: Apply transfer script changes"
    git("commit", "-m", message, "--", *existing_paths)
    print(f"[transfer] Created local commit: {message}")

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


def append_if_missing(path: Path, line: str):
    """Append line to file only if not already present (replaces grep -q guard).

    On first modification, rewrites the file as UTF-8 if it was UTF-16 / legacy-encoded.
    """
    text = read_text_compat(path)
    addition = line if line.endswith("\n") else line + "\n"
    if line.rstrip() not in text:
        path.parent.mkdir(parents=True, exist_ok=True)
        if not text:
            new_content = addition
        elif text.endswith("\n"):
            new_content = text + addition
        else:
            new_content = text + "\n" + addition
        path.write_text(new_content, encoding="utf-8")
        print(f"  Appended: {line.strip()}")
    else:
        print(f"  Already present: {line.strip()}")


def main():
    print(f"[363-transfer] Starting transfer into: {Path.cwd()}")
    ensure_ticket_branch()

    # -------------------------------------------------------------------------
    # requirements.txt -- append only if not already present
    # -------------------------------------------------------------------------
    print("[363-transfer] Patching requirements.txt...")
    req = BACKEND / "requirements.txt"
    append_if_missing(req, "ragas>=0.2.0")
    append_if_missing(req, "datasets>=2.14.0")

    # -------------------------------------------------------------------------
    # Create directories (mkdir -p equivalent -- Path.mkdir handles this)
    # -------------------------------------------------------------------------
    print("[363-transfer] Creating directories...")
    for d in [
        BACKEND / "app_retrieval" / "evaluation" / "metrics",
        BACKEND / "app_retrieval" / "evaluation" / "reporters",
        BACKEND / "app_retrieval" / "evaluation" / "config",
        BACKEND / "app_retrieval" / "management" / "commands",
        BACKEND / "tests" / "app_retrieval",
    ]:
        d.mkdir(parents=True, exist_ok=True)

    # -------------------------------------------------------------------------
    # Package __init__ files (empty)
    # -------------------------------------------------------------------------
    for init in [
        BACKEND / "app_retrieval" / "evaluation" / "__init__.py",
        BACKEND / "app_retrieval" / "evaluation" / "metrics" / "__init__.py",
        BACKEND / "app_retrieval" / "evaluation" / "reporters" / "__init__.py",
        BACKEND / "app_retrieval" / "management" / "__init__.py",
        BACKEND / "app_retrieval" / "management" / "commands" / "__init__.py",
        BACKEND / "tests" / "app_retrieval" / "__init__.py",
    ]:
        touch(init)
    print("[363-transfer] Ensured: __init__.py files")

    # -------------------------------------------------------------------------
    # evaluation/config.py
    # -------------------------------------------------------------------------
    ensure(
        BACKEND / "app_retrieval" / "evaluation" / "config.py",
        """\
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class EvalConfig(BaseModel):
    seed: int = 42
    folder_ids: list[int]
    retriever_type: Literal["semantic", "keyword", "hybrid"] = "semantic"
    top_k: int = 5
    model: str = "gpt-4o"
    gold_file: str
    output_dir: str = "evaluation/output"
    metrics: list[str] = Field(
        default=["context_relevancy", "citation_accuracy", "response_accuracy"]
    )
    # ID of a Django user to impersonate for keyword retrieval (which requires request.user).
    # None is valid for semantic-only runs.
    eval_user_id: int | None = None

    @model_validator(mode="after")
    def _require_user_for_keyword(self) -> "EvalConfig":
        if self.retriever_type in ("keyword", "hybrid") and self.eval_user_id is None:
            raise ValueError(
                f"eval_user_id is required when retriever_type is {self.retriever_type!r}"
            )
        return self
""",
    )

    # -------------------------------------------------------------------------
    # evaluation/retriever.py
    # -------------------------------------------------------------------------
    ensure(
        BACKEND / "app_retrieval" / "evaluation" / "retriever.py",
        '''\
"""Retriever adapters for the RAG evaluation harness.

Each adapter exposes a single async method `retrieve(query, folder, top_k) -> list[dict]`
so the runner can call them uniformly regardless of retriever type.

Wrappers call the real retrieval functions -- they do NOT copy their logic.
  SemanticRetriever  -> app_retrieval.data_assets.utils.search_folder_index  (async)
  KeywordRetriever   -> app_retrieval.views.search.keyword_search_folder      (async)
  HybridRetriever    -> both, merged by score descending

Note: keyword_search_folder requires an HttpRequest with a .user attribute.
We satisfy this with RequestFactory so no HTTP stack is involved.
"""
from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod

from django.test import RequestFactory


class BaseRetriever(ABC):
    @abstractmethod
    async def retrieve(self, query: str, folder, top_k: int) -> list[dict]:
        ...


class SemanticRetriever(BaseRetriever):
    async def retrieve(self, query: str, folder, top_k: int) -> list[dict]:
        from app_retrieval.data_assets.utils import search_folder_index

        return await search_folder_index(folder, query, top_k)


class KeywordRetriever(BaseRetriever):
    def __init__(self, eval_user=None) -> None:
        self._eval_user = eval_user

    async def retrieve(self, query: str, folder, top_k: int) -> list[dict]:
        from app_retrieval.views.search import keyword_search_folder

        request = RequestFactory().get("/")
        request.user = self._eval_user
        return await keyword_search_folder(
            request,
            query,
            folder,
            k=top_k,
        )


class HybridRetriever(BaseRetriever):
    def __init__(self, eval_user=None) -> None:
        self._semantic = SemanticRetriever()
        self._keyword = KeywordRetriever(eval_user=eval_user)

    async def retrieve(self, query: str, folder, top_k: int) -> list[dict]:
        semantic_results, keyword_results = await asyncio.gather(
            self._semantic.retrieve(query, folder, top_k),
            self._keyword.retrieve(query, folder, top_k),
        )
        # Merge and deduplicate by chunk pk, prefer higher score.
        seen: dict[int | str, dict] = {}
        for chunk in semantic_results + keyword_results:
            key = chunk.get("pk") or chunk.get("id") or id(chunk)
            if key not in seen or chunk.get("score", 0) > seen[key].get("score", 0):
                seen[key] = chunk
        merged = sorted(seen.values(), key=lambda c: c.get("score", 0), reverse=True)
        return merged[:top_k]


def build_retriever(retriever_type: str, eval_user=None) -> BaseRetriever:
    if retriever_type == "semantic":
        return SemanticRetriever()
    if retriever_type == "keyword":
        return KeywordRetriever(eval_user=eval_user)
    if retriever_type == "hybrid":
        return HybridRetriever(eval_user=eval_user)
    raise ValueError(f"Unknown retriever_type: {retriever_type!r}")
''',
    )

    # -------------------------------------------------------------------------
    # evaluation/metrics/base.py
    # -------------------------------------------------------------------------
    ensure(
        BACKEND / "app_retrieval" / "evaluation" / "metrics" / "base.py",
        """\
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
        \"\"\"Return a dict mapping metric name(s) to float scores.\"\"\"
        ...
""",
    )

    # -------------------------------------------------------------------------
    # evaluation/metrics/context_relevancy.py
    # -------------------------------------------------------------------------
    ensure(
        BACKEND / "app_retrieval" / "evaluation" / "metrics" / "context_relevancy.py",
        """\
\"\"\"Stub -- real implementation added in NGAIP-365.\"\"\"
from __future__ import annotations

from .base import MetricModule


class ContextRelevancyMetric(MetricModule):
    name = "context_relevancy"

    async def score(
        self,
        question: str,
        contexts: list[str],
        answer: str,
        ground_truth: str | None = None,
    ) -> dict:
        # TODO: NGAIP-365 -- implement via ragas ContextPrecision/ContextRecall
        return {"context_relevancy": 0.0}
""",
    )

    # -------------------------------------------------------------------------
    # evaluation/metrics/citation_accuracy.py
    # -------------------------------------------------------------------------
    ensure(
        BACKEND / "app_retrieval" / "evaluation" / "metrics" / "citation_accuracy.py",
        """\
\"\"\"Stub -- real implementation added in NGAIP-364.\"\"\"
from __future__ import annotations

from .base import MetricModule


class CitationAccuracyMetric(MetricModule):
    name = "citation_accuracy"

    async def score(
        self,
        question: str,
        contexts: list[str],
        answer: str,
        ground_truth: str | None = None,
    ) -> dict:
        # TODO: NGAIP-364 -- implement citation matching against context spans
        return {"citation_accuracy": 0.0}
""",
    )

    # -------------------------------------------------------------------------
    # evaluation/metrics/response_accuracy.py
    # -------------------------------------------------------------------------
    ensure(
        BACKEND / "app_retrieval" / "evaluation" / "metrics" / "response_accuracy.py",
        """\
\"\"\"Stub -- real implementation added in NGAIP-366.\"\"\"
from __future__ import annotations

from .base import MetricModule


class ResponseAccuracyMetric(MetricModule):
    name = "response_accuracy"

    async def score(
        self,
        question: str,
        contexts: list[str],
        answer: str,
        ground_truth: str | None = None,
    ) -> dict:
        # TODO: NGAIP-366 -- implement via ragas AnswerCorrectness / LLM-as-judge
        return {"response_accuracy": 0.0}
""",
    )

    # -------------------------------------------------------------------------
    # evaluation/reporters/json_reporter.py
    # -------------------------------------------------------------------------
    ensure(
        BACKEND / "app_retrieval" / "evaluation" / "reporters" / "json_reporter.py",
        """\
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from ..config import EvalConfig


class JsonReporter:
    def write(self, config: EvalConfig, results: list[dict], output_dir: Path) -> dict:
        metric_names = config.metrics
        aggregate: dict[str, float] = {}
        for name in metric_names:
            values = [r[name] for r in results if name in r]
            aggregate[name] = sum(values) / len(values) if values else 0.0

        report = {
            "config": config.model_dump(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "results": results,
            "aggregate_scores": aggregate,
        }
        out_path = output_dir / "report.json"
        out_path.write_text(json.dumps(report, indent=2))
        return report
""",
    )

    # -------------------------------------------------------------------------
    # evaluation/reporters/csv_reporter.py
    # -------------------------------------------------------------------------
    ensure(
        BACKEND / "app_retrieval" / "evaluation" / "reporters" / "csv_reporter.py",
        """\
from __future__ import annotations

import csv
from pathlib import Path

from ..config import EvalConfig


class CsvReporter:
    def write(self, config: EvalConfig, results: list[dict], output_dir: Path) -> None:
        if not results:
            return
        fieldnames = list(results[0].keys())
        out_path = output_dir / "report.csv"
        with out_path.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)
""",
    )

    # -------------------------------------------------------------------------
    # evaluation/runner.py
    # -------------------------------------------------------------------------
    ensure(
        BACKEND / "app_retrieval" / "evaluation" / "runner.py",
        """\
\"\"\"Core evaluation loop for the RAG evaluation harness (NGAIP-363).\"\"\"
from __future__ import annotations

import json
import random
from pathlib import Path

import numpy as np  # reserved for future metric implementations that use array math
import yaml

from .config import EvalConfig
from .metrics.citation_accuracy import CitationAccuracyMetric
from .metrics.context_relevancy import ContextRelevancyMetric
from .metrics.response_accuracy import ResponseAccuracyMetric
from .reporters.csv_reporter import CsvReporter
from .reporters.json_reporter import JsonReporter
from .retriever import build_retriever

_METRIC_REGISTRY = {
    "context_relevancy": ContextRelevancyMetric,
    "citation_accuracy": CitationAccuracyMetric,
    "response_accuracy": ResponseAccuracyMetric,
}


def load_config(path: str | Path) -> EvalConfig:
    raw = yaml.safe_load(Path(path).read_text())
    return EvalConfig(**raw)


def _load_gold(path: str | Path) -> list[dict]:
    lines = Path(path).read_text().splitlines()
    return [json.loads(line) for line in lines if line.strip()]


class EvalRunner:
    def __init__(self, config: EvalConfig) -> None:
        self.config = config

    async def run(self) -> dict:
        cfg = self.config
        # Seeds are scaffolding -- future steps (NGAIP-365+) will add gold-set sampling.
        random.seed(cfg.seed)
        np.random.seed(cfg.seed)

        eval_user = None
        if cfg.eval_user_id is not None:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            eval_user = await User.objects.aget(pk=cfg.eval_user_id)

        retriever = build_retriever(cfg.retriever_type, eval_user=eval_user)

        metric_instances = []
        for name in cfg.metrics:
            cls = _METRIC_REGISTRY.get(name)
            if cls is None:
                raise ValueError(f"Unknown metric: {name!r}")
            metric_instances.append(cls())

        gold_items = _load_gold(cfg.gold_file)

        folder = None
        if cfg.folder_ids:
            from app_retrieval.models import Folder
            folder = await Folder.objects.aget(pk=cfg.folder_ids[0])

        results = []
        for item in gold_items:
            question = item["question"]
            ground_truth = item.get("ground_truth")

            # Skip retrieval when no folder is configured (e.g., CI fixture runs).
            if folder is None:
                chunks = []
            else:
                chunks = await retriever.retrieve(question, folder, cfg.top_k)
            contexts = [c.get("text", "") for c in chunks]

            # Placeholder answer -- LLM call is outside this harness scope for NGAIP-363.
            answer = item.get("answer", "")

            row: dict = {"question": question}
            for metric in metric_instances:
                scores = await metric.score(question, contexts, answer, ground_truth)
                row.update(scores)
            results.append(row)

        output_dir = Path(cfg.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        report = JsonReporter().write(cfg, results, output_dir)
        CsvReporter().write(cfg, results, output_dir)

        return report
""",
    )

    # -------------------------------------------------------------------------
    # management/commands/rag_eval.py
    # -------------------------------------------------------------------------
    ensure(
        BACKEND / "app_retrieval" / "management" / "commands" / "rag_eval.py",
        """\
\"\"\"Management command: python manage.py rag_eval run --config <path>\"\"\"
from __future__ import annotations

import asyncio

from django.core.management.base import BaseCommand, CommandError

from app_retrieval.evaluation.runner import EvalRunner, load_config


class Command(BaseCommand):
    help = "Run the RAG evaluation harness"

    def add_arguments(self, parser):
        subparsers = parser.add_subparsers(dest="subcommand", required=True)
        run_parser = subparsers.add_parser("run", help="Execute an evaluation run")
        run_parser.add_argument(
            "--config",
            required=True,
            help="Path to YAML evaluation config file",
        )

    def handle(self, *args, **options):
        if options["subcommand"] != "run":
            raise CommandError(f"Unknown subcommand: {options['subcommand']}")

        config_path = options["config"]
        try:
            config = load_config(config_path)
        except Exception as exc:
            raise CommandError(f"Failed to load config: {exc}") from exc

        runner = EvalRunner(config)
        report = asyncio.run(runner.run())

        aggregate = report.get("aggregate_scores", {})
        self.stdout.write(self.style.SUCCESS("RAG evaluation complete."))
        for metric, score in aggregate.items():
            self.stdout.write(f"  {metric}: {score:.4f}")
        self.stdout.write(f"Reports written to: {config.output_dir}")
""",
    )

    # -------------------------------------------------------------------------
    # evaluation/config/eval_default.yaml
    # -------------------------------------------------------------------------
    ensure(
        BACKEND / "app_retrieval" / "evaluation" / "config" / "eval_default.yaml",
        """\
seed: 42
folder_ids: []
retriever_type: semantic
top_k: 5
model: gpt-4o
gold_file: app_retrieval/evaluation/config/ci_gold.jsonl
output_dir: /tmp/rag_eval_output
metrics:
  - context_relevancy
  - citation_accuracy
  - response_accuracy
eval_user_id: null
""",
    )

    # -------------------------------------------------------------------------
    # evaluation/config/eval_ci_fixture.yaml
    # -------------------------------------------------------------------------
    ensure(
        BACKEND / "app_retrieval" / "evaluation" / "config" / "eval_ci_fixture.yaml",
        """\
# CI fixture -- uses stub metrics, empty folder_ids, no real data.
seed: 42
folder_ids: []
retriever_type: semantic
top_k: 3
model: gpt-4o
gold_file: app_retrieval/evaluation/config/ci_gold.jsonl
output_dir: /tmp/rag_eval_output
metrics:
  - context_relevancy
  - citation_accuracy
  - response_accuracy
eval_user_id: null
""",
    )

    # -------------------------------------------------------------------------
    # evaluation/config/ci_gold.jsonl
    # -------------------------------------------------------------------------
    ensure(
        BACKEND / "app_retrieval" / "evaluation" / "config" / "ci_gold.jsonl",
        """\
{"question": "What is the standard inspection interval for a turbofan engine?", "answer": "The standard interval is defined in the maintenance manual.", "ground_truth": "Refer to the engine maintenance manual for the authoritative interval."}
{"question": "Which materials are approved for high-pressure compressor blade repair?", "answer": "Approved materials are listed in the approved parts list.", "ground_truth": "See the approved repair manual for the complete list of materials."}
""",
    )

    # -------------------------------------------------------------------------
    # tests/app_retrieval/test_eval_runner.py
    # -------------------------------------------------------------------------
    ensure(
        BACKEND / "tests" / "app_retrieval" / "test_eval_runner.py",
        '''\
"""Tests for the RAG evaluation harness (NGAIP-363).

Coverage:
  - Config validation: valid and invalid inputs
  - Retriever dispatch: correct adapter selected by retriever_type
  - Reporter output: JSON schema keys, CSV header row
  - Seeding reproducibility: same seed -> same order
  - EvalRunner.run(): end-to-end async integration (mocked retrieval)

These tests run in-process with Django\'s test infrastructure.
Real retrieval calls are mocked so no DB or vector store is needed.
"""
from __future__ import annotations

import csv
import json
import random
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from app_retrieval.evaluation.config import EvalConfig
from app_retrieval.evaluation.reporters.csv_reporter import CsvReporter
from app_retrieval.evaluation.reporters.json_reporter import JsonReporter
from app_retrieval.evaluation.retriever import build_retriever


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_config(**overrides) -> EvalConfig:
    defaults = {
        "folder_ids": [],
        "gold_file": "dummy.jsonl",
    }
    defaults.update(overrides)
    return EvalConfig(**defaults)


def _write_gold(path: Path, items: list[dict]) -> None:
    path.write_text("\\n".join(json.dumps(item) for item in items))


# ---------------------------------------------------------------------------
# Config validation
# ---------------------------------------------------------------------------

class TestEvalConfig:
    def test_valid_minimal_config(self):
        cfg = _make_config()
        assert cfg.seed == 42
        assert cfg.retriever_type == "semantic"
        assert cfg.top_k == 5
        assert cfg.metrics == ["context_relevancy", "citation_accuracy", "response_accuracy"]

    def test_invalid_retriever_type_raises(self):
        with pytest.raises(ValidationError):
            _make_config(retriever_type="invalid_type")

    def test_missing_gold_file_raises(self):
        with pytest.raises((ValidationError, TypeError)):
            EvalConfig(folder_ids=[])  # gold_file is required

    def test_missing_folder_ids_raises(self):
        with pytest.raises((ValidationError, TypeError)):
            EvalConfig(gold_file="x.jsonl")  # folder_ids is required

    def test_eval_user_id_defaults_to_none(self):
        cfg = _make_config()
        assert cfg.eval_user_id is None

    def test_keyword_without_eval_user_id_raises(self):
        with pytest.raises(ValidationError, match="eval_user_id is required"):
            _make_config(retriever_type="keyword", eval_user_id=None)

    def test_hybrid_without_eval_user_id_raises(self):
        with pytest.raises(ValidationError, match="eval_user_id is required"):
            _make_config(retriever_type="hybrid", eval_user_id=None)

    def test_keyword_with_eval_user_id_valid(self):
        cfg = _make_config(retriever_type="keyword", eval_user_id=1)
        assert cfg.retriever_type == "keyword"
        assert cfg.eval_user_id == 1

    def test_custom_values_preserved(self):
        cfg = _make_config(
            seed=99,
            top_k=10,
            model="gpt-4-turbo",
            retriever_type="hybrid",
            eval_user_id=7,
        )
        assert cfg.seed == 99
        assert cfg.top_k == 10
        assert cfg.model == "gpt-4-turbo"
        assert cfg.retriever_type == "hybrid"
        assert cfg.eval_user_id == 7


# ---------------------------------------------------------------------------
# Retriever dispatch
# ---------------------------------------------------------------------------

class TestRetrieverDispatch:
    def test_semantic_retriever_returned_for_semantic_type(self):
        from app_retrieval.evaluation.retriever import SemanticRetriever
        r = build_retriever("semantic")
        assert isinstance(r, SemanticRetriever)

    def test_keyword_retriever_returned_for_keyword_type(self):
        from app_retrieval.evaluation.retriever import KeywordRetriever
        r = build_retriever("keyword")
        assert isinstance(r, KeywordRetriever)

    def test_hybrid_retriever_returned_for_hybrid_type(self):
        from app_retrieval.evaluation.retriever import HybridRetriever
        r = build_retriever("hybrid")
        assert isinstance(r, HybridRetriever)

    def test_unknown_type_raises_value_error(self):
        with pytest.raises(ValueError, match="Unknown retriever_type"):
            build_retriever("bm25_plus")

    @pytest.mark.asyncio
    async def test_semantic_retriever_calls_search_folder_index(self):
        from app_retrieval.evaluation.retriever import SemanticRetriever

        fake_chunks = [{"pk": 1, "text": "chunk text", "score": 0.9}]
        with patch(
            "app_retrieval.data_assets.utils.search_folder_index",
            new_callable=AsyncMock,
            return_value=fake_chunks,
        ) as mock_fn:
            r = SemanticRetriever()
            result = await r.retrieve("test query", folder=MagicMock(), top_k=3)

        assert result == fake_chunks
        mock_fn.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_keyword_retriever_calls_keyword_search_folder(self):
        from app_retrieval.evaluation.retriever import KeywordRetriever

        fake_chunks = [{"pk": 2, "text": "keyword chunk", "score": 0.8}]
        mock_user = MagicMock()
        with patch(
            "app_retrieval.views.search.keyword_search_folder",
            new_callable=AsyncMock,
            return_value=fake_chunks,
        ) as mock_fn:
            r = KeywordRetriever(eval_user=mock_user)
            result = await r.retrieve("query", folder=MagicMock(), top_k=3)

        assert result == fake_chunks
        mock_fn.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_hybrid_retriever_merges_and_deduplicates(self):
        from app_retrieval.evaluation.retriever import HybridRetriever

        semantic_chunks = [
            {"pk": 1, "text": "chunk A", "score": 0.9},
            {"pk": 2, "text": "chunk B", "score": 0.7},
        ]
        keyword_chunks = [
            {"pk": 2, "text": "chunk B", "score": 0.6},  # duplicate -- lower score
            {"pk": 3, "text": "chunk C", "score": 0.5},
        ]

        r = HybridRetriever()
        with (
            patch.object(r._semantic, "retrieve", new=AsyncMock(return_value=semantic_chunks)),
            patch.object(r._keyword, "retrieve", new=AsyncMock(return_value=keyword_chunks)),
        ):
            result = await r.retrieve("query", folder=MagicMock(), top_k=10)

        pks = [c["pk"] for c in result]
        assert len(pks) == 3  # deduplicated
        assert 1 in pks and 2 in pks and 3 in pks
        # chunk B (pk=2) keeps the higher score (0.7 from semantic)
        chunk_b = next(c for c in result if c["pk"] == 2)
        assert chunk_b["score"] == 0.7


# ---------------------------------------------------------------------------
# Reporter output format
# ---------------------------------------------------------------------------

class TestReporters:
    def _sample_results(self) -> list[dict]:
        return [
            {"question": "Q1", "context_relevancy": 0.0, "citation_accuracy": 0.0, "response_accuracy": 0.0},
            {"question": "Q2", "context_relevancy": 0.0, "citation_accuracy": 0.0, "response_accuracy": 0.0},
        ]

    def test_json_reporter_required_keys_present(self, tmp_path):
        cfg = _make_config()
        results = self._sample_results()
        report = JsonReporter().write(cfg, results, tmp_path)

        assert "config" in report
        assert "timestamp" in report
        assert "results" in report
        assert "aggregate_scores" in report

    def test_json_reporter_writes_file(self, tmp_path):
        cfg = _make_config()
        JsonReporter().write(cfg, self._sample_results(), tmp_path)
        out = tmp_path / "report.json"
        assert out.exists()
        data = json.loads(out.read_text())
        assert "results" in data

    def test_json_reporter_aggregate_scores_match_metric_names(self, tmp_path):
        cfg = _make_config()
        report = JsonReporter().write(cfg, self._sample_results(), tmp_path)
        for metric in cfg.metrics:
            assert metric in report["aggregate_scores"]

    def test_csv_reporter_writes_header_row(self, tmp_path):
        cfg = _make_config()
        CsvReporter().write(cfg, self._sample_results(), tmp_path)
        out = tmp_path / "report.csv"
        assert out.exists()
        with out.open() as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
        assert "question" in fieldnames
        assert "context_relevancy" in fieldnames

    def test_csv_reporter_one_row_per_question(self, tmp_path):
        cfg = _make_config()
        results = self._sample_results()
        CsvReporter().write(cfg, results, tmp_path)
        out = tmp_path / "report.csv"
        with out.open() as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == len(results)

    def test_csv_reporter_empty_results_writes_nothing(self, tmp_path):
        cfg = _make_config()
        CsvReporter().write(cfg, [], tmp_path)
        out = tmp_path / "report.csv"
        assert not out.exists()


# ---------------------------------------------------------------------------
# Seeding reproducibility
# ---------------------------------------------------------------------------

class TestSeeding:
    def test_same_seed_produces_same_shuffle(self):
        items = list(range(20))

        random.seed(42)
        first = random.sample(items, len(items))

        random.seed(42)
        second = random.sample(items, len(items))

        assert first == second

    def test_different_seed_produces_different_shuffle(self):
        items = list(range(20))

        random.seed(42)
        first = random.sample(items, len(items))

        random.seed(99)
        second = random.sample(items, len(items))

        assert first != second


# ---------------------------------------------------------------------------
# EvalRunner end-to-end (async integration, mocked retrieval)
# ---------------------------------------------------------------------------

class TestEvalRunnerEndToEnd:
    @pytest.mark.asyncio
    async def test_run_produces_report_json_and_csv(self, tmp_path):
        """Full run() with mocked retrieval verifies the async chain is sound."""
        from app_retrieval.evaluation.runner import EvalRunner

        gold = [
            {"question": "Q1", "answer": "A1", "ground_truth": "GT1"},
            {"question": "Q2", "answer": "A2", "ground_truth": "GT2"},
        ]
        gold_file = tmp_path / "gold.jsonl"
        _write_gold(gold_file, gold)

        cfg = _make_config(
            gold_file=str(gold_file),
            output_dir=str(tmp_path / "out"),
            folder_ids=[],  # empty -> no retrieval call
        )
        runner = EvalRunner(cfg)
        report = await runner.run()

        assert "results" in report
        assert len(report["results"]) == 2
        assert "aggregate_scores" in report
        assert (tmp_path / "out" / "report.json").exists()
        assert (tmp_path / "out" / "report.csv").exists()

    @pytest.mark.asyncio
    async def test_run_skips_retrieval_when_no_folder(self, tmp_path):
        """When folder_ids is empty, retriever.retrieve() is never called."""
        from app_retrieval.evaluation.runner import EvalRunner

        gold = [{"question": "Q1", "answer": "A1"}]
        gold_file = tmp_path / "gold.jsonl"
        _write_gold(gold_file, gold)

        cfg = _make_config(
            gold_file=str(gold_file),
            output_dir=str(tmp_path / "out"),
            folder_ids=[],
        )
        runner = EvalRunner(cfg)

        fake_retriever = MagicMock()
        fake_retriever.retrieve = AsyncMock(return_value=[])

        with patch("app_retrieval.evaluation.runner.build_retriever", return_value=fake_retriever):
            await runner.run()

        fake_retriever.retrieve.assert_not_awaited()
''',
    )

    commit_transfer_changes()

    print("")
    print("[363-transfer] Complete. Verify with:")
    print("  cd backend")
    print("  pytest tests/app_retrieval/test_eval_runner.py -v")
    print("  python manage.py rag_eval run --config app_retrieval/evaluation/config/eval_ci_fixture.yaml")
    print("  ls /tmp/rag_eval_output/    # expect report.json  report.csv")
    print("  python -c \"import json; d=json.load(open('/tmp/rag_eval_output/report.json')); assert 'results' in d\"")


if __name__ == "__main__":
    main()
