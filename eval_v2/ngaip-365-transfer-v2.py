#!/usr/bin/env python3
"""NGAIP-365 v2 metric transfer."""
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
    target.write_text(content, encoding="utf-8")
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

BRANCH = 'ngaip-365-context-relevancy-metric-v2'
COMMIT_MESSAGE = 'NGAIP-365: Apply v2 RAGAS context relevancy changes'

MODULE = 'from __future__ import annotations\n\nfrom app_retrieval.evaluation.async_ragas_runner import aevaluate_cases, default_metrics\n\nCONTEXT_RELEVANCY_METRICS = ["context_precision", "context_recall", "answer_relevancy"]\n\n\nasync def score_context_relevancy(cases, *, llm=None, embeddings=None):\n    return await aevaluate_cases(cases, metrics=default_metrics(CONTEXT_RELEVANCY_METRICS), llm=llm, embeddings=embeddings)\n'
TESTS = 'from app_retrieval.evaluation.metrics.context_relevancy_v2 import CONTEXT_RELEVANCY_METRICS\n\n\ndef test_context_relevancy_uses_ragas_context_metrics():\n    assert CONTEXT_RELEVANCY_METRICS == ["context_precision", "context_recall", "answer_relevancy"]\n'

def main() -> None:
    prepare_branch(BRANCH)
    touch("app_retrieval/evaluation/metrics/__init__.py")
    touch("tests/app_retrieval/__init__.py")
    path = "app_retrieval/evaluation/metrics/context_relevancy_v2.py"
    test = "tests/app_retrieval/test_context_relevancy_v2.py"
    write(path, MODULE)
    write(test, TESTS)
    run_pytest([test])
    commit([path, "app_retrieval/evaluation/metrics/__init__.py", "tests/app_retrieval/__init__.py"], [test], COMMIT_MESSAGE)

if __name__ == "__main__":
    main()

