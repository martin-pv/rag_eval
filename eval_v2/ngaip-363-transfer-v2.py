#!/usr/bin/env python3
"""NGAIP-363 v2: async-first RAGAS harness and model factory."""
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

BRANCH = 'ngaip-363-rag-evaluation-harness-v2'
COMMIT_MESSAGE = 'NGAIP-363: Apply v2 async RAGAS harness changes'

SAMPLE_GOLD_JSONL = Path(__file__).with_name("sample_gold_v2.jsonl").read_text(encoding="utf-8")
ASYNC_RUNNER = 'from __future__ import annotations\n\nimport asyncio\nfrom dataclasses import dataclass\nfrom typing import Awaitable, Callable, Iterable, Sequence\n\nfrom datasets import Dataset\nfrom ragas import evaluate\nfrom ragas.metrics import answer_correctness, answer_relevancy, context_precision, context_recall, faithfulness\n\nfrom app_retrieval.evaluation.config.gold_schema import GoldRow\n\nAnswerFn = Callable[[GoldRow, list[str]], Awaitable[str]]\nRetrieveFn = Callable[[GoldRow], Awaitable[list[str]]]\n\n\n@dataclass(slots=True)\nclass RagasCaseResult:\n    question_id: str\n    question: str\n    response: str\n    retrieved_contexts: list[str]\n    reference: str\n\n    def to_record(self) -> dict:\n        return {"user_input": self.question, "response": self.response, "retrieved_contexts": self.retrieved_contexts, "reference": self.reference}\n\n\ndef default_metrics(names: Sequence[str] | None = None) -> list:\n    mapping = {"faithfulness": faithfulness, "answer_relevancy": answer_relevancy, "answer_correctness": answer_correctness, "context_precision": context_precision, "context_recall": context_recall}\n    selected = names or list(mapping)\n    return [mapping[name] for name in selected if name in mapping]\n\n\nasync def collect_ragas_cases(rows: Iterable[GoldRow], retrieve: RetrieveFn, answer: AnswerFn) -> list[RagasCaseResult]:\n    async def one(row: GoldRow) -> RagasCaseResult:\n        contexts = await retrieve(row)\n        response = await answer(row, contexts)\n        return RagasCaseResult(row.question_id, row.question, response, contexts, row.gold_answer)\n    return await asyncio.gather(*(one(row) for row in rows))\n\n\nasync def aevaluate_cases(cases: Sequence[RagasCaseResult], *, metrics: Sequence | None = None, llm=None, embeddings=None):\n    dataset = Dataset.from_list([case.to_record() for case in cases])\n    return await asyncio.to_thread(evaluate, dataset, metrics=list(metrics or default_metrics()), llm=llm, embeddings=embeddings)\n'
FACTORY = "from __future__ import annotations\n\nimport json\nimport os\nfrom dataclasses import dataclass\nfrom datetime import datetime, timedelta\nfrom pathlib import Path\nfrom typing import Any\n\nfrom openai import AsyncOpenAI\nfrom ragas.llms import LangchainLLMWrapper, llm_factory\nfrom ragas.metrics import DiscreteMetric\n\ntry:\n    from app.settings_intellisense import settings as _settings\nexcept Exception:\n    _settings = None\n\n_MODELHUB_CACHE = Path(\"app_retrieval/evaluation/config/modelhub_token_cache_v2.json\")\n\n\n@dataclass(frozen=True)\nclass EvaluatorModelConfig:\n    model: str = \"gpt-4o\"\n    provider: str = \"openai\"\n    api_key: str | None = None\n    base_url: str | None = None\n    azure_endpoint: str | None = None\n    api_version: str | None = None\n    modelhub_token_endpoint: str | None = None\n    modelhub_client_id: str | None = None\n    modelhub_client_secret: str | None = None\n    modelhub_scope: str | None = None\n    timeout_seconds: int = 120\n\n\ndef _setting(name: str, default: str | None = None) -> str | None:\n    if _settings is not None:\n        value = getattr(_settings, name, None)\n        if value is not None:\n            return value\n    return os.environ.get(name, default)\n\n\ndef _first(*values: str | None) -> str | None:\n    return next((value for value in values if value), None)\n\n\ndef _load_cached_token() -> str | None:\n    if not _MODELHUB_CACHE.exists():\n        return None\n    try:\n        data = json.loads(_MODELHUB_CACHE.read_text(encoding=\"utf-8\"))\n        if datetime.fromisoformat(data[\"expired_date\"]) > datetime.now():\n            return data[\"token\"]\n    except Exception:\n        return None\n    return None\n\n\ndef _save_token(token: str) -> None:\n    _MODELHUB_CACHE.parent.mkdir(parents=True, exist_ok=True)\n    _MODELHUB_CACHE.write_text(\n        json.dumps({\"token\": token, \"expired_date\": (datetime.now() + timedelta(minutes=50)).isoformat()}),\n        encoding=\"utf-8\",\n    )\n\n\ndef get_modelhub_token(config: EvaluatorModelConfig) -> str:\n    cached = _load_cached_token()\n    if cached:\n        return cached\n    import requests\n    endpoint = _first(config.modelhub_token_endpoint, _setting(\"MODELHUB_TOKEN_ENDPOINT\"))\n    if not endpoint:\n        raise ValueError(\"MODELHUB_TOKEN_ENDPOINT is required for modelhub_azure_openai\")\n    response = requests.post(\n        endpoint,\n        data={\n            \"client_id\": _first(config.modelhub_client_id, _setting(\"MODELHUB_TOKEN_CLIENT_ID\")),\n            \"client_secret\": _first(config.modelhub_client_secret, _setting(\"MODELHUB_TOKEN_CLIENT_SECRET\")),\n            \"scope\": _first(config.modelhub_scope, _setting(\"MODELHUB_TOKEN_SCOPE\")),\n            \"grant_type\": \"client_credentials\",\n        },\n        headers={\"Content-Type\": \"application/x-www-form-urlencoded\"},\n        timeout=config.timeout_seconds,\n    )\n    response.raise_for_status()\n    token = response.json()[\"access_token\"]\n    _save_token(token)\n    return token\n\n\ndef modelhub_default_headers(config: EvaluatorModelConfig) -> dict[str, str]:\n    api_key = _first(config.api_key, _setting(\"OPENAI_API_LLM_KEY\"), _setting(\"AZURE_OPENAI_API_KEY\"))\n    headers = {\"Authorization\": f\"Bearer {get_modelhub_token(config)}\"}\n    if api_key:\n        headers[\"api-key\"] = api_key\n        headers[\"Ocp-Apim-Subscription-Key\"] = api_key\n    return headers\n\n\ndef build_async_openai_client(config: EvaluatorModelConfig) -> AsyncOpenAI:\n    if config.provider == \"modelhub_azure_openai\":\n        return AsyncOpenAI(\n            api_key=_first(config.api_key, _setting(\"OPENAI_API_LLM_KEY\"), _setting(\"AZURE_OPENAI_API_KEY\")),\n            base_url=_first(config.azure_endpoint, _setting(\"OPENAI_API_LLM_ENDPOINT\"), _setting(\"AZURE_OPENAI_ENDPOINT\")),\n            default_headers=modelhub_default_headers(config),\n        )\n    if config.provider == \"azure_openai\":\n        return AsyncOpenAI(\n            api_key=_first(config.api_key, _setting(\"AZURE_OPENAI_API_KEY\")),\n            base_url=_first(config.azure_endpoint, _setting(\"AZURE_OPENAI_ENDPOINT\")),\n        )\n    return AsyncOpenAI(\n        api_key=_first(config.api_key, _setting(\"OPENAI_API_KEY\")),\n        base_url=_first(config.base_url, _setting(\"OPENAI_BASE_URL\")),\n    )\n\n\ndef build_ragas_async_llm(config: EvaluatorModelConfig):\n    return llm_factory(config.model, client=build_async_openai_client(config))\n\n\ndef build_discrete_metric(name: str, prompt: str, allowed_values: list[str] | None = None) -> DiscreteMetric:\n    return DiscreteMetric(name=name, allowed_values=allowed_values or [\"pass\", \"fail\"], prompt=prompt)\n\n\nasync def ascore_discrete_metric(metric: DiscreteMetric, *, config: EvaluatorModelConfig, **kwargs: Any):\n    return await metric.ascore(llm=build_ragas_async_llm(config), **kwargs)\n\n\ndef build_langchain_wrappers(llm, embeddings):\n    from ragas.embeddings import LangchainEmbeddingsWrapper\n    return LangchainLLMWrapper(llm), LangchainEmbeddingsWrapper(embeddings)\n"
CONFIG = 'from __future__ import annotations\n\nfrom dataclasses import dataclass, field\nfrom pathlib import Path\nimport yaml\n\n\n@dataclass(frozen=True)\nclass EvalV2Config:\n    gold_file: Path\n    output_dir: Path = Path("evaluation/output/v2")\n    metrics: list[str] = field(default_factory=lambda: ["faithfulness", "answer_relevancy", "answer_correctness", "context_precision", "context_recall"])\n    model: str = "gpt-4o"\n    top_k: int = 5\n\n\ndef load_eval_v2_config(path: str | Path) -> EvalV2Config:\n    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}\n    defaults = EvalV2Config(Path("app_retrieval/evaluation/config/sample_gold.jsonl"))\n    return EvalV2Config(gold_file=Path(data.get("gold_file", defaults.gold_file)), output_dir=Path(data.get("output_dir", defaults.output_dir)), metrics=list(data.get("metrics") or defaults.metrics), model=data.get("model", defaults.model), top_k=int(data.get("top_k", defaults.top_k)))\n'
TESTS = "import asyncio\nfrom unittest.mock import patch\n\nfrom app_retrieval.evaluation.async_ragas_runner import collect_ragas_cases, default_metrics\nfrom app_retrieval.evaluation.config.gold_schema import GoldRow\nfrom app_retrieval.evaluation.ragas_factory_v2 import EvaluatorModelConfig, build_discrete_metric, modelhub_default_headers\n\n\ndef test_default_metrics_use_ragas_objects():\n    assert {getattr(metric, \"name\", \"\") for metric in default_metrics()} >= {\"faithfulness\", \"answer_relevancy\"}\n\n\ndef test_discrete_metric_builds_for_citation_judgment():\n    metric = build_discrete_metric(\"citation_support\", \"Response: {response}\")\n    assert metric.name == \"citation_support\"\n\n\ndef test_collect_ragas_cases_is_async():\n    row = GoldRow(question_id=\"q1\", question=\"Q?\", gold_answer=\"A\", gold_doc_id=\"doc\", reference_contexts=[\"ctx\"])\n\n    async def retrieve(_row):\n        return [\"ctx\"]\n\n    async def answer(_row, _contexts):\n        return \"A\"\n\n    cases = asyncio.run(collect_ragas_cases([row], retrieve, answer))\n    assert cases[0].to_record()[\"retrieved_contexts\"] == [\"ctx\"]\n\n\ndef test_modelhub_headers_set_authorization_and_apim_keys():\n    config = EvaluatorModelConfig(provider=\"modelhub_azure_openai\", api_key=\"k123\")\n    with patch(\"app_retrieval.evaluation.ragas_factory_v2.get_modelhub_token\", return_value=\"bearer-xyz\"):\n        headers = modelhub_default_headers(config)\n    assert headers[\"Authorization\"] == \"Bearer bearer-xyz\"\n    assert headers[\"api-key\"] == \"k123\"\n    assert headers[\"Ocp-Apim-Subscription-Key\"] == \"k123\"\n"

def main() -> None:
    prepare_branch(BRANCH)
    touch("app_retrieval/__init__.py")
    touch("app_retrieval/evaluation/__init__.py")
    touch("app_retrieval/evaluation/config/__init__.py")
    touch("tests/__init__.py")
    touch("tests/app_retrieval/__init__.py")
    paths = ["app_retrieval/evaluation/async_ragas_runner.py", "app_retrieval/evaluation/ragas_factory_v2.py", "app_retrieval/evaluation/config/eval_config_v2.py", "app_retrieval/evaluation/config/sample_gold.jsonl"]
    write(paths[0], ASYNC_RUNNER)
    write(paths[1], FACTORY)
    write(paths[2], CONFIG)
    write(paths[3], SAMPLE_GOLD_JSONL)
    test = "tests/app_retrieval/test_async_ragas_runner_v2.py"
    write(test, TESTS)
    run_pytest([test])
    commit(paths + ["app_retrieval/__init__.py", "app_retrieval/evaluation/__init__.py", "app_retrieval/evaluation/config/__init__.py", "tests/__init__.py", "tests/app_retrieval/__init__.py"], [test], COMMIT_MESSAGE)

if __name__ == "__main__":
    main()

