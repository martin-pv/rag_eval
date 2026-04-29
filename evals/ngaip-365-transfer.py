#!/usr/bin/env python3
"""NGAIP-365 transfer: configure RAGAS-primary metric wrapper."""
import subprocess
from pathlib import Path

BRANCH = 'ngaip-365-context-relevancy-metric'
COMMIT_MESSAGE = "NGAIP-365: Apply transfer script changes"
BASE_BRANCH = "main"
BACKEND = Path.cwd()
GENERATED_PATHS = ["app_retrieval/evaluation/metrics/__init__.py", "app_retrieval/evaluation/metrics/context_relevancy.py", "tests/app_retrieval/__init__.py", "tests/app_retrieval/test_metric_context_relevancy.py"]
OBSOLETE_PATHS = []


def git(*args): subprocess.run(["git", *args], check=True)
def git_or(*args): return subprocess.run(["git", *args], check=False).returncode == 0
def current_branch() -> str: return subprocess.check_output(["git", "branch", "--show-current"], text=True).strip()


def ensure_ticket_branch() -> None:
    print(f"[NGAIP-365] Preparing branch: {BRANCH} from local {BASE_BRANCH}")
    if current_branch() == BRANCH: return
    if git_or("rev-parse", "--verify", f"refs/heads/{BRANCH}"):
        git("switch", BRANCH); return
    git("switch", BASE_BRANCH); git("switch", "-c", BRANCH)


def ensure(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True); path.write_text(content, encoding="utf-8"); print(f"  Created: {path}")

def touch(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True); path.touch(exist_ok=True)


def commit_transfer_changes() -> None:
    existing = [p for p in GENERATED_PATHS if (BACKEND / p).exists()]
    normal = [p for p in existing if not p.startswith("tests/")]
    tests = [p for p in existing if p.startswith("tests/")]
    if normal: git("add", "--", *normal)
    if tests: git("add", "-f", "--", *tests)
    if subprocess.run(["git", "diff", "--cached", "--quiet", "--", *existing], check=False).returncode == 0:
        print(f"[NGAIP-365] No changes to commit."); return
    git("commit", "-m", COMMIT_MESSAGE, "--", *existing)


METRIC_PY = 'from __future__ import annotations\n\nfrom app_retrieval.evaluation.ragas_adapter import RAGAS_METRIC_SPECS, build_ragas_metrics, run_ragas_evaluation\n\nMETRIC_KEY = \'context_relevancy\'\nOWNER_TICKET = \'NGAIP-365\'\nRAGAS_METRIC_SPEC = RAGAS_METRIC_SPECS[METRIC_KEY]\n\n\ndef build_metrics():\n    """Return the RAGAS metric objects owned by this ticket."""\n    return build_ragas_metrics([METRIC_KEY])\n\n\ndef evaluate_records(records, llm=None, embeddings=None):\n    """Evaluate records with RAGAS first; deterministic checks live in harness supplements."""\n    return run_ragas_evaluation(records, [METRIC_KEY], llm=llm, embeddings=embeddings)\n'
TEST_PY = "from __future__ import annotations\n\nfrom app_retrieval.evaluation.metrics.context_relevancy import METRIC_KEY, OWNER_TICKET, RAGAS_METRIC_SPEC\n\n\ndef test_context_relevancy_is_ragas_configured():\n    assert METRIC_KEY == 'context_relevancy'\n    assert OWNER_TICKET == 'NGAIP-365'\n    assert RAGAS_METRIC_SPEC.ragas_symbols\n"


def main():
    ensure_ticket_branch()
    touch(BACKEND / "app_retrieval" / "evaluation" / "metrics" / "__init__.py")
    touch(BACKEND / "tests" / "app_retrieval" / "__init__.py")
    ensure(BACKEND / "app_retrieval" / "evaluation" / "metrics" / "context_relevancy.py", METRIC_PY)
    ensure(BACKEND / "tests" / "app_retrieval" / "test_metric_context_relevancy.py", TEST_PY)
    commit_transfer_changes()
    print("[NGAIP-365] Done. This ticket now configures RAGAS metrics through the NGAIP-363 adapter.")


if __name__ == "__main__":
    main()
