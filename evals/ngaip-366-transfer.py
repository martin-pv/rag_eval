"""ngaip-366-transfer.py — cross-platform transfer script (Windows/macOS/Linux).
Run from repo root: python ngaip-366-transfer.py

Produces 3 files:
  ENCHS-PW-GenAI-Backend/app_retrieval/evaluation/metrics/response_accuracy.py  (replaces stub)
  ENCHS-PW-GenAI-Backend/app_retrieval/evaluation/annotation_exporter.py        (new)
  ENCHS-PW-GenAI-Backend/tests/app_retrieval/test_metric_response_accuracy.py   (new)

Safe to run twice — all writes overwrite cleanly.
"""
import ast
import subprocess
from pathlib import Path

BRANCH = "ngaip-366-response-accuracy-metric"
BASE_BRANCH = "main-backup-for-mac-claude-repo-04-07-2026"
BACKEND = Path.cwd()


def git(*args):
    subprocess.run(["git", *args], check=True)


def git_or(*args):
    return subprocess.run(["git", *args], check=False).returncode == 0


def ensure_ticket_branch() -> None:
    """Create or switch to this ticket branch from the local backup branch."""
    print(f"[NGAIP-366] Preparing branch: {BRANCH} from local {BASE_BRANCH}")
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

def ensure(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def touch(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch()


# ---------------------------------------------------------------------------
# Branch setup
# ---------------------------------------------------------------------------
ensure_ticket_branch()

# ---------------------------------------------------------------------------
# Directories and __init__ files
# ---------------------------------------------------------------------------
print("[NGAIP-366] Creating directories...")
touch(BACKEND / "tests" / "__init__.py")
touch(BACKEND / "tests" / "app_retrieval" / "__init__.py")

# ---------------------------------------------------------------------------
# response_accuracy.py  (replaces stub from NGAIP-363)
# ---------------------------------------------------------------------------
RESPONSE_ACCURACY_PY = '''\
"""Response accuracy metric — LLM-as-judge implementation (NGAIP-366).

Replaces the stub from NGAIP-363. Scores three criteria via an LLM judge using
the ternary scale defined in metrics_spec.yaml (NGAIP-415):
  0 = fail, 0.5 = partial, 1 = pass
  response_accuracy = (factuality + completeness + groundedness) / 3

Threshold is read from metrics_spec.yaml at init time — never hardcoded.
temperature=0.0 is required for reproducible scoring (NGAIP-415 spec).
Prompt version is stored as a 12-char SHA-256 hash in every result dict.
"""
from __future__ import annotations

import hashlib
import json as _json
import logging
import re
from pathlib import Path

import yaml

from app_retrieval.evaluation.metrics.base import MetricModule

logger = logging.getLogger(__name__)

_SPEC_PATH = Path(__file__).parent.parent / "config" / "metrics_spec.yaml"

# Ternary scale per NGAIP-415 spec: 0=fail, 0.5=partial, 1=pass.
# Composite: (factuality + completeness + groundedness) / 3 → already in [0, 1].
_JUDGE_PROMPT_TEMPLATE = """\
You are evaluating an AI assistant\'s answer. Score each criterion using ONLY these values:
  0   = fail (clearly wrong / missing / unsupported)
  0.5 = partial (somewhat correct but incomplete or only partially supported)
  1   = pass (fully correct, complete, and supported)

Question: {question}
Gold Answer: {gold_answer}
Model Answer: {answer}
Retrieved Context: {context_summary}

Criteria:
1. Factuality: Is the answer factually accurate based on the context?
2. Completeness: Does it cover all key points from the gold answer?
3. Groundedness: Are all claims supported by the retrieved context?

Respond with JSON only using exactly these keys:
{{"factuality": <0|0.5|1>, "completeness": <0|0.5|1>, "groundedness": <0|0.5|1>}}"""

PROMPT_HASH = hashlib.sha256(_JUDGE_PROMPT_TEMPLATE.encode()).hexdigest()[:12]
METRIC_VERSION = "1.0"
_VALID_SCORES = {0, 0.5, 1}
_EXPECTED_KEYS = {"factuality", "completeness", "groundedness"}


def _load_accuracy_threshold() -> float:
    """Read pass threshold from metrics_spec.yaml. Metrics are stored as a list."""
    spec = yaml.safe_load(_SPEC_PATH.read_text())
    for entry in spec["metrics"]:
        if entry["id"] == "response_accuracy":
            pass_str = str(entry["threshold"].get("pass", "0.70"))
            match = re.search(r"[\\d.]+", pass_str)
            return float(match.group()) if match else 0.70
    return 0.70


def _judge_model() -> str:
    """Return the Azure OpenAI deployment name from Django settings."""
    try:
        from django.conf import settings
        return getattr(settings, "AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o")
    except Exception:
        return "gpt-4o"


class ResponseAccuracyMetric(MetricModule):
    name = "response_accuracy"

    def __init__(self, llm_client=None) -> None:
        # llm_client: optional OpenAI-compatible async client.
        # If None, returns placeholder requiring human annotation.
        self.llm_client = llm_client
        self.accuracy_threshold = _load_accuracy_threshold()

    async def score(
        self,
        question: str,
        contexts: list[str],
        answer: str,
        ground_truth: str | None = None,
    ) -> dict:
        context_summary = " ".join(c[:200] for c in contexts[:3])
        effective_gold = ground_truth or ""

        if self.llm_client and effective_gold:
            prompt = _JUDGE_PROMPT_TEMPLATE.format(
                question=question,
                gold_answer=effective_gold,
                answer=answer,
                context_summary=context_summary,
            )
            try:
                resp = await self.llm_client.chat.completions.create(
                    model=_judge_model(),
                    temperature=0.0,
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"},
                )
                raw = _json.loads(resp.choices[0].message.content)

                missing = _EXPECTED_KEYS - raw.keys()
                if missing:
                    raise ValueError(f"LLM response missing keys: {missing}")

                scores = {k: float(raw[k]) for k in _EXPECTED_KEYS}
                invalid = {k: v for k, v in scores.items() if v not in _VALID_SCORES}
                if invalid:
                    raise ValueError(f"LLM returned out-of-spec scores: {invalid}")

                composite = round(sum(scores.values()) / 3, 4)
                return {
                    "response_accuracy": composite,
                    "response_factuality": scores["factuality"],
                    "response_completeness": scores["completeness"],
                    "response_groundedness": scores["groundedness"],
                    "response_accuracy_pass": composite >= self.accuracy_threshold,
                    "judge_prompt_hash": PROMPT_HASH,
                    "metric_version": METRIC_VERSION,
                }
            except Exception as exc:
                logger.warning(
                    "response_accuracy judge failed for question %r: %s",
                    question[:80],
                    exc,
                )

        # No judge, no gold, or judge error — return placeholder for human annotation.
        return {
            "response_accuracy": None,
            "response_accuracy_pass": None,
            "judge_prompt_hash": PROMPT_HASH,
            "metric_version": METRIC_VERSION,
            "note": "human annotation required",
        }
'''

ensure(
    BACKEND / "app_retrieval" / "evaluation" / "metrics" / "response_accuracy.py",
    RESPONSE_ACCURACY_PY,
)
print("[NGAIP-366] Created: app_retrieval/evaluation/metrics/response_accuracy.py")

# ---------------------------------------------------------------------------
# annotation_exporter.py
# ---------------------------------------------------------------------------
ANNOTATION_EXPORTER_PY = '''\
"""Annotation exporter for human dual-annotation workflow (NGAIP-366).

Exports a harness eval case as a structured Markdown file so two human raters
can independently score factuality, completeness, and groundedness.
Results feed into inter-rater kappa calculation (target kappa >= 0.70).
"""
from __future__ import annotations

from pathlib import Path


def export_annotation_case(
    output_dir: str,
    question_id: str,
    question: str,
    answer: str,
    contexts: list[dict],
    gold_answer: str = "",
) -> Path:
    """Write a single eval case as Markdown for human dual-annotation.

    Args:
        output_dir: Directory to write cases/ subdirectory into.
        question_id: Unique identifier for this question (used as filename).
        question: The evaluation question.
        answer: The model\'s answer to score.
        contexts: Retrieved chunks as dicts with \'context\' and \'asset_id\' keys.
        gold_answer: Reference answer from the gold dataset.

    Returns:
        Path to the written Markdown file.
    """
    cases_dir = Path(output_dir) / "cases"
    cases_dir.mkdir(parents=True, exist_ok=True)
    safe_id = Path(question_id).name.replace("/", "_")
    case_path = cases_dir / f"{safe_id}.md"

    context_block = "\\n\\n".join(
        f"**Chunk {i + 1}** (`{c.get(\'asset_id\', \'?\')}`):\\n{c.get(\'context\', \'\')}"
        for i, c in enumerate(contexts[:5])
    )

    rater_table = """\
| Criterion | Score (1-5) | Notes |
|-----------|-------------|-------|
| Factuality | | |
| Completeness | | |
| Groundedness | | |"""

    case_path.write_text(
        f"# Case: {question_id}\\n\\n"
        f"## Question\\n{question}\\n\\n"
        f"## Gold Answer\\n{gold_answer or \'_not provided_\'}\\n\\n"
        f"## Model Answer\\n{answer}\\n\\n"
        f"## Retrieved Context\\n{context_block}\\n\\n"
        f"---\\n"
        f"## Rater 1\\n\\n{rater_table}\\n\\n"
        f"## Rater 2\\n\\n{rater_table}\\n"
    )
    return case_path
'''

ensure(
    BACKEND / "app_retrieval" / "evaluation" / "annotation_exporter.py",
    ANNOTATION_EXPORTER_PY,
)
print("[NGAIP-366] Created: app_retrieval/evaluation/annotation_exporter.py")

# ---------------------------------------------------------------------------
# tests/app_retrieval/test_metric_response_accuracy.py
# ---------------------------------------------------------------------------
TEST_METRIC_PY = '''\
"""Tests for ResponseAccuracyMetric and export_annotation_case (NGAIP-366).

LLM calls are mocked — no live API needed.
Scale: ternary (0 / 0.5 / 1) per NGAIP-415 spec, NOT Likert 1-5.
"""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_metric(llm_client=None, threshold=0.70):
    with patch(
        "app_retrieval.evaluation.metrics.response_accuracy._load_accuracy_threshold",
        return_value=threshold,
    ):
        from app_retrieval.evaluation.metrics.response_accuracy import ResponseAccuracyMetric
        return ResponseAccuracyMetric(llm_client=llm_client)


def _mock_client(factuality, completeness, groundedness):
    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.choices[0].message.content = json.dumps(
        {"factuality": factuality, "completeness": completeness, "groundedness": groundedness}
    )
    mock_client.chat.completions.create = AsyncMock(return_value=mock_resp)
    return mock_client


# ---------------------------------------------------------------------------
# Placeholder paths
# ---------------------------------------------------------------------------

class TestResponseAccuracyPlaceholder:
    @pytest.mark.asyncio
    async def test_no_client_returns_placeholder(self):
        metric = _make_metric(llm_client=None)
        result = await metric.score("Q?", [], "A", ground_truth="Gold")
        assert result["response_accuracy"] is None
        assert result["response_accuracy_pass"] is None
        assert "judge_prompt_hash" in result
        assert result["metric_version"] == "1.0"
        assert result["note"] == "human annotation required"

    @pytest.mark.asyncio
    async def test_no_ground_truth_skips_llm_call(self):
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock()
        metric = _make_metric(llm_client=mock_client)
        result = await metric.score("Q?", [], "A", ground_truth=None)
        assert result["response_accuracy"] is None
        mock_client.chat.completions.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_llm_error_falls_back_to_placeholder(self):
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(side_effect=Exception("API down"))
        metric = _make_metric(llm_client=mock_client)
        result = await metric.score("Q?", [], "A", ground_truth="Gold")
        assert result["response_accuracy"] is None
        assert result["note"] == "human annotation required"


# ---------------------------------------------------------------------------
# Ternary scale scoring
# ---------------------------------------------------------------------------

class TestResponseAccuracyScoring:
    @pytest.mark.asyncio
    async def test_all_pass_gives_1_0(self):
        metric = _make_metric(llm_client=_mock_client(1, 1, 1))
        result = await metric.score("Q?", ["ctx"], "A", ground_truth="Gold")
        assert result["response_accuracy"] == pytest.approx(1.0)
        assert result["response_accuracy_pass"] is True

    @pytest.mark.asyncio
    async def test_all_fail_gives_0_0(self):
        metric = _make_metric(llm_client=_mock_client(0, 0, 0))
        result = await metric.score("Q?", ["ctx"], "A", ground_truth="Gold")
        assert result["response_accuracy"] == pytest.approx(0.0)
        assert result["response_accuracy_pass"] is False

    @pytest.mark.asyncio
    async def test_all_partial_gives_0_5(self):
        metric = _make_metric(llm_client=_mock_client(0.5, 0.5, 0.5))
        result = await metric.score("Q?", ["ctx"], "A", ground_truth="Gold")
        assert result["response_accuracy"] == pytest.approx(0.5)
        assert result["response_accuracy_pass"] is False

    @pytest.mark.asyncio
    async def test_mixed_composite_is_mean(self):
        # (1 + 0.5 + 0.5) / 3 = 0.6667
        metric = _make_metric(llm_client=_mock_client(1, 0.5, 0.5))
        result = await metric.score("Q?", ["ctx"], "A", ground_truth="Gold")
        assert result["response_accuracy"] == pytest.approx(2 / 3, abs=0.001)

    @pytest.mark.asyncio
    async def test_subscores_present_in_result(self):
        metric = _make_metric(llm_client=_mock_client(1, 0.5, 0))
        result = await metric.score("Q?", [], "A", ground_truth="Gold")
        assert result["response_factuality"] == 1
        assert result["response_completeness"] == 0.5
        assert result["response_groundedness"] == 0

    @pytest.mark.asyncio
    async def test_temperature_zero_passed_to_llm(self):
        mock_client = _mock_client(1, 1, 1)
        metric = _make_metric(llm_client=mock_client)
        await metric.score("Q?", [], "A", ground_truth="Gold")
        kwargs = mock_client.chat.completions.create.call_args.kwargs
        assert kwargs.get("temperature") == 0.0

    @pytest.mark.asyncio
    async def test_prompt_hash_matches_module_constant(self):
        metric = _make_metric()
        result = await metric.score("Q?", [], "A", ground_truth=None)
        from app_retrieval.evaluation.metrics.response_accuracy import PROMPT_HASH
        assert result["judge_prompt_hash"] == PROMPT_HASH


# ---------------------------------------------------------------------------
# LLM response validation
# ---------------------------------------------------------------------------

class TestResponseValidation:
    @pytest.mark.asyncio
    async def test_missing_key_falls_back(self):
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.choices[0].message.content = json.dumps({"factuality": 1})
        mock_client.chat.completions.create = AsyncMock(return_value=mock_resp)
        metric = _make_metric(llm_client=mock_client)
        result = await metric.score("Q?", [], "A", ground_truth="Gold")
        assert result["response_accuracy"] is None

    @pytest.mark.asyncio
    async def test_likert_score_rejected(self):
        # 5 is not a valid ternary value — should fall back to placeholder
        metric = _make_metric(llm_client=_mock_client(5, 5, 5))
        result = await metric.score("Q?", [], "A", ground_truth="Gold")
        assert result["response_accuracy"] is None
        assert result["note"] == "human annotation required"

    @pytest.mark.asyncio
    async def test_non_numeric_value_falls_back(self):
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.choices[0].message.content = json.dumps(
            {"factuality": "good", "completeness": 1, "groundedness": 0.5}
        )
        mock_client.chat.completions.create = AsyncMock(return_value=mock_resp)
        metric = _make_metric(llm_client=mock_client)
        result = await metric.score("Q?", [], "A", ground_truth="Gold")
        assert result["response_accuracy"] is None


# ---------------------------------------------------------------------------
# export_annotation_case
# ---------------------------------------------------------------------------

class TestExportAnnotationCase:
    def test_creates_file_in_cases_subdir(self, tmp_path):
        from app_retrieval.evaluation.annotation_exporter import export_annotation_case
        path = export_annotation_case(
            output_dir=str(tmp_path), question_id="q-001",
            question="What is X?", answer="X is Y",
            contexts=[{"context": "X equals Y", "asset_id": "doc1"}],
            gold_answer="X is Y",
        )
        assert path == tmp_path / "cases" / "q-001.md"
        assert path.exists()

    def test_file_contains_rater_tables(self, tmp_path):
        from app_retrieval.evaluation.annotation_exporter import export_annotation_case
        path = export_annotation_case(
            output_dir=str(tmp_path), question_id="q-002",
            question="Q?", answer="A", contexts=[],
        )
        content = path.read_text()
        assert "Rater 1" in content and "Rater 2" in content
        assert "Factuality" in content and "Groundedness" in content

    def test_missing_gold_shows_placeholder(self, tmp_path):
        from app_retrieval.evaluation.annotation_exporter import export_annotation_case
        path = export_annotation_case(
            output_dir=str(tmp_path), question_id="q-003",
            question="Q?", answer="A", contexts=[], gold_answer="",
        )
        assert "_not provided_" in path.read_text()

    def test_context_chunks_included(self, tmp_path):
        from app_retrieval.evaluation.annotation_exporter import export_annotation_case
        path = export_annotation_case(
            output_dir=str(tmp_path), question_id="q-004", question="Q?", answer="A",
            contexts=[{"context": "chunk alpha", "asset_id": "asset-1"}],
        )
        content = path.read_text()
        assert "chunk alpha" in content and "asset-1" in content

    def test_idempotent_overwrite(self, tmp_path):
        from app_retrieval.evaluation.annotation_exporter import export_annotation_case
        kwargs = dict(output_dir=str(tmp_path), question_id="q-005",
                      question="Q?", answer="A", contexts=[])
        export_annotation_case(**kwargs)
        path = export_annotation_case(**kwargs)
        assert path.exists()
'''

ensure(
    BACKEND / "tests" / "app_retrieval" / "test_metric_response_accuracy.py",
    TEST_METRIC_PY,
)
print("[NGAIP-366] Created: tests/app_retrieval/test_metric_response_accuracy.py")

commit_transfer_changes()

print("")
print("[NGAIP-366] Done. Verify with:")
print("  cd ENCHS-PW-GenAI-Backend")
print("  pytest tests/app_retrieval/test_metric_response_accuracy.py -v")
print("  # Expect 18 tests passing")
