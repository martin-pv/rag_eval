# RAGAS Implementation Runbook for NGAIP RAG Evaluation

## Purpose

This runbook describes how to implement the NGAIP RAG evaluation tickets on the actual runtime computer using a RAGAS-first approach.

The intended branch model is:

- One parent integration branch for the whole RAGAS evaluation effort.
- One sub-branch per NGAIP ticket.
- Each ticket branch should be created locally from the RAGAS parent branch, not directly from `main`, after the parent branch has been created from the local backend backup branch.

The transfer scripts in this repository are still useful as repeatable generators, but the actual runtime machine should use Git branches and commits to preserve each ticket as reviewable work.

## High-Level Decision

Use the `ragas` library as the primary evaluator framework for semantic RAG quality:

- Context relevance should use RAGAS context metrics.
- Grounding should use RAGAS faithfulness/grounding metrics.
- Response quality should use RAGAS answer correctness and answer relevancy metrics.
- Testset creation should use the RAGAS testset generator to produce candidate questions, answers, and references from approved source documents.

Keep deterministic PrattWise-specific checks where RAGAS does not know enough about backend metadata:

- Gold dataset schema validation.
- Source `asset_id` matching.
- Citation precision and recall.
- Hallucinated citation detection.
- Token-overlap diagnostics for cheap CI smoke tests and original acceptance-criteria compatibility.

## Why RAGAS

RAGAS is better than pure token overlap for this program because the RAG answers and retrieved contexts can be semantically correct without sharing exact words. The evaluation needs to answer questions like "did the retrieved context support the reference answer?" and "is this generated answer grounded?" Those are semantic judgments, and RAGAS provides standard metrics for them.

RAGAS does not replace every backend-specific check. PrattWise still needs deterministic validation for metadata and source linkage because RAGAS does not understand PrattWise `asset_id`, page/span references, folder ids, `ChatResponse.sources`, or internal citation structures unless we adapt those fields into its input format.

## Branch Strategy

### Parent Branch

Create one parent branch for all RAGAS evaluation work:

```cmd
cd path\to\Pratt-Backend\backend
git switch main-backup-for-mac-claude-repo-04-07-2026
git switch -c ragas-rag-evaluation
```

This branch should contain shared setup that every ticket needs:

- Dependency setup for `ragas`, `datasets`, `pytest`, `pytest-django`, and `pytest-asyncio`.
- Shared evaluation package directories.
- Shared RAGAS adapter utilities.
- Shared report metadata fields.
- Shared test fixtures.

Commit the parent setup locally:

```cmd
git add pyproject.toml uv.lock requirements.txt pytest.ini app_retrieval tests
git commit -m "NGAIP: Add RAGAS evaluation foundation"
```

Do not publish unless the team explicitly wants this branch on GitHub.

### Ticket Branches

Create sub-branches from the parent branch:

```cmd
git switch ragas-rag-evaluation
git switch -c ngaip-362-corpus-gold-dataset
```

After finishing a ticket:

```cmd
git add app_retrieval tests
git commit -m "NGAIP-362: Add gold dataset schema and fixtures"
git switch ragas-rag-evaluation
git merge --no-ff ngaip-362-corpus-gold-dataset
```

Repeat for:

- `ngaip-363-rag-evaluation-harness`
- `ngaip-415-metrics-success-criteria`
- `ngaip-365-context-relevancy-metric`
- `ngaip-364-citation-accuracy-metric`
- `ngaip-366-response-accuracy-metric`

Recommended implementation order:

1. `NGAIP-362`
2. `NGAIP-363`
3. `NGAIP-415`
4. `NGAIP-365`
5. `NGAIP-364`
6. `NGAIP-366`

The order matters because 362 provides the gold data contract, 363 provides the harness, 415 defines the metric/report contract, and the metric tickets plug into that foundation.

## Dependency Setup

The backend uses `uv sync`, so dependencies should be declared in `pyproject.toml` and locked through `uv`, not installed only into the current environment.

From the backend project directory:

```cmd
cd path\to\Pratt-Backend\backend
uv add ragas datasets
uv add langchain langchain-core langchain-openai langchain-community
uv add --dev pytest pytest-django pytest-asyncio
uv sync --group dev
```

If the runtime machine needs pinned versions, start with:

```cmd
uv add ragas>=0.2.0 datasets>=2.14.0
uv add langchain==0.3.10 langchain-community==0.3.4 langchain-core==0.3.21 langchain-openai==0.2.11
uv add --dev pytest==8.3.3 pytest-django==4.9.0 pytest-asyncio==0.23.8
uv sync --group dev
```

The reconstructed backend already lists LangChain packages in `requirements.txt`, but add them to `pyproject.toml` through `uv` if the runtime branch is missing them.

Validate that Django pytest setup works:

```cmd
uv run pytest --version
uv run python -c "from langchain_core.documents import Document; import ragas; print('ragas/langchain OK')"
uv run pytest tests/app_retrieval -v
```

Settings import convention for generated backend code:

- Use `from app.settings_intellisense import settings` when code needs Django settings and should match the existing PrattWise backend pattern.
- The module name is `settings_intellisense` with double `ll`.
- Avoid introducing new `from django.conf import settings` imports in the generated evaluation package unless the surrounding file already uses that style.

The backend already has `pytest.ini` with:

```ini
[pytest]
DJANGO_SETTINGS_MODULE = app.settings
```

Normal Django tests do not require `python manage.py runserver`. Start the server only for true HTTP end-to-end tests that call `localhost`.

## RAGAS Testset Generator

Use the RAGAS testset generator to create candidate evaluation examples from approved PrattWise/Samba source documents.

Ticket ownership:

- `NGAIP-362` owns loading approved source documents into LangChain `Document` objects, generating candidate testsets, preserving provenance, and promoting reviewed rows into the gold dataset.
- `NGAIP-363` owns the reusable harness pieces that later consume the approved gold rows.
- `NGAIP-415` owns the report/schema fields that describe generated, reviewed, and approved testset provenance.

Important rule:

- RAGAS-generated examples are not automatically gold data.
- They are candidate QA/reference rows.
- A human reviewer should approve, edit, or reject them before they become part of the `NGAIP-362` gold dataset.

Recommended flow:

1. Select a small approved document corpus.
2. Convert each source document into the document format required by the installed RAGAS version.
3. Run the RAGAS testset generator to create candidate questions, reference answers, and supporting contexts.
4. Export generated examples to an intermediate file such as `candidate_testset.jsonl`.
5. Review candidates manually for correctness, controlled-data suitability, source traceability, and answerability.
6. Promote approved rows into the `NGAIP-362` gold schema.
7. Keep generated-but-unapproved rows out of the official gold set.

Suggested files:

```text
app_retrieval/evaluation/langchain_document_loader.py
app_retrieval/evaluation/testset_generator.py
app_retrieval/evaluation/config/candidate_testset.schema.md
tests/app_retrieval/test_langchain_document_loader.py
tests/app_retrieval/test_testset_generator.py
```

### LangChain Document Loader Code

`NGAIP-362` should add a loader that turns approved document exports into LangChain `Document` objects. The backend already has LangChain packages in `requirements.txt`, so use `langchain_core.documents.Document` as the stable object shape that RAGAS testset generation can consume.

Recommended file: `app_retrieval/evaluation/langchain_document_loader.py`

```python
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from langchain_core.documents import Document


REQUIRED_SOURCE_FIELDS = {"asset_id", "text"}


def load_langchain_documents(path: Path) -> list[Document]:
    """Load approved source-document JSONL into LangChain Documents.

    Expected JSONL fields:
      - asset_id: PrattWise stable source id
      - text: source text used for testset generation
      - title/page/section/chunk_id: optional provenance fields
    """
    docs: list[Document] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid source document JSON at line {line_number}: {exc}") from exc

        missing = REQUIRED_SOURCE_FIELDS - row.keys()
        if missing:
            raise ValueError(f"Missing source document fields at line {line_number}: {sorted(missing)}")

        metadata = {k: v for k, v in row.items() if k != "text"}
        metadata["source_line"] = line_number
        docs.append(Document(page_content=row["text"], metadata=metadata))

    return docs


def dump_candidate_rows(path: Path, rows: Iterable[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
```

Use JSONL rather than raw filesystem crawling for the first implementation because it is easier to control approved documents, redact content, preserve `asset_id`, and screenshot/review the exact source list. If later needed, add optional `DirectoryLoader`/`TextLoader` support behind the same `load_langchain_documents()` output shape.

Example approved source JSONL:

```json
{"asset_id":"asset-001","title":"Approved Maintenance Extract","page":12,"section":"Inspection","chunk_id":"chunk-001","text":"Approved source text goes here."}
```

Loader tests should verify:

- Valid JSONL returns LangChain `Document` objects.
- `asset_id` and provenance fields are preserved in `metadata`.
- Missing `asset_id` or `text` raises `ValueError`.
- Invalid JSON raises `ValueError` with a line number.

### RAGAS Testset Generator Code

The generator wrapper should isolate RAGAS API details because RAGAS testset APIs can change between versions. Keep the rest of the harness dependent on a stable PrattWise function, for example:

```python
def generate_candidate_testset(source_docs: list[dict], *, size: int) -> list[dict]:
    ...
```

Recommended file: `app_retrieval/evaluation/testset_generator.py`

```python
from __future__ import annotations

from collections.abc import Sequence
from importlib.metadata import version

from langchain_core.documents import Document


def _ragas_version() -> str:
    try:
        return version("ragas")
    except Exception:
        return "unknown"


def generate_candidate_testset(
    documents: Sequence[Document],
    *,
    size: int,
    generator_llm,
    critic_llm,
    embeddings,
) -> list[dict]:
    """Generate candidate QA/reference rows with RAGAS.

    Keep this wrapper small and version-isolated. If the installed RAGAS API
    changes, update this file without changing the Django command or gold schema.
    """
    try:
        from ragas.testset import TestsetGenerator
    except ImportError:
        from ragas.testset.generator import TestsetGenerator

    generator = TestsetGenerator.from_langchain(
        generator_llm=generator_llm,
        critic_llm=critic_llm,
        embeddings=embeddings,
    )
    testset = generator.generate_with_langchain_docs(
        list(documents),
        test_size=size,
    )
    return normalize_ragas_testset(testset, documents)


def normalize_ragas_testset(testset, documents: Sequence[Document]) -> list[dict]:
    """Convert RAGAS output into PrattWise candidate rows.

    The exact RAGAS object shape can vary by version, so keep normalization here.
    """
    if hasattr(testset, "to_pandas"):
        records = testset.to_pandas().to_dict(orient="records")
    elif hasattr(testset, "to_list"):
        records = testset.to_list()
    else:
        records = list(testset)

    source_metadata = [doc.metadata for doc in documents]
    rows: list[dict] = []
    for index, record in enumerate(records, start=1):
        rows.append(
            {
                "candidate_id": f"candidate-{index:04d}",
                "question": record.get("question") or record.get("user_input"),
                "reference_answer": record.get("ground_truth") or record.get("reference"),
                "supporting_context": record.get("contexts") or record.get("reference_contexts"),
                "source_metadata": source_metadata,
                "review_status": "candidate",
                "generator": {
                    "framework": "ragas",
                    "ragas_version": _ragas_version(),
                },
            }
        )
    return rows
```

The actual `generator_llm`, `critic_llm`, and `embeddings` should come from the same evaluator config used by the harness. For Azure OpenAI, build those objects in one shared RAGAS/LangChain factory owned by `NGAIP-363`.

### Golden Test Generator Orchestration

`NGAIP-362` should include one command/module that wires the document loader, Azure OpenAI factory, and RAGAS testset generator together. This is the path that produces the candidate golden set.

Recommended file: `app_retrieval/evaluation/golden_test_generator.py`

```python
from __future__ import annotations

from pathlib import Path

from app_retrieval.evaluation.config.eval_config import load_eval_config
from app_retrieval.evaluation.langchain_document_loader import (
    dump_candidate_rows,
    load_langchain_documents,
)
from app_retrieval.evaluation.ragas_factory import (
    build_ragas_azure_completion_llm,
    build_ragas_langchain_models,
)
from app_retrieval.evaluation.testset_generator import generate_candidate_testset


def generate_golden_candidates(
    *,
    source_docs_path: Path,
    eval_config_path: Path,
    output_path: Path,
    size: int,
) -> list[dict]:
    """Generate candidate golden-set rows from approved source documents."""
    config = load_eval_config(eval_config_path)
    if not config.evaluator.enabled:
        raise ValueError("RAGAS evaluator must be enabled to generate golden candidates")

    documents = load_langchain_documents(source_docs_path)

    # Use AzureChatOpenAI by default for RAGAS generation/judging and Azure
    # embeddings for document/testset embedding. Keep AzureOpenAI completion
    # available for RAGAS paths that specifically need completion-style LLMs.
    chat_llm, embeddings = build_ragas_langchain_models(config.evaluator)
    completion_llm = build_ragas_azure_completion_llm(config.evaluator)

    candidates = generate_candidate_testset(
        documents,
        size=size,
        generator_llm=chat_llm,
        critic_llm=completion_llm,
        embeddings=embeddings,
    )
    dump_candidate_rows(output_path, candidates)
    return candidates
```

If the installed RAGAS version expects both `generator_llm` and `critic_llm` to be chat-compatible, pass `chat_llm` for both values. Keep that decision inside this orchestration/factory layer so the rest of the harness does not care which exact RAGAS API version is installed.

Recommended command shape:

```cmd
uv run python -m app_retrieval.evaluation.golden_test_generator --source-docs approved_docs.jsonl --config app_retrieval/evaluation/config/rag_eval.yaml --output candidate_testset.jsonl --size 50
```

Tests for this orchestration should mock:

- `load_langchain_documents`
- `build_ragas_langchain_models`
- `build_ragas_azure_completion_llm`
- `generate_candidate_testset`
- `dump_candidate_rows`

That gives Django/pytest coverage for the golden generator wiring without making live Azure OpenAI or RAGAS calls.

### Using RAGAS Testset Generator for the Golden Set

Use the RAGAS testset generator as the first draft of the golden set, not as an automatic replacement for human-approved gold data.

The intended `NGAIP-362` workflow is:

1. Load approved source documents into LangChain `Document` objects.
2. Run the RAGAS testset generator.
3. Save the output to `candidate_testset.jsonl`.
4. Human-review each candidate row.
5. Promote only `approved` or `edited` rows into `gold.jsonl`.
6. Validate `gold.jsonl` with the Pydantic `GoldRow` schema.
7. Use the validated `gold.jsonl` as the official golden set for `NGAIP-363`, `NGAIP-365`, `NGAIP-364`, and `NGAIP-366`.

Recommended file owned by `NGAIP-362`: `app_retrieval/evaluation/gold_promoter.py`

```python
from __future__ import annotations

import json
from pathlib import Path

from app_retrieval.evaluation.config.gold_schema import GoldRow


PROMOTABLE_STATUSES = {"approved", "edited"}


def promote_candidates_to_gold(candidate_path: Path, gold_path: Path) -> list[GoldRow]:
    """Promote reviewed RAGAS-generated candidates into the official gold set."""
    promoted: list[GoldRow] = []

    for line in candidate_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("review_status") not in PROMOTABLE_STATUSES:
            continue

        gold_row = GoldRow(
            question_id=row.get("question_id") or row["candidate_id"],
            question=row["question"],
            gold_answer=row["reference_answer"],
            gold_doc_id=row["source_metadata"][0]["asset_id"],
            gold_chunk_ids=[
                item["chunk_id"]
                for item in row.get("source_metadata", [])
                if item.get("chunk_id")
            ]
            or None,
            tags=row.get("tags"),
        )
        promoted.append(gold_row)

    gold_path.parent.mkdir(parents=True, exist_ok=True)
    with gold_path.open("w", encoding="utf-8") as handle:
        for row in promoted:
            handle.write(row.model_dump_json(exclude_none=True) + "\n")

    return promoted
```

Recommended commands:

```cmd
uv run python -m app_retrieval.evaluation.testset_generator --input approved_docs.jsonl --output candidate_testset.jsonl --size 50
uv run python -m app_retrieval.evaluation.gold_promoter --input candidate_testset.reviewed.jsonl --output gold.jsonl
uv run pytest tests/app_retrieval/test_gold_loader.py tests/app_retrieval/test_gold_promoter.py -v
```

Golden set acceptance rules:

- Every generated row must retain source provenance.
- Every promoted row must pass `GoldRow` validation.
- Generated answers must be reviewed against the source document before promotion.
- Rejected candidates must remain outside `gold.jsonl`.
- Edited candidates should preserve both the original generated value and final reviewed value when possible.

Each candidate row should preserve enough provenance to support human review and later citation scoring:

- Source document id or `asset_id`.
- Source title/path if allowed.
- Source span, page, section, or chunk id where possible.
- Generated question.
- Generated reference answer.
- Generated supporting context.
- Generator model/deployment metadata.
- RAGAS version.
- Review status: `candidate`, `approved`, `rejected`, or `edited`.

The approved output should still pass through the Pydantic `GoldRow` validation from `NGAIP-362`. That keeps the final gold file stable even if RAGAS changes its generated-object format.

Recommended commands:

```cmd
uv run python -m app_retrieval.evaluation.testset_generator --input approved_docs.jsonl --output candidate_testset.jsonl --size 25
uv run pytest tests/app_retrieval/test_testset_generator.py -v
```

Use live evaluator/generator credentials only for manual or gated smoke runs. Structural tests should mock the RAGAS generator and validate conversion/export behavior without calling a model.

## RAGAS Configuration

Ticket ownership:

- `NGAIP-363` must add the evaluator section to the RAG evaluation config and implement the config loader/factory code.
- `NGAIP-415` must define the required evaluator metadata fields in `metrics_spec.yaml` and `eval_report.schema.json`.
- `NGAIP-365`, `NGAIP-364`, and `NGAIP-366` consume this config when they call RAGAS metrics.

Add an evaluator section to the RAG evaluation config in `NGAIP-363` so live model calls are explicit and reproducible:

```yaml
evaluator:
  framework: ragas
  enabled: false
  provider: azure_openai
  model: ${AZURE_OPENAI_EVAL_DEPLOYMENT}
  embeddings: ${AZURE_OPENAI_EMBEDDING_DEPLOYMENT}
  temperature: 0
  timeout_seconds: 120
  max_retries: 2
```

Recommended behavior:

- `enabled: false` for default CI and local structural tests.
- `enabled: true` only when credentials and evaluator deployment are available.
- Record evaluator metadata in every `report.json`.

Report metadata should include:

```json
{
  "metrics_spec_version": "ngaip-415-ragas-v1",
  "evaluator": {
    "framework": "ragas",
    "provider": "azure_openai",
    "model": "deployment-name",
    "temperature": 0
  }
}
```

### Evaluator Config Code

Recommended file owned by `NGAIP-363`: `app_retrieval/evaluation/config/eval_config.py`

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class RagasEvaluatorConfig:
    framework: str = "ragas"
    enabled: bool = False
    provider: str = "azure_openai"
    model: str | None = None
    embeddings: str | None = None
    temperature: float = 0
    timeout_seconds: int = 120
    max_retries: int = 2


@dataclass(frozen=True)
class EvalConfig:
    metrics_spec_version: str
    evaluator: RagasEvaluatorConfig
    raw: dict[str, Any]


def load_eval_config(path: Path) -> EvalConfig:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    evaluator_data = data.get("evaluator", {})
    evaluator = RagasEvaluatorConfig(**evaluator_data)
    if evaluator.framework != "ragas":
        raise ValueError(f"Unsupported evaluator framework: {evaluator.framework}")
    return EvalConfig(
        metrics_spec_version=str(data.get("metrics_spec_version", "unknown")),
        evaluator=evaluator,
        raw=data,
    )
```

Recommended file owned by `NGAIP-363`: `app_retrieval/evaluation/ragas_factory.py`

```python
from __future__ import annotations

import os

from app.settings_intellisense import settings
from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings
from langchain_openai.llms import AzureOpenAI

from app_retrieval.evaluation.config.eval_config import RagasEvaluatorConfig


def build_ragas_langchain_models(config: RagasEvaluatorConfig):
    """Build LangChain models for RAGAS metrics and testset generation."""
    if config.provider != "azure_openai":
        raise ValueError(f"Unsupported RAGAS provider: {config.provider}")
    if not config.model:
        raise ValueError("RAGAS evaluator model deployment is required")
    if not config.embeddings:
        raise ValueError("RAGAS embedding deployment is required")

    llm = AzureChatOpenAI(
        azure_deployment=config.model,
        api_key=getattr(settings, "AZURE_OPENAI_API_KEY", os.environ.get("AZURE_OPENAI_API_KEY")),
        azure_endpoint=getattr(settings, "AZURE_OPENAI_ENDPOINT", os.environ.get("AZURE_OPENAI_ENDPOINT")),
        api_version=getattr(settings, "AZURE_OPENAI_API_VERSION", os.environ.get("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")),
        temperature=config.temperature,
        timeout=config.timeout_seconds,
        max_retries=config.max_retries,
    )
    embeddings = AzureOpenAIEmbeddings(
        azure_deployment=config.embeddings,
        api_key=getattr(settings, "AZURE_OPENAI_API_KEY", os.environ.get("AZURE_OPENAI_API_KEY")),
        azure_endpoint=getattr(settings, "AZURE_OPENAI_ENDPOINT", os.environ.get("AZURE_OPENAI_ENDPOINT")),
        api_version=getattr(settings, "AZURE_OPENAI_API_VERSION", os.environ.get("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")),
    )
    return llm, embeddings


def build_ragas_azure_completion_llm(config: RagasEvaluatorConfig) -> AzureOpenAI:
    """Optional completion-style Azure OpenAI LLM for RAGAS paths that require it."""
    if not config.model:
        raise ValueError("RAGAS evaluator model deployment is required")
    return AzureOpenAI(
        azure_deployment=config.model,
        api_key=getattr(settings, "AZURE_OPENAI_API_KEY", os.environ.get("AZURE_OPENAI_API_KEY")),
        azure_endpoint=getattr(settings, "AZURE_OPENAI_ENDPOINT", os.environ.get("AZURE_OPENAI_ENDPOINT")),
        api_version=getattr(settings, "AZURE_OPENAI_API_VERSION", os.environ.get("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")),
        temperature=config.temperature,
        timeout=config.timeout_seconds,
        max_retries=config.max_retries,
    )
```

The same factory can be used by:

- `NGAIP-362` testset generation.
- `NGAIP-365` context metrics.
- `NGAIP-364` faithfulness/grounding.
- `NGAIP-366` answer metrics.

Import note:

- Use `from langchain_openai.llms import AzureOpenAI` when a RAGAS path needs the completion-style Azure OpenAI LLM.
- The class name is `AzureOpenAI`, with capital `A`, `O`, `AI`.
- Use `AzureChatOpenAI` when the RAGAS metric or judge path expects a chat model.
- Keep both options centralized in `app_retrieval/evaluation/ragas_factory.py`.

### Direct RAGAS OpenAI Embeddings Option

If the runtime configuration uses a direct OpenAI client instead of Azure OpenAI through LangChain, document and isolate the RAGAS-native embeddings import in the same `NGAIP-363` factory layer:

```python
from openai import OpenAI
from ragas.embeddings import OpenAIEmbeddings


def build_ragas_openai_embeddings(api_key: str | None = None) -> OpenAIEmbeddings:
    client = OpenAI(api_key=api_key)
    return OpenAIEmbeddings(client=client)
```

Use this only when the evaluator provider is configured as direct OpenAI. For PrattWise/Azure OpenAI, prefer the `AzureOpenAIEmbeddings` plus LangChain path above, because it matches the existing backend dependencies and Azure deployment model.

Do not scatter `from ragas.embeddings import OpenAIEmbeddings` through metric files. Keep it in `app_retrieval/evaluation/ragas_factory.py` so `NGAIP-365`, `NGAIP-364`, and `NGAIP-366` consume one shared embeddings object.

## Teammate Practical RAGAS Guide, Adapted for PrattWise

This section incorporates the practical RAGAS implementation guide being used by the teammate. Treat it as the developer-facing mental model for the work, while the ticket sections below remain the implementation contract.

Ticket mapping:

- Dependency install: parent `ragas-rag-evaluation` branch and `NGAIP-363`.
- Minimal testable RAG pipeline: `NGAIP-363`.
- Existing LanceDB retrieval integration: `NGAIP-363`.
- Evaluation dataset shape: `NGAIP-362` plus `NGAIP-363` adapter.
- RAGAS evaluation call: `NGAIP-365`, `NGAIP-364`, and `NGAIP-366`.
- Score interpretation and thresholds: `NGAIP-415`.

### Core Metrics to Implement

RAGAS evaluates the RAG pipeline across the same dimensions called out in the teammate guide:

| Metric | What it measures | Required fields |
|---|---|---|
| `faithfulness` / `ragas_faithfulness` | Whether the answer is grounded in retrieved context | question, answer, contexts |
| `answer_relevancy` / `ragas_answer_relevancy` | Whether the answer addresses the question | question, answer |
| `context_precision` / `ragas_context_precision` | Whether retrieved chunks are actually relevant | question, contexts, reference/gold answer |
| `context_recall` / `ragas_context_recall` | Whether retrieval captured all needed information | question, contexts, reference/gold answer |

The exact RAGAS field names vary by version. Older examples often use:

```python
{
    "question": "...",
    "answer": "...",
    "contexts": ["chunk 1", "chunk 2"],
    "ground_truth": "...",
}
```

Newer RAGAS versions may use names like:

```python
{
    "user_input": "...",
    "response": "...",
    "retrieved_contexts": ["chunk 1", "chunk 2"],
    "reference": "...",
}
```

Do not spread this version-specific mapping through the codebase. `NGAIP-363` should centralize it in the RAGAS adapter so the ticket metric modules can pass normalized PrattWise objects.

### Minimal Testable RAG Pipeline

The teammate guide starts with a minimal local RAG pipeline. That is useful for proving RAGAS wiring before connecting to PrattWise retrieval.

Reference-only example:

```python
from langchain.chains import RetrievalQA
from langchain.schema import Document
from langchain.vectorstores import FAISS
from langchain_openai import ChatOpenAI, OpenAIEmbeddings


def build_minimal_rag_pipeline(docs: list[str]):
    documents = [Document(page_content=doc) for doc in docs]
    embeddings = OpenAIEmbeddings()
    vectorstore = FAISS.from_documents(documents, embeddings)
    retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    return RetrievalQA.from_chain_type(
        llm=llm,
        retriever=retriever,
        return_source_documents=True,
    )
```

For this program, keep this as a local smoke-test pattern only. The real implementation should use PrattWise retriever adapters from `NGAIP-363`, not a new FAISS store.

### Existing LanceDB Retriever Pattern

The teammate guide correctly notes that RAGAS does not care which vector store produced the contexts. It only needs the final RAG outputs:

- question
- answer
- retrieved contexts
- reference/gold answer

If testing directly against an existing LanceDB table, the generic retriever shape is:

```python
import lancedb
from langchain.schema import Document
from langchain.retrievers import BaseRetriever
from langchain_openai import OpenAIEmbeddings
from pydantic import Field


class LanceDBRetriever(BaseRetriever):
    table_name: str
    k: int = 3
    embeddings: OpenAIEmbeddings = Field(default_factory=OpenAIEmbeddings)
    db_path: str = "./lancedb"

    def _get_relevant_documents(self, query: str) -> list[Document]:
        db = lancedb.connect(self.db_path)
        table = db.open_table(self.table_name)

        query_embedding = self.embeddings.embed_query(query)
        results = table.search(query_embedding).limit(self.k).to_list()

        return [
            Document(
                page_content=row["text"],
                metadata={"source": row.get("source", "")},
            )
            for row in results
        ]

    async def _aget_relevant_documents(self, query: str) -> list[Document]:
        return self._get_relevant_documents(query)
```

PrattWise adaptation:

- Do not assume the LanceDB text field is named `text`; inspect the table schema and map the correct field, such as `content`, `chunk`, or `body`.
- Use the same embedding model/deployment that populated the LanceDB table. Mismatched embeddings will make retrieval quality and RAGAS scores misleading.
- Prefer the existing PrattWise retrieval helpers and adapters in `NGAIP-363` over raw LanceDB access unless the ticket explicitly needs a low-level LanceDB smoke test.
- Preserve source metadata such as `asset_id`, page, section, and chunk id for `NGAIP-364` citation checks.

Schema inspection command:

```python
import lancedb

db = lancedb.connect("./your_lancedb_path")
table = db.open_table("your_table_name")
print(table.schema)
```

### Evaluation Dataset Construction

RAGAS expects the evaluation rows to combine the gold input with the pipeline output.

Gold rows from `NGAIP-362` provide:

```python
eval_samples = [
    {
        "question": "What is the return policy?",
        "ground_truth": "Items can be returned within 30 days with a receipt.",
    },
    {
        "question": "How do I reset my password?",
        "ground_truth": "Go to the login page and click Forgot Password.",
    },
]
```

After the RAG pipeline runs, `NGAIP-363` should collect:

```python
def collect_rag_outputs(qa_chain, eval_samples: list[dict]) -> list[dict]:
    rows: list[dict] = []
    for sample in eval_samples:
        response = qa_chain(sample["question"])
        rows.append(
            {
                "question": sample["question"],
                "answer": response["result"],
                "contexts": [
                    doc.page_content
                    for doc in response["source_documents"]
                ],
                "ground_truth": sample["ground_truth"],
            }
        )
    return rows
```

PrattWise adaptation:

- The actual collector should work with PrattWise retriever and answer outputs, not necessarily LangChain `RetrievalQA`.
- If the backend returns source dictionaries instead of `Document` objects, normalize them into strings for RAGAS contexts and preserve metadata for deterministic citation metrics.
- The collector belongs in `NGAIP-363`.
- The final metric field names belong to `NGAIP-415`.

### Running RAGAS Evaluation

The teammate guide uses the standard RAGAS evaluation shape:

```python
from datasets import Dataset
from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_precision,
    context_recall,
)


def run_evaluation(rag_outputs: list[dict]):
    dataset = Dataset.from_list(rag_outputs)
    results = evaluate(
        dataset=dataset,
        metrics=[
            faithfulness,
            answer_relevancy,
            context_precision,
            context_recall,
        ],
    )
    df = results.to_pandas()
    df.to_csv("ragas_results.csv", index=False)
    return results
```

PrattWise adaptation:

- `NGAIP-365` should own context precision/recall output.
- `NGAIP-364` should own faithfulness/grounding plus deterministic citation metadata.
- `NGAIP-366` should own answer correctness/relevancy.
- Do not write only `ragas_results.csv`; the harness should emit `report.json` and `report.csv`.
- Include RAGAS result columns inside the `scores` dict for each question.

### Non-OpenAI Judge Option

The teammate guide shows that RAGAS can use a non-OpenAI judge through wrappers:

```python
from langchain_anthropic import ChatAnthropic
from ragas.llms import LangchainLLMWrapper


judge_llm = LangchainLLMWrapper(ChatAnthropic(model="claude-opus-4-5"))

results = evaluate(
    dataset=dataset,
    metrics=[faithfulness, answer_relevancy],
    llm=judge_llm,
)
```

For PrattWise, this should be a config-driven option in `NGAIP-363`, not hardcoded in metric files. Azure OpenAI remains the default unless the runtime environment is explicitly configured for another provider.

### Score Interpretation

Use these bands as initial review guidance, not final acceptance thresholds:

| Score range | Interpretation |
|---|---|
| `0.9 - 1.0` | Excellent, likely production-ready |
| `0.7 - 0.9` | Good, may need minor tuning |
| `0.5 - 0.7` | Fair, revisit chunking, retrieval, prompts, or references |
| `< 0.5` | Poor, likely fundamental retrieval or grounding issue |

Where to look when scores are low:

- Low faithfulness: answer may be hallucinated or unsupported; tighten system prompt and grounding.
- Low answer relevancy: prompt may be vague, retrieval may be noisy, or answer formatting may be off.
- Low context precision: reduce `k`, improve reranking, filter noisy chunks, or improve source selection.
- Low context recall: improve chunking strategy, embedding model alignment, or query expansion.

`NGAIP-415` must calibrate real pass/fail thresholds on the `NGAIP-362` gold set before these become official criteria.

### Key Tips From the Teammate Guide

- Start small: 20-50 hand-curated QA pairs are enough to get meaningful signal.
- Automate growth carefully: use the RAGAS testset generator to draft candidate questions, then review before promoting to gold.
- Track over time: store `report.json`, `report.csv`, evaluator metadata, and git commit ids so improvements can be compared.
- Do not rely on a single metric: optimizing one RAGAS metric in isolation can hurt the others.
- Always preserve provenance: source ids and chunk metadata are required for PrattWise citation checks.

## Can RAGAS Evaluations Run as Django Tests?

Yes, but split them into two categories.

### Structural Django Tests

These should always run in CI:

- Gold schema validation.
- Config parsing.
- RAGAS adapter input shaping.
- Report JSON/CSV field output.
- Token-overlap diagnostic behavior.
- Citation metadata calculations.

These tests should not call a live LLM.

Example:

```cmd
uv run pytest tests/app_retrieval -v
```

### Live RAGAS Smoke Tests

These can run as Django tests, but should be gated by config or environment variables:

```cmd
set RUN_RAGAS_LIVE=1
set AZURE_OPENAI_EVAL_DEPLOYMENT=...
set AZURE_OPENAI_API_KEY=...
uv run pytest tests/app_retrieval/test_ragas_live.py -v
```

Use `pytest.mark.skipif` so these tests skip when credentials are missing.

Recommended rule:

- CI should prove the harness and adapters are correct without secrets.
- A manual or scheduled smoke run should prove live RAGAS scoring works against a small approved gold dataset.

## Script Generation Requirements

Each transfer script should:

- Check the current branch with `git branch --show-current`.
- Continue if already on the expected ticket branch.
- Switch to the expected ticket branch if it already exists locally.
- Create the expected branch from the configured base branch if it does not exist.
- Write or update only files owned by that ticket.
- Stage only files written or touched by that script.
- Create a local commit with a ticket-specific message.
- Never run `git push`, `git fetch`, or `git pull`.

Commit messages should be explicit:

- `NGAIP-362: Add gold dataset schema and fixtures`
- `NGAIP-363: Add RAG evaluation harness`
- `NGAIP-415: Add RAGAS metrics contract`
- `NGAIP-365: Add RAGAS context relevancy metrics`
- `NGAIP-364: Add citation and grounding metrics`
- `NGAIP-366: Add RAGAS response accuracy metrics`

If generating scripts from the `rag_eval` repository, copy the relevant `evals/ngaip-*-transfer.py` script to the runtime backend root, run it from that root, inspect the diff, then keep or amend the generated local commit.

## Ticket Checklist

### NGAIP-362: Gold Corpus and Dataset

Goal: define the reference data that RAGAS and deterministic metrics will consume.

Implementation checklist:

- Add `app_retrieval/evaluation/config/gold_schema.py`.
- Add `app_retrieval/evaluation/config/gold_schema.md`.
- Add redacted CI fixture such as `ci_gold.jsonl`.
- Add `app_retrieval/evaluation/gold_loader.py`.
- Add `app_retrieval/evaluation/langchain_document_loader.py`.
- Add a RAGAS testset-generator wrapper for producing candidate rows from approved source documents.
- Add `app_retrieval/evaluation/golden_test_generator.py` to orchestrate document loading, Azure OpenAI model creation, RAGAS testset generation, and candidate export.
- Add `app_retrieval/evaluation/gold_promoter.py` to convert reviewed RAGAS candidates into official gold rows.
- Add an intermediate candidate schema/document explaining review status and provenance fields.
- Add tests for valid rows, missing fields, invalid JSON, extra fields, and optional spans/chunk ids.
- Add tests for LangChain `Document` loading and provenance preservation.
- Add tests for converting mocked RAGAS-generated examples into candidate rows.
- Add tests for golden test generator orchestration with all live model/RAGAS calls mocked.
- Add tests for promoting only approved/edited candidates into the official golden set.

Use Pydantic here.

Justification:

- `NGAIP-362` is not an evaluator metric ticket; it is a data-contract ticket.
- Pydantic is appropriate for validating gold rows before they are passed into RAGAS.
- The backend already includes `pydantic==2.9.2` in `requirements.txt` and uses Pydantic in existing backend code.
- RAGAS still needs clean structured input, and Pydantic helps guarantee that input.
- The RAGAS testset generator helps draft candidate examples, but human review and Pydantic validation decide what becomes official gold data.

RAGAS relationship:

- Do not replace the 362 schema with RAGAS.
- Use RAGAS testset generation to produce candidate rows from approved source documents.
- Preserve provenance so generated candidates can be traced back to source docs/chunks.
- Convert validated `GoldRow` objects into RAGAS dataset rows later in the harness.
- Required RAGAS fields usually include question/user input, retrieved contexts, generated answer, and reference/ground-truth answer.

Done when:

- Gold fixture loads successfully.
- Invalid rows fail with useful errors.
- RAGAS-generated candidates can be reviewed and promoted into validated `gold.jsonl`.
- Golden test generator wiring is covered by mocked Django/pytest tests.
- Tests run under Django/pytest without live RAGAS credentials.

### NGAIP-363: RAG Evaluation Harness

Goal: create the reusable Django-native harness that loads gold data, runs retrievers, invokes metrics, and writes reports.

Implementation checklist:

- Add `app_retrieval/evaluation/` package.
- Add config loader.
- Add Django management command, for example `python manage.py rag_eval run --config ...`.
- Add the `evaluator` config section and parser.
- Add the RAGAS/LangChain model factory.
- Add retriever adapters for semantic, keyword, and hybrid modes.
- Add metric registry.
- Add JSON and CSV reporters.
- Add RAGAS adapter helpers that map PrattWise data into RAGAS inputs.
- Add tests for config loading, command wiring, fake retriever flow, metric registry, and report output.

RAGAS-specific requirements:

- Add `ragas` and `datasets` dependencies.
- Create an adapter layer rather than scattering RAGAS calls through each command.
- Keep live RAGAS calls disabled unless config says they are enabled.

Done when:

- A redacted fixture can run end-to-end through the harness with fake/deterministic metrics.
- Reports include placeholders or real fields compatible with 415.
- RAGAS dependencies are installed and importable.

### NGAIP-415: Metrics and Success Criteria

Goal: define the metric contract used by all reports and ticket implementations.

Implementation checklist:

- Add `metrics_spec.yaml`.
- Add `eval_report.schema.json`.
- Add a human-readable metrics document.
- Include RAGAS metric ids and deterministic adapter ids.
- Include `metrics_spec_version`.
- Include evaluator metadata requirements.
- Require report fields for testset generator provenance where candidate or generated gold rows were used.
- Add tests that validate required metric ids and report schema structure.

Recommended metric ids:

- `ragas_context_precision`
- `ragas_context_recall`
- `ragas_faithfulness`
- `ragas_answer_correctness`
- `ragas_answer_relevancy`
- `citation_precision`
- `citation_recall`
- `hallucination_rate`
- `token_overlap_at_k`

Justification:

- RAGAS metrics should be the primary semantic metrics.
- Deterministic metrics should remain for metadata and cheap CI.
- Thresholds should be calibrated on the 362 gold corpus before final sign-off.

Done when:

- Reports can declare the metric spec version.
- Every metric ticket knows which field names to output.
- Schema tests fail if report contracts drift.

### NGAIP-365: Context Relevancy

Goal: measure whether retrieved contexts are useful for answering each gold question.

Implementation checklist:

- Replace the 363 context metric stub.
- Implement RAGAS context precision and context recall through the shared adapter.
- Keep token overlap as a diagnostic metric.
- Record evaluator metadata in `report.json`.
- Add unit tests for adapter input shape and deterministic token overlap.
- Add a gated live RAGAS smoke test if credentials are available.

RAGAS behavior:

- Use retrieved chunks as `contexts`.
- Use gold answer or reference answer as the reference.
- Use generated answer where required by the selected RAGAS metric.

Justification:

- Context relevance is semantic, so token overlap should not be the primary score.
- Token overlap stays useful for CI and for explaining retrieval misses.

Done when:

- Report output includes RAGAS context fields.
- Structural tests pass without credentials.
- Live smoke test can run when enabled.

### NGAIP-364: Citation Accuracy and Grounding

Goal: measure whether citations and grounding are correct.

Implementation checklist:

- Replace the 363 citation metric stub.
- Add deterministic citation precision and recall.
- Add hallucinated citation detection.
- Add RAGAS faithfulness/grounding as the semantic grounding metric.
- Add tests for correct source, wrong source, missing citation, and hallucinated citation.

RAGAS behavior:

- Use RAGAS faithfulness to check whether the answer is supported by retrieved contexts.
- Do not rely on RAGAS for PrattWise source metadata validation.

Justification:

- RAGAS can judge semantic grounding.
- PrattWise code must still validate `asset_id`, source references, and citation metadata.

Done when:

- Reports include both semantic grounding and deterministic citation metadata fields.
- Wrong-source citations fail deterministic tests.

### NGAIP-366: Response Accuracy

Goal: measure answer quality against the gold answer.

Implementation checklist:

- Replace the 363 response metric stub.
- Implement RAGAS answer correctness.
- Implement RAGAS answer relevancy if supported by the installed version.
- Include RAGAS faithfulness where useful for answer grounding.
- Keep human annotation export for calibration.
- Add structural tests for adapter inputs and report outputs.
- Add gated live smoke tests for evaluator scoring.

Justification:

- Response accuracy is semantic and should use RAGAS as the automated evaluator path.
- Human calibration remains necessary for threshold sign-off and stakeholder confidence.

Done when:

- Reports include response quality RAGAS scores.
- Annotation export remains available.
- Live scoring can be run manually with credentials.

## RAGAS Adapter Shape

Keep one adapter layer responsible for converting PrattWise evaluation rows into RAGAS-compatible examples.

The adapter should accept:

- `question`
- `answer`
- `ground_truth` or `reference`
- `contexts`
- optional source metadata for deterministic checks

The adapter should produce the input format required by the installed RAGAS version. RAGAS APIs change between versions, so isolate imports and API calls in one file, for example:

```text
app_retrieval/evaluation/ragas_adapter.py
```

Benefits:

- Easier upgrades when RAGAS changes metric names or signatures.
- Easier unit testing without live model calls.
- Cleaner separation between PrattWise retrieval objects and evaluator library inputs.

## Django Test Plan

Default test command:

```cmd
uv run pytest tests/app_retrieval -v
```

Suggested test groups:

- `test_gold_loader.py`: no RAGAS calls.
- `test_gold_promoter.py`: no RAGAS calls; verifies reviewed candidates become valid `GoldRow` rows.
- `test_golden_test_generator.py`: no live calls; mocks document loading, Azure OpenAI factory, RAGAS generation, and candidate writing.
- `test_eval_config.py`: no RAGAS calls.
- `test_ragas_adapter.py`: no live LLM; verify input mapping.
- `test_metric_context_relevancy.py`: deterministic plus mocked RAGAS.
- `test_metric_citation_accuracy.py`: deterministic plus mocked RAGAS faithfulness.
- `test_metric_response_accuracy.py`: mocked RAGAS scoring.
- `test_ragas_live.py`: skipped unless `RUN_RAGAS_LIVE=1`.

Example skip policy:

```python
import os
import pytest

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_RAGAS_LIVE") != "1",
    reason="Live RAGAS evaluation requires credentials",
)
```

## Report Checklist

Every report should include:

- Run id.
- Timestamp.
- Git branch and commit if available.
- Config path.
- Gold dataset path or dataset id.
- Retriever mode.
- `metrics_spec_version`.
- RAGAS evaluator provider/model/deployment.
- Per-question scores.
- Aggregate scores.
- Any skipped metrics with reason.

Every per-question score should include fields from 415, even if some are `null` or skipped because live evaluation was disabled.

## Final Implementation Checklist

- Create `ragas-rag-evaluation` from `main-backup-for-mac-claude-repo-04-07-2026`.
- Add dependencies through `uv add`, then run `uv sync --group dev`.
- Confirm `uv run pytest --version`.
- Implement 362 data contract with Pydantic validation.
- Implement 362 LangChain `Document` loader for approved source documents.
- Add RAGAS testset generation for candidate QA/reference rows and require human review before promotion to gold.
- Implement 363 harness, evaluator config parser, RAGAS/LangChain factory, and RAGAS adapter layer.
- Implement 415 metric/report contract, including evaluator and testset provenance fields.
- Implement 365 RAGAS context metrics and token-overlap diagnostic.
- Implement 364 RAGAS faithfulness plus deterministic citation metadata checks.
- Implement 366 RAGAS answer metrics plus human annotation export.
- Add Django tests for structural behavior.
- Add gated live RAGAS smoke tests.
- Generate `report.json` and `report.csv`.
- Confirm reports include evaluator metadata.
- Keep ticket commits local unless publishing is explicitly approved.

## Answer to the Pydantic Question for NGAIP-362

Yes, using Pydantic for `NGAIP-362` is reasonable.

`NGAIP-362` defines and validates the gold dataset. That is a schema/data-contract problem, not a metric-evaluation problem. RAGAS should consume the validated dataset later, but RAGAS should not be used as the schema validator.

The backend already has Pydantic in `requirements.txt`, and some backend code already imports Pydantic. The repo is mostly Django models for persisted database objects, but Pydantic is appropriate for non-persisted structured inputs such as JSONL evaluation rows.

Recommended split:

- Pydantic validates `GoldRow`.
- RAGAS testset generator creates candidate examples from approved documents.
- Human review promotes accepted generated examples into the official gold dataset.
- The harness converts `GoldRow` into RAGAS examples.
- RAGAS scores context relevance, faithfulness, answer correctness, and answer relevancy.
- Deterministic PrattWise code scores source metadata and cheap diagnostics.
