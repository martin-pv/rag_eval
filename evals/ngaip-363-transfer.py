#!/usr/bin/env python3
"""NGAIP-363 Transfer Script — cross-platform (Windows/macOS/Linux)
Usage: python ngaip-363-transfer.py  (run from repo root)
"""
import subprocess
from pathlib import Path

BRANCH = "ngaip-363-rag-evaluation-harness"
COMMIT_MESSAGE = "NGAIP-363: Apply transfer script changes"
BASE_BRANCH = "main-backup-for-mac-claude-repo-04-07-2026"
BACKEND = Path.cwd()

GENERATED_PATHS = [
    "requirements.txt",
    "app_retrieval/evaluation/__init__.py",
    "app_retrieval/evaluation/config.py",
    "app_retrieval/evaluation/config/__init__.py",
    "app_retrieval/evaluation/config/eval_config.py",
    "app_retrieval/evaluation/config/eval_default.yaml",
    "app_retrieval/evaluation/config/eval_ci_fixture.yaml",
    "app_retrieval/evaluation/config/ci_gold.jsonl",
    "app_retrieval/evaluation/ragas_factory.py",
    "app_retrieval/evaluation/harness.py",
    "app_retrieval/management/__init__.py",
    "app_retrieval/management/commands/__init__.py",
    "app_retrieval/management/commands/rag_eval.py",
    "tests/app_retrieval/__init__.py",
    "tests/app_retrieval/test_eval_harness.py",
]

OBSOLETE_PATHS = ['app_retrieval/evaluation/retriever.py', 'app_retrieval/evaluation/runner.py', 'app_retrieval/evaluation/metrics/base.py', 'app_retrieval/evaluation/metrics/context_relevancy.py', 'app_retrieval/evaluation/metrics/citation_accuracy.py', 'app_retrieval/evaluation/metrics/response_accuracy.py', 'app_retrieval/evaluation/reporters/json_reporter.py', 'app_retrieval/evaluation/reporters/csv_reporter.py', 'tests/app_retrieval/test_eval_config.py', 'tests/app_retrieval/test_eval_runner.py']


def read_text_compat(path: Path) -> str:
    if not path.exists():
        return ""
    raw = path.read_bytes()
    if not raw:
        return ""
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        return raw.decode("utf-16")
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw.decode("utf-8-sig")
    for encoding in ("utf-8", "utf-16-le", "cp1252", "latin-1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("latin-1")


def git(*args):
    subprocess.run(["git", *args], check=True)


def git_or(*args):
    return subprocess.run(["git", *args], check=False).returncode == 0


def current_branch() -> str:
    return subprocess.check_output(["git", "branch", "--show-current"], text=True).strip()


def ensure_ticket_branch() -> None:
    """Ensure this transfer runs on its local ticket branch; never push/publish."""
    print(f"[363-transfer] Preparing branch: {BRANCH} from local {BASE_BRANCH}")
    if current_branch() == BRANCH:
        print(f"[363-transfer] Already on ticket branch: {BRANCH}")
        return
    if git_or("rev-parse", "--verify", f"refs/heads/{BRANCH}"):
        git("switch", BRANCH)
        return
    git("switch", BASE_BRANCH)
    git("switch", "-c", BRANCH)


def ensure(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"  Created: {path}")


def touch(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.touch()
        print(f"  Touched: {path}")
    else:
        print(f"  Already exists: {path}")


def append_if_missing(path: Path, line: str):
    text = read_text_compat(path)
    addition = line if line.endswith("\n") else line + "\n"
    if line.rstrip() not in text:
        path.parent.mkdir(parents=True, exist_ok=True)
        new_content = addition if not text else text + ("" if text.endswith("\n") else "\n") + addition
        path.write_text(new_content, encoding="utf-8")
        print(f"  Appended: {line.strip()}")
    else:
        print(f"  Already present: {line.strip()}")


def remove_obsolete_generated_files() -> None:
    print("[363-transfer] Removing obsolete split NGAIP-363 files if present...")
    git("rm", "--ignore-unmatch", "--", *OBSOLETE_PATHS)


def commit_transfer_changes() -> None:
    existing_paths = [p for p in GENERATED_PATHS if (BACKEND / p).exists()]
    commit_paths = sorted(set(existing_paths + OBSOLETE_PATHS))
    if not commit_paths:
        print("[363-transfer] No generated files exist to commit.")
        return
    normal_paths = [p for p in existing_paths if not p.startswith("tests/")]
    test_paths = [p for p in existing_paths if p.startswith("tests/")]
    if normal_paths:
        git("add", "--", *normal_paths)
    if test_paths:
        print("[363-transfer] Force-adding generated test files...")
        git("add", "-f", "--", *test_paths)
    staged = subprocess.run(["git", "diff", "--cached", "--quiet", "--", *commit_paths], check=False)
    if staged.returncode == 0:
        print("[363-transfer] No changes to commit.")
        return
    git("commit", "-m", COMMIT_MESSAGE, "--", *commit_paths)
    print(f"[363-transfer] Created local commit: {COMMIT_MESSAGE}")


def main():
    print(f"[363-transfer] Starting transfer into: {BACKEND}")
    ensure_ticket_branch()

    print("[363-transfer] Patching requirements.txt...")
    req = BACKEND / "requirements.txt"
    append_if_missing(req, "ragas>=0.2.0")
    append_if_missing(req, "datasets>=2.14.0")
    append_if_missing(req, "lancedb")
    append_if_missing(req, "openai>=1.109.1")
    append_if_missing(req, "langchain-openai==0.2.11")
    append_if_missing(req, "langchain-core==0.3.21")
    append_if_missing(req, "langchain-community==0.3.4")
    append_if_missing(req, "langchain==0.3.10")

    for directory in [
        BACKEND / "app_retrieval" / "evaluation" / "config",
        BACKEND / "app_retrieval" / "management" / "commands",
        BACKEND / "tests" / "app_retrieval",
    ]:
        directory.mkdir(parents=True, exist_ok=True)

    for init in [
        BACKEND / "app_retrieval" / "evaluation" / "__init__.py",
        BACKEND / "app_retrieval" / "evaluation" / "config" / "__init__.py",
        BACKEND / "app_retrieval" / "management" / "__init__.py",
        BACKEND / "app_retrieval" / "management" / "commands" / "__init__.py",
        BACKEND / "tests" / "app_retrieval" / "__init__.py",
    ]:
        touch(init)

    remove_obsolete_generated_files()

    ensure(BACKEND / "app_retrieval" / "evaluation" / "config.py", 'from __future__ import annotations\n\nfrom typing import Literal\n\nfrom pydantic import BaseModel, Field, model_validator\n\n\nclass EvalConfig(BaseModel):\n    seed: int = 42\n    folder_ids: list[int]\n    retriever_type: Literal["semantic", "keyword", "hybrid"] = "semantic"\n    top_k: int = 5\n    model: str = "gpt-4o"\n    gold_file: str\n    output_dir: str = "evaluation/output"\n    metrics: list[str] = Field(default=["context_relevancy", "citation_accuracy", "response_accuracy"])\n    eval_user_id: int | None = None\n\n    @model_validator(mode="after")\n    def _require_user_for_keyword(self) -> "EvalConfig":\n        if self.retriever_type in ("keyword", "hybrid") and self.eval_user_id is None:\n            raise ValueError(f"eval_user_id is required when retriever_type is {self.retriever_type!r}")\n        return self\n')
    ensure(BACKEND / "app_retrieval" / "evaluation" / "config" / "eval_config.py", 'from __future__ import annotations\n\nfrom dataclasses import dataclass\nfrom pathlib import Path\nfrom typing import Any\n\nimport yaml\n\n\n@dataclass(frozen=True)\nclass RagasEvaluatorConfig:\n    framework: str = "ragas"\n    enabled: bool = False\n    provider: str = "azure_openai"\n    model: str | None = None\n    embeddings: str | None = None\n    temperature: float = 0\n    timeout_seconds: int = 120\n    max_retries: int = 2\n\n\n@dataclass(frozen=True)\nclass EvalConfig:\n    metrics_spec_version: str\n    evaluator: RagasEvaluatorConfig\n    raw: dict[str, Any]\n\n\ndef load_eval_config(path: Path) -> EvalConfig:\n    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}\n    evaluator = RagasEvaluatorConfig(**data.get("evaluator", {}))\n    if evaluator.framework != "ragas":\n        raise ValueError(f"Unsupported evaluator framework: {evaluator.framework}")\n    return EvalConfig(\n        metrics_spec_version=str(data.get("metrics_spec_version", "unknown")),\n        evaluator=evaluator,\n        raw=data,\n    )\n')
    ensure(BACKEND / "app_retrieval" / "evaluation" / "ragas_factory.py", 'from __future__ import annotations\n\nimport os\n\nfrom app.settings_intellisense import settings\nfrom langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings, OpenAIEmbeddings as LangChainOpenAIEmbeddings\nfrom langchain_openai.llms import AzureOpenAI\nfrom openai import OpenAI\nfrom ragas.embeddings import OpenAIEmbeddings\n\nfrom app_retrieval.evaluation.config.eval_config import RagasEvaluatorConfig\n\n\ndef _setting(name: str, default: str | None = None) -> str | None:\n    return getattr(settings, name, os.environ.get(name, default))\n\n\ndef build_ragas_langchain_models(config: RagasEvaluatorConfig):\n    if config.provider != "azure_openai":\n        raise ValueError(f"Unsupported RAGAS provider: {config.provider}")\n    if not config.model or not config.embeddings:\n        raise ValueError("RAGAS model and embedding deployments are required")\n    llm = AzureChatOpenAI(\n        azure_deployment=config.model,\n        api_key=_setting("AZURE_OPENAI_API_KEY"),\n        azure_endpoint=_setting("AZURE_OPENAI_ENDPOINT"),\n        api_version=_setting("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),\n        temperature=config.temperature,\n        timeout=config.timeout_seconds,\n        max_retries=config.max_retries,\n    )\n    embeddings = AzureOpenAIEmbeddings(\n        azure_deployment=config.embeddings,\n        api_key=_setting("AZURE_OPENAI_API_KEY"),\n        azure_endpoint=_setting("AZURE_OPENAI_ENDPOINT"),\n        api_version=_setting("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),\n    )\n    return llm, embeddings\n\n\ndef build_ragas_azure_completion_llm(config: RagasEvaluatorConfig) -> AzureOpenAI:\n    if not config.model:\n        raise ValueError("RAGAS evaluator model deployment is required")\n    return AzureOpenAI(\n        azure_deployment=config.model,\n        api_key=_setting("AZURE_OPENAI_API_KEY"),\n        azure_endpoint=_setting("AZURE_OPENAI_ENDPOINT"),\n        api_version=_setting("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),\n        temperature=config.temperature,\n        timeout=config.timeout_seconds,\n        max_retries=config.max_retries,\n    )\n\n\ndef build_langchain_openai_embeddings(model: str | None = None) -> LangChainOpenAIEmbeddings:\n    return LangChainOpenAIEmbeddings(\n        model=model or _setting("OPENAI_EMBEDDINGS_MODEL", "text-embedding-3-small"),\n        api_key=_setting("OPENAI_API_KEY"),\n    )\n\n\ndef build_ragas_openai_embeddings(api_key: str | None = None) -> OpenAIEmbeddings:\n    return OpenAIEmbeddings(client=OpenAI(api_key=api_key))\n')
    ensure(BACKEND / "app_retrieval" / "evaluation" / "harness.py", 'from __future__ import annotations\n\nimport asyncio\nimport csv\nimport json\nimport random\nfrom abc import ABC, abstractmethod\nfrom dataclasses import asdict, dataclass\nfrom pathlib import Path\n\nfrom django.test import RequestFactory\n\nfrom app_retrieval.evaluation.config import EvalConfig\n\n\n@dataclass\nclass MetricResult:\n    metric_name: str\n    score: float\n    details: dict\n\n\nclass BaseRetriever(ABC):\n    @abstractmethod\n    async def retrieve(self, query: str, folder, top_k: int) -> list[dict]:\n        ...\n\n\nclass SemanticRetriever(BaseRetriever):\n    async def retrieve(self, query: str, folder, top_k: int) -> list[dict]:\n        from app_retrieval.data_assets.utils import search_folder_index\n        return await search_folder_index(folder, query, top_k)\n\n\nclass KeywordRetriever(BaseRetriever):\n    def __init__(self, eval_user=None) -> None:\n        self._eval_user = eval_user\n\n    async def retrieve(self, query: str, folder, top_k: int) -> list[dict]:\n        from app_retrieval.views.search import keyword_search_folder\n        request = RequestFactory().get("/")\n        request.user = self._eval_user\n        return await keyword_search_folder(request, query, folder, k=top_k)\n\n\nclass HybridRetriever(BaseRetriever):\n    def __init__(self, eval_user=None) -> None:\n        self._semantic = SemanticRetriever()\n        self._keyword = KeywordRetriever(eval_user=eval_user)\n\n    async def retrieve(self, query: str, folder, top_k: int) -> list[dict]:\n        semantic_results, keyword_results = await asyncio.gather(\n            self._semantic.retrieve(query, folder, top_k),\n            self._keyword.retrieve(query, folder, top_k),\n        )\n        seen: dict[int | str, dict] = {}\n        for chunk in semantic_results + keyword_results:\n            key = chunk.get("pk") or chunk.get("id") or id(chunk)\n            if key not in seen or chunk.get("score", 0) > seen[key].get("score", 0):\n                seen[key] = chunk\n        return sorted(seen.values(), key=lambda c: c.get("score", 0), reverse=True)[:top_k]\n\n\ndef build_retriever(retriever_type: str, eval_user=None) -> BaseRetriever:\n    if retriever_type == "semantic":\n        return SemanticRetriever()\n    if retriever_type == "keyword":\n        return KeywordRetriever(eval_user=eval_user)\n    if retriever_type == "hybrid":\n        return HybridRetriever(eval_user=eval_user)\n    raise ValueError(f"Unknown retriever_type: {retriever_type!r}")\n\n\ndef context_relevancy(gold_row: dict, retrieved_chunks: list[dict]) -> MetricResult:\n    return MetricResult("context_relevancy", 0.0, {"todo": "NGAIP-365 RAGAS context metrics"})\n\n\ndef citation_accuracy(gold_row: dict, retrieved_chunks: list[dict], answer: str | None = None) -> MetricResult:\n    return MetricResult("citation_accuracy", 0.0, {"todo": "NGAIP-364 citation metadata metrics"})\n\n\ndef response_accuracy(gold_row: dict, answer: str | None = None) -> MetricResult:\n    return MetricResult("response_accuracy", 0.0, {"todo": "NGAIP-366 RAGAS answer metrics"})\n\n\nclass JsonReporter:\n    def write(self, path: Path, payload: dict) -> None:\n        path.parent.mkdir(parents=True, exist_ok=True)\n        path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")\n\n\nclass CsvReporter:\n    def write(self, path: Path, rows: list[dict]) -> None:\n        path.parent.mkdir(parents=True, exist_ok=True)\n        if not rows:\n            path.write_text("", encoding="utf-8")\n            return\n        with path.open("w", newline="", encoding="utf-8") as handle:\n            writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))\n            writer.writeheader()\n            writer.writerows(rows)\n\n\nclass EvalRunner:\n    def __init__(self, config: EvalConfig, retriever: BaseRetriever | None = None) -> None:\n        self.config = config\n        self.retriever = retriever or build_retriever(config.retriever_type)\n\n    def _seeded_rows(self, gold_rows: list[dict]) -> list[dict]:\n        rows = list(gold_rows)\n        random.Random(self.config.seed).shuffle(rows)\n        return rows\n\n    async def run(self, gold_rows: list[dict], folder=None) -> dict:\n        results = []\n        for row in self._seeded_rows(gold_rows):\n            retrieved = await self.retriever.retrieve(row["question"], folder, self.config.top_k)\n            metric_results = [\n                context_relevancy(row, retrieved),\n                citation_accuracy(row, retrieved),\n                response_accuracy(row),\n            ]\n            results.append(\n                {\n                    "question_id": row.get("question_id"),\n                    "question": row.get("question"),\n                    "retrieved_count": len(retrieved),\n                    "scores": {m.metric_name: m.score for m in metric_results},\n                    "details": {m.metric_name: m.details for m in metric_results},\n                }\n            )\n        return {"config": self.config.model_dump(), "results": results}\n\n\ndef metric_result_to_dict(result: MetricResult) -> dict:\n    return asdict(result)\n')
    ensure(BACKEND / "app_retrieval" / "management" / "commands" / "rag_eval.py", 'from __future__ import annotations\n\nimport json\nfrom pathlib import Path\n\nimport yaml\nfrom django.core.management.base import BaseCommand, CommandError\n\nfrom app_retrieval.evaluation.config import EvalConfig\nfrom app_retrieval.evaluation.harness import CsvReporter, EvalRunner, JsonReporter\n\n\nclass Command(BaseCommand):\n    help = "Run PrattWise RAG evaluation harness."\n\n    def add_arguments(self, parser):\n        parser.add_argument("run", nargs="?")\n        parser.add_argument("--config", required=True)\n\n    def handle(self, *args, **options):\n        config_path = Path(options["config"])\n        if not config_path.exists():\n            raise CommandError(f"Config not found: {config_path}")\n        data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}\n        config = EvalConfig(**data)\n        gold_path = Path(config.gold_file)\n        if not gold_path.exists():\n            raise CommandError(f"Gold file not found: {gold_path}")\n        gold_rows = [json.loads(line) for line in gold_path.read_text(encoding="utf-8").splitlines() if line.strip()]\n        import asyncio\n        payload = asyncio.run(EvalRunner(config).run(gold_rows))\n        output_dir = Path(config.output_dir)\n        JsonReporter().write(output_dir / "report.json", payload)\n        CsvReporter().write(output_dir / "report.csv", payload["results"])\n        self.stdout.write(self.style.SUCCESS(f"Wrote reports to {output_dir}"))\n')
    ensure(BACKEND / "app_retrieval" / "evaluation" / "config" / "eval_default.yaml", 'seed: 42\nfolder_ids: []\nretriever_type: semantic\ntop_k: 5\nmodel: gpt-4o\ngold_file: app_retrieval/evaluation/config/ci_gold.jsonl\noutput_dir: evaluation/output\nmetrics:\n  - context_relevancy\n  - citation_accuracy\n  - response_accuracy\n')
    ensure(BACKEND / "app_retrieval" / "evaluation" / "config" / "eval_ci_fixture.yaml", 'seed: 42\nfolder_ids: []\nretriever_type: semantic\ntop_k: 2\nmodel: ci-mock\ngold_file: app_retrieval/evaluation/config/ci_gold.jsonl\noutput_dir: evaluation/output/ci\nmetrics:\n  - context_relevancy\n')
    ensure(BACKEND / "app_retrieval" / "evaluation" / "config" / "ci_gold.jsonl", '{"question": "What is the standard inspection interval for a turbofan engine?", "answer": "The standard interval is defined in the maintenance manual.", "ground_truth": "Refer to the engine maintenance manual for the authoritative interval."}\n{"question": "Which materials are approved for high-pressure compressor blade repair?", "answer": "Approved materials are listed in the approved parts list.", "ground_truth": "See the approved repair manual for the complete list of materials."}\n')
    ensure(BACKEND / "tests" / "app_retrieval" / "test_eval_harness.py", 'from __future__ import annotations\n\nimport json\nfrom pathlib import Path\nfrom unittest.mock import AsyncMock\n\nimport pytest\nfrom pydantic import ValidationError\n\nfrom app_retrieval.evaluation.config import EvalConfig\nfrom app_retrieval.evaluation.config.eval_config import load_eval_config\nfrom app_retrieval.evaluation.harness import CsvReporter, EvalRunner, JsonReporter, build_retriever, metric_result_to_dict, response_accuracy\n\n\nclass TestEvalConfig:\n    def test_valid_minimal_config(self):\n        cfg = EvalConfig(folder_ids=[], gold_file="dummy.jsonl")\n        assert cfg.seed == 42\n        assert cfg.retriever_type == "semantic"\n        assert cfg.top_k == 5\n\n    def test_invalid_retriever_type_raises(self):\n        with pytest.raises(ValidationError):\n            EvalConfig(folder_ids=[], gold_file="dummy.jsonl", retriever_type="invalid")\n\n    def test_keyword_without_eval_user_id_raises(self):\n        with pytest.raises(ValidationError, match="eval_user_id is required"):\n            EvalConfig(folder_ids=[], gold_file="dummy.jsonl", retriever_type="keyword")\n\n\ndef test_load_eval_config_parses_ragas_evaluator(tmp_path: Path):\n    config = tmp_path / "rag_eval.yaml"\n    config.write_text(\n        """\nmetrics_spec_version: ngaip-415-ragas-v1\nevaluator:\n  framework: ragas\n  enabled: true\n  provider: azure_openai\n  model: eval-deployment\n  embeddings: embedding-deployment\n""".strip(),\n        encoding="utf-8",\n    )\n    loaded = load_eval_config(config)\n    assert loaded.metrics_spec_version == "ngaip-415-ragas-v1"\n    assert loaded.evaluator.enabled is True\n    assert loaded.evaluator.model == "eval-deployment"\n\n\ndef test_load_eval_config_rejects_non_ragas_framework(tmp_path: Path):\n    config = tmp_path / "rag_eval.yaml"\n    config.write_text("evaluator:\\\\n  framework: other\\\\n", encoding="utf-8")\n    with pytest.raises(ValueError, match="Unsupported evaluator framework"):\n        load_eval_config(config)\n\n\ndef test_build_retriever_rejects_unknown_type():\n    with pytest.raises(ValueError, match="Unknown retriever_type"):\n        build_retriever("unknown")\n\n\n@pytest.mark.asyncio\nasync def test_eval_runner_calls_retriever_and_returns_report_shape():\n    cfg = EvalConfig(folder_ids=[], gold_file="dummy.jsonl", top_k=2)\n    retriever = AsyncMock()\n    retriever.retrieve.return_value = [{"id": "chunk-1"}, {"id": "chunk-2"}]\n    payload = await EvalRunner(cfg, retriever=retriever).run([\n        {"question_id": "q1", "question": "What?", "gold_answer": "Answer"}\n    ])\n    assert payload["results"][0]["retrieved_count"] == 2\n    assert "context_relevancy" in payload["results"][0]["scores"]\n\n\ndef test_reporters_write_json_and_csv(tmp_path: Path):\n    JsonReporter().write(tmp_path / "report.json", {"ok": True})\n    CsvReporter().write(tmp_path / "report.csv", [{"question_id": "q1", "score": 0.5}])\n    assert json.loads((tmp_path / "report.json").read_text())["ok"] is True\n    assert "question_id" in (tmp_path / "report.csv").read_text()\n\n\ndef test_metric_result_to_dict_shape():\n    data = metric_result_to_dict(response_accuracy({"question": "Q"}, answer="A"))\n    assert data["metric_name"] == "response_accuracy"\n    assert "todo" in data["details"]\n')

    commit_transfer_changes()

    print("")
    print("[363-transfer] Done. Verify with:")
    print("  pytest tests/app_retrieval/test_eval_harness.py -v")
    print("  python manage.py rag_eval run --config app_retrieval/evaluation/config/eval_ci_fixture.yaml")


if __name__ == "__main__":
    main()
