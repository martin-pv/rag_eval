#!/usr/bin/env python3
"""NGAIP-363 transfer: RAGAS-primary evaluation harness."""
import subprocess
from pathlib import Path

BRANCH = 'ngaip-363-rag-evaluation-harness'
COMMIT_MESSAGE = 'NGAIP-363: Apply transfer script changes'
BASE_BRANCH = "main-backup-for-mac-claude-repo-04-07-2026"
BACKEND = Path.cwd()


def git(*args):
    subprocess.run(["git", *args], check=True)


def git_or(*args):
    return subprocess.run(["git", *args], check=False).returncode == 0


def current_branch() -> str:
    return subprocess.check_output(["git", "branch", "--show-current"], text=True).strip()


def ensure_ticket_branch() -> None:
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


def read_text_compat(path: Path) -> str:
    if not path.exists():
        return ""
    raw = path.read_bytes()
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        return raw.decode("utf-16")
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw.decode("utf-8-sig")
    for encoding in ("utf-8", "utf-16-le", "cp1252", "latin-1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            pass
    return raw.decode("latin-1")


def append_if_missing(path: Path, line: str):
    text = read_text_compat(path)
    addition = line if line.endswith("\n") else line + "\n"
    if line.rstrip() not in text:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(addition if not text else text + ("" if text.endswith("\n") else "\n") + addition, encoding="utf-8")
        print(f"  Appended: {line.strip()}")
    else:
        print(f"  Already present: {line.strip()}")


def remove_obsolete_generated_files() -> None:
    if OBSOLETE_PATHS:
        git("rm", "--ignore-unmatch", "--", *OBSOLETE_PATHS)


def commit_transfer_changes() -> None:
    existing_paths = [p for p in GENERATED_PATHS if (BACKEND / p).exists()]
    commit_paths = sorted(set(existing_paths + OBSOLETE_PATHS))
    normal_paths = [p for p in existing_paths if not p.startswith("tests/")]
    test_paths = [p for p in existing_paths if p.startswith("tests/")]
    if normal_paths:
        git("add", "--", *normal_paths)
    if test_paths:
        print(f"[363-transfer] Force-adding generated test files...")
        git("add", "-f", "--", *test_paths)
    staged = subprocess.run(["git", "diff", "--cached", "--quiet", "--", *commit_paths], check=False)
    if staged.returncode == 0:
        print(f"[363-transfer] No changes to commit.")
        return
    git("commit", "-m", COMMIT_MESSAGE, "--", *commit_paths)
    print(f"[363-transfer] Created local commit: {COMMIT_MESSAGE}")

GENERATED_PATHS = ['requirements.txt', 'app_retrieval/evaluation/__init__.py', 'app_retrieval/evaluation/config/__init__.py', 'app_retrieval/evaluation/config/eval_config.py', 'app_retrieval/evaluation/config/rag_eval.yaml', 'app_retrieval/evaluation/config/eval_default.yaml', 'app_retrieval/evaluation/config/eval_ci_fixture.yaml', 'app_retrieval/evaluation/config/ci_gold.jsonl', 'app_retrieval/evaluation/ragas_factory.py', 'app_retrieval/evaluation/ragas_adapter.py', 'app_retrieval/evaluation/harness.py', 'app_retrieval/management/__init__.py', 'app_retrieval/management/commands/__init__.py', 'app_retrieval/management/commands/rag_eval.py', 'tests/app_retrieval/__init__.py', 'tests/app_retrieval/test_eval_harness.py']
OBSOLETE_PATHS = ['app_retrieval/evaluation/config.py', 'app_retrieval/evaluation/retriever.py', 'app_retrieval/evaluation/runner.py', 'app_retrieval/evaluation/metrics/base.py', 'app_retrieval/evaluation/reporters/json_reporter.py', 'app_retrieval/evaluation/reporters/csv_reporter.py', 'tests/app_retrieval/test_eval_config.py', 'tests/app_retrieval/test_eval_runner.py']


def main():
    ensure_ticket_branch()
    for dep in ["ragas>=0.2.0", "datasets>=2.14.0", "lancedb", "openai>=1.109.1", "langchain-openai==0.2.11", "langchain-core==0.3.21", "langchain-community==0.3.4", "langchain==0.3.10"]:
        append_if_missing(BACKEND / "requirements.txt", dep)
    for init in [BACKEND / "app_retrieval" / "evaluation" / "__init__.py", BACKEND / "app_retrieval" / "evaluation" / "config" / "__init__.py", BACKEND / "app_retrieval" / "management" / "__init__.py", BACKEND / "app_retrieval" / "management" / "commands" / "__init__.py", BACKEND / "tests" / "app_retrieval" / "__init__.py"]:
        touch(init)
    remove_obsolete_generated_files()
    ensure(BACKEND / "app_retrieval" / "evaluation" / "config" / "__init__.py", 'from __future__ import annotations\n\nfrom typing import Literal\n\nfrom pydantic import BaseModel, Field, model_validator\n\n\nclass EvalConfig(BaseModel):\n    seed: int = 42\n    folder_ids: list[int]\n    retriever_type: Literal["semantic", "keyword", "hybrid"] = "semantic"\n    top_k: int = 5\n    model: str = "gpt-4o"\n    gold_file: str\n    output_dir: str = "evaluation/output"\n    metrics: list[str] = Field(default=["context_relevancy", "citation_accuracy", "response_accuracy"])\n    eval_user_id: int | None = None\n\n    @model_validator(mode="after")\n    def _require_user_for_keyword(self) -> "EvalConfig":\n        if self.retriever_type in ("keyword", "hybrid") and self.eval_user_id is None:\n            raise ValueError(f"eval_user_id is required when retriever_type is {self.retriever_type!r}")\n        return self\n')
    ensure(BACKEND / "app_retrieval" / "evaluation" / "config" / "eval_config.py", 'from __future__ import annotations\n\nfrom dataclasses import dataclass\nfrom pathlib import Path\nfrom typing import Any\n\nimport yaml\n\n\n@dataclass(frozen=True)\nclass RagasEvaluatorConfig:\n    framework: str = "ragas"\n    enabled: bool = True\n    provider: str = "azure_openai"\n    model: str | None = None\n    embeddings: str | None = None\n    temperature: float = 0\n    timeout_seconds: int = 120\n    max_retries: int = 2\n\n\n@dataclass(frozen=True)\nclass EvalConfig:\n    metrics_spec_version: str\n    evaluator: RagasEvaluatorConfig\n    raw: dict[str, Any]\n\n\ndef load_eval_config(path: Path) -> EvalConfig:\n    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}\n    evaluator = RagasEvaluatorConfig(**data.get("evaluator", {}))\n    if evaluator.framework != "ragas":\n        raise ValueError(f"Unsupported evaluator framework: {evaluator.framework}")\n    return EvalConfig(str(data.get("metrics_spec_version", "unknown")), evaluator, data)\n')
    ensure(BACKEND / "app_retrieval" / "evaluation" / "ragas_factory.py", 'from __future__ import annotations\n\nimport os\n\nfrom app.settings_intellisense import settings\nfrom langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings, OpenAIEmbeddings as LangChainOpenAIEmbeddings\nfrom langchain_openai.llms import AzureOpenAI\nfrom openai import OpenAI\nfrom ragas.embeddings import OpenAIEmbeddings\n\nfrom app_retrieval.evaluation.config.eval_config import RagasEvaluatorConfig\n\n\ndef _setting(name: str, default: str | None = None) -> str | None:\n    return getattr(settings, name, os.environ.get(name, default))\n\n\ndef build_ragas_langchain_models(config: RagasEvaluatorConfig):\n    if config.provider != "azure_openai":\n        raise ValueError(f"Unsupported RAGAS provider: {config.provider}")\n    if not config.model or not config.embeddings:\n        raise ValueError("RAGAS model and embedding deployments are required")\n    llm = AzureChatOpenAI(azure_deployment=config.model, api_key=_setting("AZURE_OPENAI_API_KEY"), azure_endpoint=_setting("AZURE_OPENAI_ENDPOINT"), api_version=_setting("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"), temperature=config.temperature, timeout=config.timeout_seconds, max_retries=config.max_retries)\n    embeddings = AzureOpenAIEmbeddings(azure_deployment=config.embeddings, api_key=_setting("AZURE_OPENAI_API_KEY"), azure_endpoint=_setting("AZURE_OPENAI_ENDPOINT"), api_version=_setting("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"))\n    return llm, embeddings\n\n\ndef build_ragas_azure_completion_llm(config: RagasEvaluatorConfig) -> AzureOpenAI:\n    return AzureOpenAI(azure_deployment=config.model, api_key=_setting("AZURE_OPENAI_API_KEY"), azure_endpoint=_setting("AZURE_OPENAI_ENDPOINT"), api_version=_setting("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"), temperature=config.temperature)\n\n\ndef build_langchain_openai_embeddings(model: str | None = None) -> LangChainOpenAIEmbeddings:\n    return LangChainOpenAIEmbeddings(model=model or _setting("OPENAI_EMBEDDINGS_MODEL", "text-embedding-3-small"), api_key=_setting("OPENAI_API_KEY"))\n\n\ndef build_ragas_openai_embeddings(api_key: str | None = None) -> OpenAIEmbeddings:\n    return OpenAIEmbeddings(client=OpenAI(api_key=api_key))\n')
    ensure(BACKEND / "app_retrieval" / "evaluation" / "ragas_adapter.py", 'from __future__ import annotations\n\nfrom dataclasses import dataclass\nfrom importlib import import_module\nfrom typing import Any, Iterable\n\n\n@dataclass(frozen=True)\nclass RagasMetricSpec:\n    ticket: str\n    metric_key: str\n    ragas_symbols: tuple[str, ...]\n    deterministic_supplements: tuple[str, ...] = ()\n\n\nRAGAS_METRIC_SPECS: dict[str, RagasMetricSpec] = {\n    "context_relevancy": RagasMetricSpec("NGAIP-365", "context_relevancy", ("LLMContextPrecisionWithoutReference", "LLMContextRecall", "ContextPrecision", "ContextRecall")),\n    "citation_accuracy": RagasMetricSpec("NGAIP-364", "citation_accuracy", ("Faithfulness", "ContextPrecision", "LLMContextPrecisionWithoutReference"), ("citation_asset_precision", "citation_asset_recall", "citation_hallucination_rate")),\n    "response_accuracy": RagasMetricSpec("NGAIP-366", "response_accuracy", ("AnswerCorrectness", "AnswerRelevancy", "ResponseRelevancy", "Faithfulness")),\n}\n\n\ndef _metric_from_symbol(symbol: str):\n    metric = getattr(import_module("ragas.metrics"), symbol, None)\n    if metric is None:\n        return None\n    return metric() if isinstance(metric, type) else metric\n\n\ndef build_ragas_metrics(metric_keys: Iterable[str]):\n    metrics = []\n    seen = set()\n    for key in metric_keys:\n        spec = RAGAS_METRIC_SPECS.get(key)\n        if spec is None:\n            raise ValueError(f"Unknown RAGAS metric key: {key}")\n        for symbol in spec.ragas_symbols:\n            metric = _metric_from_symbol(symbol)\n            if metric is not None and symbol not in seen:\n                metrics.append(metric)\n                seen.add(symbol)\n    if not metrics:\n        raise ImportError("No configured RAGAS metrics were available from ragas.metrics")\n    return metrics\n\n\ndef build_ragas_records(gold_rows: list[dict], retrieved_by_id: dict[str, list[dict]], answers_by_id: dict[str, str]) -> list[dict[str, Any]]:\n    records = []\n    for row in gold_rows:\n        qid = str(row.get("question_id") or row.get("id") or row.get("question"))\n        contexts = [c.get("context") or c.get("text") or c.get("page_content") or "" for c in retrieved_by_id.get(qid, [])]\n        response = answers_by_id.get(qid) or row.get("answer") or row.get("gold_answer") or ""\n        reference = row.get("gold_answer") or row.get("ground_truth") or row.get("reference") or ""\n        records.append({"user_input": row.get("question"), "response": response, "retrieved_contexts": contexts, "reference": reference, "question": row.get("question"), "answer": response, "contexts": contexts, "ground_truth": reference, "question_id": qid})\n    return records\n\n\ndef to_ragas_dataset(records: list[dict[str, Any]]):\n    from datasets import Dataset\n\n    return Dataset.from_list(records)\n\n\ndef run_ragas_evaluation(records: list[dict[str, Any]], metric_keys: list[str], llm=None, embeddings=None):\n    from ragas import evaluate\n\n    kwargs = {"metrics": build_ragas_metrics(metric_keys)}\n    if llm is not None:\n        kwargs["llm"] = llm\n    if embeddings is not None:\n        kwargs["embeddings"] = embeddings\n    return evaluate(to_ragas_dataset(records), **kwargs)\n\n\ndef normalize_ragas_result(result) -> dict[str, Any]:\n    if hasattr(result, "to_pandas"):\n        return {"rows": result.to_pandas().to_dict(orient="records")}\n    if isinstance(result, dict):\n        return result\n    return {"raw": result}\n\n\ndef citation_asset_overlap(model_asset_ids: list[str], gold_doc_ids: list[str], retrieved_asset_ids: list[str]) -> dict[str, float]:\n    gold = set(gold_doc_ids)\n    retrieved = set(retrieved_asset_ids)\n    if not model_asset_ids:\n        return {"citation_asset_precision": 0.0, "citation_asset_recall": 0.0, "citation_hallucination_rate": 0.0}\n    true_positive = sum(1 for asset_id in model_asset_ids if asset_id in gold)\n    hallucinated = sum(1 for asset_id in model_asset_ids if asset_id not in retrieved and asset_id not in gold)\n    return {"citation_asset_precision": round(true_positive / len(model_asset_ids), 4), "citation_asset_recall": round(true_positive / len(gold), 4) if gold else 0.0, "citation_hallucination_rate": round(hallucinated / len(model_asset_ids), 4)}\n')
    ensure(BACKEND / "app_retrieval" / "evaluation" / "harness.py", 'from __future__ import annotations\n\nimport asyncio\nimport csv\nimport json\nimport random\nfrom abc import ABC, abstractmethod\nfrom pathlib import Path\n\nfrom django.test import RequestFactory\n\nfrom app_retrieval.evaluation.config import EvalConfig\nfrom app_retrieval.evaluation.ragas_adapter import build_ragas_records, citation_asset_overlap, normalize_ragas_result, run_ragas_evaluation\n\n\nclass BaseRetriever(ABC):\n    @abstractmethod\n    async def retrieve(self, query: str, folder, top_k: int) -> list[dict]:\n        ...\n\n\nclass SemanticRetriever(BaseRetriever):\n    async def retrieve(self, query: str, folder, top_k: int) -> list[dict]:\n        from app_retrieval.data_assets.utils import search_folder_index\n        return await search_folder_index(folder, query, top_k)\n\n\nclass KeywordRetriever(BaseRetriever):\n    def __init__(self, eval_user=None) -> None:\n        self._eval_user = eval_user\n\n    async def retrieve(self, query: str, folder, top_k: int) -> list[dict]:\n        from app_retrieval.views.search import keyword_search_folder\n        request = RequestFactory().get("/")\n        request.user = self._eval_user\n        return await keyword_search_folder(request, query, folder, k=top_k)\n\n\nclass HybridRetriever(BaseRetriever):\n    def __init__(self, eval_user=None) -> None:\n        self._semantic = SemanticRetriever()\n        self._keyword = KeywordRetriever(eval_user=eval_user)\n\n    async def retrieve(self, query: str, folder, top_k: int) -> list[dict]:\n        semantic_results, keyword_results = await asyncio.gather(self._semantic.retrieve(query, folder, top_k), self._keyword.retrieve(query, folder, top_k))\n        seen: dict[int | str, dict] = {}\n        for chunk in semantic_results + keyword_results:\n            key = chunk.get("pk") or chunk.get("id") or id(chunk)\n            if key not in seen or chunk.get("score", 0) > seen[key].get("score", 0):\n                seen[key] = chunk\n        return sorted(seen.values(), key=lambda c: c.get("score", 0), reverse=True)[:top_k]\n\n\ndef build_retriever(retriever_type: str, eval_user=None) -> BaseRetriever:\n    if retriever_type == "semantic":\n        return SemanticRetriever()\n    if retriever_type == "keyword":\n        return KeywordRetriever(eval_user=eval_user)\n    if retriever_type == "hybrid":\n        return HybridRetriever(eval_user=eval_user)\n    raise ValueError(f"Unknown retriever_type: {retriever_type!r}")\n\n\nclass JsonReporter:\n    def write(self, path: Path, payload: dict) -> None:\n        path.parent.mkdir(parents=True, exist_ok=True)\n        path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")\n\n\nclass CsvReporter:\n    def write(self, path: Path, rows: list[dict]) -> None:\n        path.parent.mkdir(parents=True, exist_ok=True)\n        if not rows:\n            path.write_text("", encoding="utf-8")\n            return\n        with path.open("w", newline="", encoding="utf-8") as handle:\n            writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))\n            writer.writeheader()\n            writer.writerows(rows)\n\n\nclass EvalRunner:\n    def __init__(self, config: EvalConfig, retriever: BaseRetriever | None = None, llm=None, embeddings=None) -> None:\n        self.config = config\n        self.retriever = retriever or build_retriever(config.retriever_type)\n        self.llm = llm\n        self.embeddings = embeddings\n\n    def _seeded_rows(self, gold_rows: list[dict]) -> list[dict]:\n        rows = list(gold_rows)\n        random.Random(self.config.seed).shuffle(rows)\n        return rows\n\n    async def run(self, gold_rows: list[dict], folder=None, answers_by_id: dict[str, str] | None = None) -> dict:\n        answers_by_id = answers_by_id or {}\n        retrieved_by_id: dict[str, list[dict]] = {}\n        for row in self._seeded_rows(gold_rows):\n            qid = str(row.get("question_id") or row.get("question"))\n            retrieved_by_id[qid] = await self.retriever.retrieve(row["question"], folder, self.config.top_k)\n        records = build_ragas_records(gold_rows, retrieved_by_id, answers_by_id)\n        ragas_result = await asyncio.to_thread(run_ragas_evaluation, records, self.config.metrics, self.llm, self.embeddings)\n        supplements = {str(row.get("question_id") or row.get("question")): citation_asset_overlap([s.get("asset_id", "") for s in row.get("model_sources", [])], [row.get("gold_doc_id", "")], [c.get("asset_id", "") for c in retrieved_by_id.get(str(row.get("question_id") or row.get("question")), [])]) for row in gold_rows}\n        return {"config": self.config.model_dump(), "ragas": normalize_ragas_result(ragas_result), "deterministic_supplements": supplements, "records": records}\n')
    ensure(BACKEND / "app_retrieval" / "management" / "commands" / "rag_eval.py", 'from __future__ import annotations\n\nimport json\nfrom pathlib import Path\n\nimport yaml\nfrom django.core.management.base import BaseCommand, CommandError\n\nfrom app_retrieval.evaluation.config import EvalConfig\nfrom app_retrieval.evaluation.harness import CsvReporter, EvalRunner, JsonReporter\n\n\nclass Command(BaseCommand):\n    help = "Run PrattWise RAGAS-primary RAG evaluation harness."\n\n    def add_arguments(self, parser):\n        parser.add_argument("run", nargs="?")\n        parser.add_argument("--config", required=True)\n\n    def handle(self, *args, **options):\n        config_path = Path(options["config"])\n        if not config_path.exists():\n            raise CommandError(f"Config not found: {config_path}")\n        config = EvalConfig(**(yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}))\n        gold_path = Path(config.gold_file)\n        if not gold_path.exists():\n            raise CommandError(f"Gold file not found: {gold_path}")\n        gold_rows = [json.loads(line) for line in gold_path.read_text(encoding="utf-8").splitlines() if line.strip()]\n        import asyncio\n        payload = asyncio.run(EvalRunner(config).run(gold_rows))\n        output_dir = Path(config.output_dir)\n        JsonReporter().write(output_dir / "report.json", payload)\n        CsvReporter().write(output_dir / "ragas_records.csv", payload["records"])\n        self.stdout.write(self.style.SUCCESS(f"Wrote RAGAS reports to {output_dir}"))\n')
    ensure(BACKEND / "app_retrieval" / "evaluation" / "config" / "rag_eval.yaml", "seed: 42\nfolder_ids: []\nretriever_type: semantic\ntop_k: 5\nmodel: gpt-4o\ngold_file: app_retrieval/evaluation/config/ci_gold.jsonl\noutput_dir: evaluation/output\nmetrics:\n  - context_relevancy\n  - citation_accuracy\n  - response_accuracy\n")
    ensure(BACKEND / "app_retrieval" / "evaluation" / "config" / "eval_default.yaml", "seed: 42\nfolder_ids: []\nretriever_type: semantic\ntop_k: 5\nmodel: gpt-4o\ngold_file: app_retrieval/evaluation/config/ci_gold.jsonl\noutput_dir: evaluation/output\nmetrics:\n  - context_relevancy\n  - citation_accuracy\n  - response_accuracy\n")
    ensure(BACKEND / "app_retrieval" / "evaluation" / "config" / "eval_ci_fixture.yaml", "seed: 42\nfolder_ids: []\nretriever_type: semantic\ntop_k: 2\nmodel: ci-mock\ngold_file: app_retrieval/evaluation/config/ci_gold.jsonl\noutput_dir: evaluation/output/ci\nmetrics:\n  - context_relevancy\n  - citation_accuracy\n  - response_accuracy\n")
    ensure(BACKEND / "app_retrieval" / "evaluation" / "config" / "ci_gold.jsonl", '{"question_id":"ci-001","question":"What is the maintenance interval for component X?","gold_answer":"Component X requires maintenance every 500 flight hours.","gold_doc_id":"ci-asset-001"}\n')
    ensure(BACKEND / "tests" / "app_retrieval" / "test_eval_harness.py", 'from __future__ import annotations\n\nfrom unittest.mock import AsyncMock, patch\n\nimport pytest\n\nfrom app_retrieval.evaluation.config import EvalConfig\nfrom app_retrieval.evaluation.harness import EvalRunner\nfrom app_retrieval.evaluation.ragas_adapter import RAGAS_METRIC_SPECS, build_ragas_records, citation_asset_overlap\n\n\ndef test_metric_map_is_ragas_primary_for_all_rag_tickets():\n    assert RAGAS_METRIC_SPECS["context_relevancy"].ticket == "NGAIP-365"\n    assert RAGAS_METRIC_SPECS["citation_accuracy"].ticket == "NGAIP-364"\n    assert RAGAS_METRIC_SPECS["response_accuracy"].ticket == "NGAIP-366"\n    assert "Faithfulness" in RAGAS_METRIC_SPECS["citation_accuracy"].ragas_symbols\n\n\ndef test_build_ragas_records_uses_canonical_columns():\n    records = build_ragas_records([{"question_id": "q1", "question": "Q?", "gold_answer": "Gold"}], {"q1": [{"context": "ctx", "asset_id": "doc"}]}, {"q1": "Model"})\n    assert records[0]["user_input"] == "Q?"\n    assert records[0]["response"] == "Model"\n    assert records[0]["retrieved_contexts"] == ["ctx"]\n    assert records[0]["reference"] == "Gold"\n\n\ndef test_citation_asset_overlap_is_supplemental_not_primary():\n    assert citation_asset_overlap(["ghost"], ["gold"], ["retrieved"])["citation_hallucination_rate"] == 1.0\n\n\n@pytest.mark.asyncio\nasync def test_eval_runner_calls_ragas_evaluation_as_primary_path():\n    cfg = EvalConfig(folder_ids=[], gold_file="dummy.jsonl", top_k=1)\n    retriever = AsyncMock()\n    retriever.retrieve.return_value = [{"context": "ctx", "asset_id": "doc"}]\n    with patch("app_retrieval.evaluation.harness.run_ragas_evaluation", return_value={"faithfulness": 1.0}) as evaluate_mock:\n        payload = await EvalRunner(cfg, retriever=retriever).run([{"question_id": "q1", "question": "Q?", "gold_answer": "Gold", "gold_doc_id": "doc"}], answers_by_id={"q1": "Model"})\n    evaluate_mock.assert_called_once()\n    assert payload["ragas"]["faithfulness"] == 1.0\n')
    commit_transfer_changes()
    print("[363-transfer] Done. Verify with: pytest tests/app_retrieval/test_eval_harness.py -v")


if __name__ == "__main__":
    main()
