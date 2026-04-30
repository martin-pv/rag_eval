#!/usr/bin/env python3
"""NGAIP-412 v2: async RAGAS POC runner."""
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

BRANCH = 'ngaip-412-rag-eval-harness-poc-v2'
COMMIT_MESSAGE = 'NGAIP-412: Apply v2 async RAGAS POC changes'

POC = 'from __future__ import annotations\n\nimport asyncio\nfrom pathlib import Path\n\nfrom app_retrieval.evaluation.async_ragas_runner import aevaluate_cases, collect_ragas_cases, default_metrics\nfrom app_retrieval.evaluation.gold_dataset import load_gold_file\n\n\nasync def run_poc(gold_file: str | Path, retrieve, answer, *, llm=None, embeddings=None):\n    rows = load_gold_file(gold_file)\n    cases = await collect_ragas_cases(rows, retrieve, answer)\n    return await aevaluate_cases(cases, metrics=default_metrics(["faithfulness", "context_precision", "answer_relevancy"]), llm=llm, embeddings=embeddings)\n\n\ndef run_poc_sync(*args, **kwargs):\n    return asyncio.run(run_poc(*args, **kwargs))\n'
TESTS = 'from app_retrieval.evaluation.poc_async_ragas_eval import run_poc_sync\n\n\ndef test_run_poc_sync_symbol_exists():\n    assert callable(run_poc_sync)\n'

def main() -> None:
    prepare_branch(BRANCH)
    touch("app_retrieval/__init__.py")
    touch("app_retrieval/evaluation/__init__.py")
    touch("app_retrieval/evaluation/__init__.py")
    touch("tests/app_retrieval/__init__.py")
    path = "app_retrieval/evaluation/poc_async_ragas_eval.py"
    test = "tests/app_retrieval/test_poc_async_ragas_eval.py"
    write(path, POC)
    write(test, TESTS)
    run_pytest([test])
    commit([path, "app_retrieval/evaluation/__init__.py", "tests/app_retrieval/__init__.py", "app_retrieval/__init__.py", "app_retrieval/evaluation/__init__.py"], [test], COMMIT_MESSAGE)

if __name__ == "__main__":
    main()

