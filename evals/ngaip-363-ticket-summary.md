# NGAIP-363 - Build RAG Evaluation Harness

## Ticket Purpose

NGAIP-363 builds the reusable Django-native harness that runs RAG evaluations against gold data, selected retrievers, RAGAS-backed metric adapters, deterministic PrattWise checks, and report writers. It is the execution layer that the metric tickets plug into.

## Runbook Decision

The harness should run inside the backend process instead of requiring a web server. Normal Django tests and evaluation commands should use Django settings, models, and retrieval helpers directly. Start `runserver` only for true HTTP end-to-end tests.

RAGAS is the primary semantic evaluator framework, while the harness keeps PrattWise-specific deterministic adapters for metadata that RAGAS cannot infer.

## Generated Files

`ngaip-363-transfer.py` should generate or update:

- `app_retrieval/evaluation/config/__init__.py`
- `app_retrieval/evaluation/config/eval_config.py`
- `app_retrieval/evaluation/config/rag_eval.yaml`
- `app_retrieval/evaluation/config/eval_sample.yaml`
- `app_retrieval/evaluation/ragas_factory.py`
- `app_retrieval/evaluation/harness.py`
- `app_retrieval/management/commands/rag_eval.py`
- `tests/app_retrieval/test_eval_harness.py`

The transfer script intentionally consolidates the harness into fewer files. `harness.py` contains the shared retriever adapters, runner, reporter helpers, and placeholder metric hooks. Later metric tickets can still replace or add focused metric modules where needed.

## Evaluator Config Ownership

This ticket owns the reusable `evaluator:` config section. The config should include:

- `framework: ragas`
- `enabled`
- `provider`, usually `azure_openai`, or `modelhub_azure_openai` when Pratt ModelHub fronts the OpenAI-compatible deployment
- evaluator model deployment
- embedding deployment
- temperature, timeout, and retry settings

`NGAIP-415` owns the report/schema contract for these fields, but `NGAIP-363` owns parsing and using them.

## RAGAS Factory Ownership

This ticket owns `app_retrieval/evaluation/ragas_factory.py`. It should use the backend convention:

```python
from app.settings_intellisense import settings
```

It should provide:

- `AzureChatOpenAI` for RAGAS judge/generator paths.
- `AzureOpenAIEmbeddings` for PrattWise default embeddings.
- `langchain_openai.OpenAIEmbeddings` for direct OpenAI embeddings when LanceDB smoke tests or non-Azure configs require it.
- `langchain_openai.llms.AzureOpenAI` for completion-style RAGAS flows when needed.
- `ragas.embeddings.OpenAIEmbeddings` as a direct OpenAI option for non-Azure experiments.
- ModelHub token/header handling when `provider: modelhub_azure_openai`, using the same OpenAI-compatible model endpoint instead of a separate evaluator path.

## Dependency Setup

The backend uses `uv sync`, so dependencies should be added through `uv` rather than only installed into an active environment:

```cmd
uv add ragas datasets lancedb
uv add langchain langchain-core langchain-openai langchain-community
uv add --dev pytest pytest-django pytest-asyncio
uv sync --group dev
```

If the runtime branch needs pinned versions, use the runbook pins:

```cmd
uv add ragas>=0.2.0 datasets>=2.14.0 lancedb
uv add langchain==0.3.10 langchain-community==0.3.4 langchain-core==0.3.21 langchain-openai==0.2.11
uv add --dev pytest==8.3.3 pytest-django==4.9.0 pytest-asyncio==0.23.8
uv sync --group dev
```

## LanceDB Ownership

This ticket owns the harness adapter path that retrieves contexts from the existing LanceDB-backed PrattWise retrieval layer. Raw LanceDB access should be limited to smoke tests or document generation helpers; production evaluation should use the same retrieval code path the application uses.

## Harness Behavior

The management command should support a flow like:

```cmd
uv run python manage.py rag_eval run --config app_retrieval/evaluation/config/rag_eval.yaml
```

For a sanitized sample golden set, use:

```cmd
uv run python manage.py rag_eval run --config app_retrieval/evaluation/config/eval_sample.yaml
```

Expected behavior:

- Load the gold JSONL from `NGAIP-362`.
- Select semantic, keyword, or hybrid retrieval.
- Call real PrattWise retrieval helpers in-process, backed by the existing LanceDB vector store.
- Run enabled metric adapters.
- Emit `report.json` and `report.csv`.
- Include evaluator metadata for reproducibility.
- Allow CI tests to run without live model credentials by mocking retrieval/model calls.

## Validation

Start with non-live structural tests:

```cmd
uv run pytest tests/app_retrieval/test_eval_harness.py -v
uv run python -c "from langchain_core.documents import Document; import ragas; print('ragas/langchain OK')"
```

Live RAGAS/model tests should be opt-in and skipped unless credentials and approved corpora are present.

## Branching and Commit Behavior

The runtime implementation should branch from the shared `ragas-rag-evaluation` parent. The transfer script still supports repeatable local use by bootstrapping from `main`, switching or creating `ngaip-363-rag-evaluation-harness`, applying files, removing obsolete split harness files, force-adding generated tests with `git add -f`, and committing locally without pushing.
## RAGAS-Primary Update

`NGAIP-363` now owns `ragas_adapter.py`, conversion into RAGAS dataset records, construction of RAGAS metric objects, and the default `ragas.evaluate()` call. `harness.py` treats deterministic citation/source checks as report supplements, not replacement metrics.

## Reasoning, Choices, and Code Breakdown

The main design choice is to make `NGAIP-363` the shared execution layer for all RAG metrics. RAGAS calls, model construction, dataset conversion, retrieval orchestration, and report writing belong in one harness so the later metric tickets stay thin and consistent.

Rejected alternatives:

- A separate runner per metric ticket: would duplicate RAGAS setup, dataset conversion, and report logic.
- Shell-only evaluation scripts: would bypass Django settings, retrieval helpers, user context, and backend models.
- Hardcoding Azure OpenAI only: insufficient because Pratt ModelHub may provide the OpenAI-compatible model endpoint in the runtime environment.

Code/file breakdown:

- `config/__init__.py`: exposes the lightweight `EvalConfig` used by the management command and harness.
- `config/eval_config.py`: parses the richer `evaluator:` config, including Azure OpenAI and ModelHub-backed provider settings.
- `config/rag_eval.yaml`: default RAGAS evaluation config.
- `config/eval_sample.yaml`: sample config pointing at `sample_gold.jsonl` for local end-to-end wiring tests.
- `ragas_factory.py`: builds LangChain/RAGAS LLM and embedding objects, centralizes Azure OpenAI and ModelHub token/header handling.
- `ragas_adapter.py`: maps ticket metric keys to RAGAS metric classes, builds RAGAS records/datasets, calls `ragas.evaluate()`, and normalizes results.
- `harness.py`: selects retrievers, collects contexts, runs RAGAS through the adapter, adds deterministic supplements, and writes report payloads.
- `management/commands/rag_eval.py`: gives the backend a Django-native command entry point.
- `test_eval_harness.py`: verifies metric mapping, record conversion, deterministic citation supplements, and that RAGAS is the primary evaluation path.

This structure lets `NGAIP-364`, `365`, and `366` plug into a common RAGAS-first flow instead of each reinventing evaluator setup.

## Runtime Setup and Test Playbook

Run from the backend repository root on the runtime machine, where `manage.py` lives. The transfer script creates or switches to `ngaip-363-rag-evaluation-harness` from base branch `main`.

```cmd
cd C:\path\to\ENCHS-PW-GenAI-Backend
py -3 C:\path\to\rag_eval\evals\ngaip-363-transfer.py
```

On macOS/Linux use:

```bash
cd /path/to/ENCHS-PW-GenAI-Backend
python3 /path/to/rag_eval/evals/ngaip-363-transfer.py
```

Set up dependencies with `uv`:

```cmd
uv add ragas datasets lancedb openai
uv add langchain==0.3.10 langchain-community==0.3.4 langchain-core==0.3.21 langchain-openai==0.2.11
uv add --dev pytest pytest-django pytest-asyncio
uv sync --group dev
```

Run structural tests first. They should not require live model credentials because RAGAS/model calls are mocked where needed.

```cmd
uv run pytest tests/app_retrieval/test_eval_harness.py -v
uv run python -c "from app_retrieval.evaluation.config import EvalConfig; print(EvalConfig(folder_ids=[], gold_file='app_retrieval/evaluation/config/ci_gold.jsonl').model_dump())"
```

To test harness wiring with the sample golden set after `NGAIP-362` or this script has generated `sample_gold.jsonl`, run:

```cmd
uv run python manage.py rag_eval run --config app_retrieval/evaluation/config/eval_sample.yaml
```

Live RAGAS evaluation requires Azure OpenAI or ModelHub-backed OpenAI-compatible credentials. For ModelHub, configure `provider: modelhub_azure_openai` and set the `MODELHUB_TOKEN_*` and `OPENAI_API_LLM_*` environment variables described in the runbook.

The transfer script force-adds generated tests automatically. If you stage manually, use:

```cmd
git add app_retrieval/evaluation/config/__init__.py app_retrieval/evaluation/config/eval_config.py app_retrieval/evaluation/ragas_factory.py app_retrieval/evaluation/ragas_adapter.py app_retrieval/evaluation/harness.py app_retrieval/management/commands/rag_eval.py app_retrieval/evaluation/config/*.yaml app_retrieval/evaluation/config/*.jsonl
git add -f tests/app_retrieval/test_eval_harness.py
git commit -m "NGAIP-363: Apply transfer script changes"
```
