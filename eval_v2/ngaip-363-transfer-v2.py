#!/usr/bin/env python3
"""NGAIP-363 v2: async-first RAGAS harness and model factory.

Reuses the existing PrattWise ModelHub plumbing:
- token mint:    app_background.background_tasks.modelhub.periodic_modelhub_processor
- token consume: cache.aget("MODELHUB_TOKEN")  (same as app_chatbot.utils etc.)
"""
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


BRANCH = 'ngaip-363-rag-evaluation-harness-v2'
COMMIT_MESSAGE = 'NGAIP-363: Apply v2 async RAGAS harness changes'

SAMPLE_GOLD_JSONL = Path(__file__).with_name("sample_gold_v2.jsonl").read_text(encoding="utf-8")

ASYNC_RUNNER = "from __future__ import annotations\n\nimport asyncio\nfrom dataclasses import dataclass\nfrom typing import Awaitable, Callable, Iterable, Sequence\n\nfrom datasets import Dataset\nfrom ragas import evaluate\nfrom ragas.metrics import answer_correctness, answer_relevancy, context_precision, context_recall, faithfulness\n\nfrom app_retrieval.evaluation.config.gold_schema import GoldRow\n\nAnswerFn = Callable[[GoldRow, list[str]], Awaitable[str]]\nRetrieveFn = Callable[[GoldRow], Awaitable[list[str]]]\n\n\n@dataclass(slots=True)\nclass RagasCaseResult:\n    question_id: str\n    question: str\n    response: str\n    retrieved_contexts: list[str]\n    reference: str\n\n    def to_record(self) -> dict:\n        return {\"user_input\": self.question, \"response\": self.response, \"retrieved_contexts\": self.retrieved_contexts, \"reference\": self.reference}\n\n\ndef default_metrics(names: Sequence[str] | None = None) -> list:\n    mapping = {\"faithfulness\": faithfulness, \"answer_relevancy\": answer_relevancy, \"answer_correctness\": answer_correctness, \"context_precision\": context_precision, \"context_recall\": context_recall}\n    selected = names or list(mapping)\n    return [mapping[name] for name in selected if name in mapping]\n\n\nasync def collect_ragas_cases(rows: Iterable[GoldRow], retrieve: RetrieveFn, answer: AnswerFn) -> list[RagasCaseResult]:\n    async def one(row: GoldRow) -> RagasCaseResult:\n        contexts = await retrieve(row)\n        response = await answer(row, contexts)\n        return RagasCaseResult(row.question_id, row.question, response, contexts, row.gold_answer)\n    return await asyncio.gather(*(one(row) for row in rows))\n\n\nasync def aevaluate_cases(cases: Sequence[RagasCaseResult], *, metrics: Sequence | None = None, llm=None, embeddings=None):\n    dataset = Dataset.from_list([case.to_record() for case in cases])\n    return await asyncio.to_thread(evaluate, dataset, metrics=list(metrics or default_metrics()), llm=llm, embeddings=embeddings)\n"
FACTORY = "from __future__ import annotations\n\nimport os\nfrom dataclasses import dataclass\nfrom typing import Any\n\nfrom openai import AsyncOpenAI\nfrom ragas.llms import LangchainLLMWrapper, llm_factory\nfrom ragas.metrics import DiscreteMetric\n\n# ModelHub token is minted by app_background.background_tasks.modelhub.periodic_modelhub_processor\n# and stored in Django's cache as \"MODELHUB_TOKEN\". Every other LLM consumer\n# (app_chatbot.utils, app_chatbot.views.chatstream, app_retrieval.api_lancedb,\n# app_core.utils) reads it via cache.aget. RAGAS reuses the same source.\ntry:\n    from django.core.cache import cache as _django_cache\nexcept Exception:\n    _django_cache = None\n\ntry:\n    from app.settings_intellisense import settings as _settings\nexcept Exception:\n    _settings = None\n\n\n@dataclass(frozen=True)\nclass EvaluatorModelConfig:\n    model: str = \"gpt-4o\"\n    provider: str = \"openai\"  # openai | azure_openai | modelhub_azure_openai\n    api_key: str | None = None\n    base_url: str | None = None\n    azure_endpoint: str | None = None\n    api_version: str | None = None\n    deployment: str | None = None\n    timeout_seconds: int = 120\n\n\ndef _setting(name: str, default: str | None = None) -> str | None:\n    if _settings is not None:\n        value = getattr(_settings, name, None)\n        if value is not None:\n            return value\n    return os.environ.get(name, default)\n\n\ndef _first(*values: str | None) -> str | None:\n    return next((value for value in values if value), None)\n\n\nasync def aget_modelhub_token() -> str | None:\n    \"\"\"Read the current ModelHub bearer token from Django's cache.\n\n    Reuses the cache populated by app_background.background_tasks.modelhub.periodic_modelhub_processor.\n    Returns None when the cache layer is unavailable or the key is unset\n    (e.g. tests, or settings.USE_OPENAI_DIRECT, or before the refresh task has run).\n    \"\"\"\n    if _django_cache is None:\n        return None\n    return await _django_cache.aget(\"MODELHUB_TOKEN\", None)\n\n\ndef build_modelhub_default_headers(config: EvaluatorModelConfig, *, modelhub_token: str | None) -> dict[str, str]:\n    \"\"\"Mirror app_chatbot.utils.OpenAIStreamGenerator: api-key + Ocp-Apim + optional Bearer.\"\"\"\n    api_key = _first(config.api_key, _setting(\"OPENAI_API_LLM_KEY\"), _setting(\"AZURE_OPENAI_API_KEY\"))\n    headers: dict[str, str] = {\"Content-Type\": \"application/json\"}\n    if api_key:\n        headers[\"api-key\"] = api_key\n        headers[\"Ocp-Apim-Subscription-Key\"] = api_key\n    if modelhub_token:\n        headers[\"Authorization\"] = f\"Bearer {modelhub_token}\"\n    return headers\n\n\nasync def abuild_async_openai_client(config: EvaluatorModelConfig) -> AsyncOpenAI:\n    \"\"\"Build an AsyncOpenAI client; pulls the ModelHub token from Django cache when needed.\"\"\"\n    if config.provider == \"modelhub_azure_openai\":\n        token = await aget_modelhub_token()\n        return AsyncOpenAI(\n            api_key=_first(config.api_key, _setting(\"OPENAI_API_LLM_KEY\"), _setting(\"AZURE_OPENAI_API_KEY\")),\n            base_url=_first(config.azure_endpoint, _setting(\"OPENAI_API_LLM_ENDPOINT\"), _setting(\"AZURE_OPENAI_ENDPOINT\")),\n            default_headers=build_modelhub_default_headers(config, modelhub_token=token),\n        )\n    if config.provider == \"azure_openai\":\n        return AsyncOpenAI(\n            api_key=_first(config.api_key, _setting(\"AZURE_OPENAI_API_KEY\")),\n            base_url=_first(config.azure_endpoint, _setting(\"AZURE_OPENAI_ENDPOINT\")),\n        )\n    return AsyncOpenAI(\n        api_key=_first(config.api_key, _setting(\"OPENAI_API_KEY\")),\n        base_url=_first(config.base_url, _setting(\"OPENAI_BASE_URL\")),\n    )\n\n\nasync def abuild_ragas_async_llm(config: EvaluatorModelConfig):\n    return llm_factory(config.model, client=await abuild_async_openai_client(config))\n\n\ndef build_discrete_metric(name: str, prompt: str, allowed_values: list[str] | None = None) -> DiscreteMetric:\n    return DiscreteMetric(name=name, allowed_values=allowed_values or [\"pass\", \"fail\"], prompt=prompt)\n\n\nasync def ascore_discrete_metric(metric: DiscreteMetric, *, config: EvaluatorModelConfig, **kwargs: Any):\n    return await metric.ascore(llm=await abuild_ragas_async_llm(config), **kwargs)\n\n\ndef build_langchain_wrappers(llm, embeddings):\n    from ragas.embeddings import LangchainEmbeddingsWrapper\n    return LangchainLLMWrapper(llm), LangchainEmbeddingsWrapper(embeddings)\n"
CONFIG = "from __future__ import annotations\n\nfrom dataclasses import dataclass, field\nfrom pathlib import Path\nimport yaml\n\n\n@dataclass(frozen=True)\nclass EvalV2Config:\n    gold_file: Path\n    output_dir: Path = Path(\"evaluation/output/v2\")\n    metrics: list[str] = field(default_factory=lambda: [\"faithfulness\", \"answer_relevancy\", \"answer_correctness\", \"context_precision\", \"context_recall\"])\n    model: str = \"gpt-4o\"\n    top_k: int = 5\n\n\ndef load_eval_v2_config(path: str | Path) -> EvalV2Config:\n    data = yaml.safe_load(Path(path).read_text(encoding=\"utf-8\")) or {}\n    defaults = EvalV2Config(Path(\"app_retrieval/evaluation/config/sample_gold.jsonl\"))\n    return EvalV2Config(gold_file=Path(data.get(\"gold_file\", defaults.gold_file)), output_dir=Path(data.get(\"output_dir\", defaults.output_dir)), metrics=list(data.get(\"metrics\") or defaults.metrics), model=data.get(\"model\", defaults.model), top_k=int(data.get(\"top_k\", defaults.top_k)))\n"
TESTS = "import asyncio\n\nfrom app_retrieval.evaluation.async_ragas_runner import collect_ragas_cases, default_metrics\nfrom app_retrieval.evaluation.config.gold_schema import GoldRow\nfrom app_retrieval.evaluation.ragas_factory_v2 import (\n    EvaluatorModelConfig,\n    build_discrete_metric,\n    build_modelhub_default_headers,\n)\n\n\ndef test_default_metrics_use_ragas_objects():\n    assert {getattr(metric, \"name\", \"\") for metric in default_metrics()} >= {\"faithfulness\", \"answer_relevancy\"}\n\n\ndef test_discrete_metric_builds_for_citation_judgment():\n    metric = build_discrete_metric(\"citation_support\", \"Response: {response}\")\n    assert metric.name == \"citation_support\"\n\n\ndef test_collect_ragas_cases_is_async():\n    row = GoldRow(question_id=\"q1\", question=\"Q?\", gold_answer=\"A\", gold_doc_id=\"doc\", reference_contexts=[\"ctx\"])\n\n    async def retrieve(_row):\n        return [\"ctx\"]\n\n    async def answer(_row, _contexts):\n        return \"A\"\n\n    cases = asyncio.run(collect_ragas_cases([row], retrieve, answer))\n    assert cases[0].to_record()[\"retrieved_contexts\"] == [\"ctx\"]\n\n\ndef test_modelhub_headers_match_chatstream_layout_when_token_present():\n    config = EvaluatorModelConfig(provider=\"modelhub_azure_openai\", api_key=\"k123\")\n    headers = build_modelhub_default_headers(config, modelhub_token=\"bearer-xyz\")\n    assert headers[\"Authorization\"] == \"Bearer bearer-xyz\"\n    assert headers[\"api-key\"] == \"k123\"\n    assert headers[\"Ocp-Apim-Subscription-Key\"] == \"k123\"\n\n\ndef test_modelhub_headers_omit_bearer_when_token_unset():\n    config = EvaluatorModelConfig(provider=\"modelhub_azure_openai\", api_key=\"k123\")\n    headers = build_modelhub_default_headers(config, modelhub_token=None)\n    assert \"Authorization\" not in headers\n    assert headers[\"api-key\"] == \"k123\"\n"

def main() -> None:
    prepare_branch(BRANCH)
    touch("app_retrieval/__init__.py")
    touch("app_retrieval/evaluation/__init__.py")
    touch("app_retrieval/evaluation/config/__init__.py")
    touch("tests/__init__.py")
    touch("tests/app_retrieval/__init__.py")
    paths = [
        "app_retrieval/evaluation/async_ragas_runner.py",
        "app_retrieval/evaluation/ragas_factory_v2.py",
        "app_retrieval/evaluation/config/eval_config_v2.py",
        "app_retrieval/evaluation/config/sample_gold.jsonl",
    ]
    write(paths[0], ASYNC_RUNNER)
    write(paths[1], FACTORY)
    write(paths[2], CONFIG)
    write(paths[3], SAMPLE_GOLD_JSONL)
    test = "tests/app_retrieval/test_async_ragas_runner_v2.py"
    write(test, TESTS)
    run_pytest([test])
    commit(
        paths
        + [
            "app_retrieval/__init__.py",
            "app_retrieval/evaluation/__init__.py",
            "app_retrieval/evaluation/config/__init__.py",
            "tests/__init__.py",
            "tests/app_retrieval/__init__.py",
        ],
        [test],
        COMMIT_MESSAGE,
    )


if __name__ == "__main__":
    main()
