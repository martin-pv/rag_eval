#!/usr/bin/env python3
"""NGAIP-364 v2 metric transfer."""
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

BRANCH = 'ngaip-364-citation-accuracy-metric-v2'
COMMIT_MESSAGE = 'NGAIP-364: Apply v2 RAGAS citation accuracy changes'

MODULE = 'from __future__ import annotations\n\nfrom app_retrieval.evaluation.async_ragas_runner import aevaluate_cases, default_metrics\nfrom app_retrieval.evaluation.ragas_factory_v2 import EvaluatorModelConfig, ascore_discrete_metric, build_discrete_metric\n\nCITATION_SUPPORT_PROMPT = """Judge whether cited sources support the response.\\nResponse: {response}\\nRetrieved context: {retrieved_contexts}\\nReturn only pass or fail."""\n\n\ndef source_id_recall(expected: set[str], actual: set[str]) -> float:\n    if not expected:\n        return 1.0\n    return len(expected & actual) / len(expected)\n\n\nasync def score_citation_accuracy(cases, *, llm=None, embeddings=None):\n    return await aevaluate_cases(cases, metrics=default_metrics(["faithfulness", "context_precision"]), llm=llm, embeddings=embeddings)\n\n\nasync def judge_citation_support(response: str, retrieved_contexts: list[str], *, config: EvaluatorModelConfig):\n    metric = build_discrete_metric("citation_support", CITATION_SUPPORT_PROMPT)\n    return await ascore_discrete_metric(metric, config=config, response=response, retrieved_contexts="\\n".join(retrieved_contexts))\n'
TESTS = 'from app_retrieval.evaluation.metrics.citation_accuracy_v2 import source_id_recall\n\n\ndef test_source_id_recall_is_supplemental_deterministic_check():\n    assert source_id_recall({"a", "b"}, {"b", "c"}) == 0.5\n'

def main() -> None:
    prepare_branch(BRANCH)
    touch("app_retrieval/__init__.py")
    touch("app_retrieval/evaluation/__init__.py")
    touch("app_retrieval/evaluation/metrics/__init__.py")
    touch("tests/app_retrieval/__init__.py")
    path = "app_retrieval/evaluation/metrics/citation_accuracy_v2.py"
    test = "tests/app_retrieval/test_citation_accuracy_v2.py"
    write(path, MODULE)
    write(test, TESTS)
    run_pytest([test])
    commit([path, "app_retrieval/evaluation/metrics/__init__.py", "tests/app_retrieval/__init__.py", "app_retrieval/__init__.py", "app_retrieval/evaluation/__init__.py"], [test], COMMIT_MESSAGE)

if __name__ == "__main__":
    main()

