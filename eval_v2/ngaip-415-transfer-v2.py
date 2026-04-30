#!/usr/bin/env python3
"""NGAIP-415 v2: RAGAS-primary report schema."""
import subprocess
import sys
from pathlib import Path

BASE_BRANCH = "main"
BACKEND = Path.cwd()

def git(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=BACKEND, check=check, text=True)

def prepare_branch(branch: str) -> None:
    current = subprocess.run(["git", "branch", "--show-current"], cwd=BACKEND, text=True, capture_output=True, check=True).stdout.strip()
    if current == branch:
        return
    if git("switch", branch, check=False).returncode == 0:
        return
    git("switch", BASE_BRANCH)
    git("switch", "-c", branch)

def write(path: str, content: str) -> Path:
    target = BACKEND / path
    target.parent.mkdir(parents=True, exist_ok=True)
    # Use write_bytes to force LF line endings on Windows (text mode would
    # translate "\n" -> "\r\n", contaminating generated .py and .jsonl files).
    target.write_bytes(content.encode("utf-8"))
    print(f"[write] {target.relative_to(BACKEND)}")
    return target

def touch(path: str) -> Path:
    target = BACKEND / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.touch(exist_ok=True)
    return target

def run_pytest(test_paths: list[str]) -> None:
    if test_paths:
        subprocess.run([sys.executable, "-m", "pytest", *test_paths, "-v"], cwd=BACKEND, check=True)

def commit(paths: list[str], forced_tests: list[str], message: str) -> None:
    if paths:
        git("add", *paths)
    for test_path in forced_tests:
        git("add", "-f", test_path)
    status = subprocess.run(["git", "status", "--short"], cwd=BACKEND, text=True, capture_output=True, check=True).stdout.strip()
    if not status:
        print("[commit] no changes")
        return
    git("commit", "-m", message)

BRANCH = 'ngaip-415-metrics-success-criteria-v2'
COMMIT_MESSAGE = 'NGAIP-415: Apply v2 RAGAS report schema changes'

SCHEMA = 'from __future__ import annotations\n\nfrom dataclasses import asdict, dataclass, field\nfrom datetime import datetime, timezone\nfrom typing import Any\n\nRAGAS_PRIMARY_METRICS = ["faithfulness", "answer_relevancy", "answer_correctness", "context_precision", "context_recall"]\nDETERMINISTIC_SUPPLEMENTS = ["source_id_recall", "citation_span_match", "token_overlap"]\n\n\n@dataclass(slots=True)\nclass RagasReport:\n    ticket: str\n    metric_scores: dict[str, float]\n    case_count: int\n    evaluator_model: str\n    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())\n    deterministic_supplements: dict[str, Any] = field(default_factory=dict)\n\n    def to_dict(self) -> dict[str, Any]:\n        data = asdict(self)\n        data["ragas_primary_metrics"] = RAGAS_PRIMARY_METRICS\n        data["deterministic_supplements_used"] = sorted(self.deterministic_supplements)\n        return data\n'
TESTS = 'from app_retrieval.evaluation.report_schema_v2 import RAGAS_PRIMARY_METRICS, RagasReport\n\n\ndef test_report_marks_ragas_primary_metrics():\n    report = RagasReport(ticket="NGAIP-415", metric_scores={"faithfulness": 1.0}, case_count=1, evaluator_model="gpt-4o")\n    data = report.to_dict()\n    assert "faithfulness" in data["ragas_primary_metrics"]\n    assert RAGAS_PRIMARY_METRICS[0] == "faithfulness"\n'

def main() -> None:
    prepare_branch(BRANCH)
    touch("app_retrieval/__init__.py")
    touch("app_retrieval/evaluation/__init__.py")
    touch("app_retrieval/evaluation/__init__.py")
    touch("tests/app_retrieval/__init__.py")
    path = "app_retrieval/evaluation/report_schema_v2.py"
    test = "tests/app_retrieval/test_report_schema_v2.py"
    write(path, SCHEMA)
    write(test, TESTS)
    run_pytest([test])
    commit([path, "app_retrieval/evaluation/__init__.py", "tests/app_retrieval/__init__.py", "app_retrieval/__init__.py", "app_retrieval/evaluation/__init__.py"], [test], COMMIT_MESSAGE)

if __name__ == "__main__":
    main()

