# NGAIP-362 - Assemble Corpus and Gold Dataset

## Ticket Purpose

NGAIP-362 owns the evaluation corpus and gold dataset contract for the RAG evaluation program. It defines how approved PrattWise/Samba source material becomes validated gold rows with questions, reference answers, source identifiers, optional spans, chunk ids, tags, and generation provenance.

This ticket comes first in the implementation order because every downstream metric depends on a stable reference set:

1. `NGAIP-362`
2. `NGAIP-363`
3. `NGAIP-415`
4. `NGAIP-365`
5. `NGAIP-364`
6. `NGAIP-366`

## Runbook Decision

Use RAGAS for generating candidate testset rows from approved documents, but do not treat generated rows as gold automatically. RAGAS candidates must be reviewed by a human before promotion into the official gold JSONL file.

Pydantic is still used here because it validates the gold data schema. RAGAS evaluates RAG quality; Pydantic validates that the evaluation data is well-formed before the harness uses it.

## Generated Files

`ngaip-362-transfer.py` should generate:

- `app_retrieval/evaluation/config/gold_schema.py`
- `app_retrieval/evaluation/config/gold_schema.md`
- `app_retrieval/evaluation/config/ci_gold.jsonl`
- `app_retrieval/evaluation/config/sample_gold.jsonl`
- `app_retrieval/evaluation/gold_dataset.py`
- `app_retrieval/evaluation/golden_test_generator.py`
- `tests/app_retrieval/test_gold_dataset_generation.py`

## Golden Set Flow

1. Export or curate approved source documents from PrattWise/Samba.
2. Load them into LangChain `Document` objects with `asset_id`, `chunk_id`, content type, and source metadata.
3. Load or construct knowledge graph context for the same corpus.
4. Serialize KG nodes and relationships into readable context text.
5. Attach KG context to the LangChain documents before candidate generation.
6. Run the RAGAS `TestsetGenerator` to create candidate questions, reference answers, and supporting context. If the installed RAGAS version supports it, pass both `knowledge_graph` and serialized `llm_context` so graph relationships influence generation.
7. Write candidates to `candidate_testset.jsonl`.
8. Human reviewers mark each candidate `approved`, `edited`, or `rejected`.
9. Promote only approved/edited candidates through `gold_dataset.py`.
10. Validate promoted rows with `GoldRow` before the official gold JSONL is used by the harness.

## RAGAS Role

RAGAS is used for candidate testset generation, not for schema enforcement. The generated candidate rows should preserve:

- `candidate_id`
- question
- reference answer
- supporting context
- source metadata
- knowledge graph context
- generator metadata, including RAGAS version
- review status

## Non-Text Source Handling

For PDFs, tables, OCR, and mixed content, this ticket should preserve the retrieval system's text or markdown representation. RAGAS evaluates the text context that PrattWise provides to the model. It should not be expected to judge raw visuals unless the document pipeline converts those visuals into trustworthy textual/structured context.

Use `content_type` or metadata tags such as `text`, `table`, `ocr`, `graph`, or `mixed` so later reports can separate performance by source modality.

## Dependencies

This ticket depends on the shared RAGAS branch setup:

```cmd
uv add ragas datasets
uv add langchain langchain-core langchain-openai langchain-community
uv add --dev pytest pytest-django pytest-asyncio
uv sync --group dev
```

## Validation

Run structural tests first, without live model calls:

```cmd
uv run pytest tests/app_retrieval/test_gold_dataset_generation.py -v
```

Only run live RAGAS generation after Azure OpenAI settings and approved source documents are available.

If the runtime uses Pratt ModelHub, `NGAIP-362` should obtain its RAGAS LLM and embedding objects from the `NGAIP-363` factory. The teammate `prattwise-scripts` reference used ModelHub as the gateway while still providing an OpenAI-compatible model to RAGAS.

The generated `sample_gold.jsonl` is a sanitized five-row fixture for testing schema validation, RAGAS row conversion, and harness/report plumbing before a real approved corpus is available.

## Branching and Commit Behavior

The runtime implementation should start from the parent `ragas-rag-evaluation` branch when available. The transfer script still bootstraps from local `main-backup-for-mac-claude-repo-04-07-2026` for repeatable transfer use, creates or switches to `ngaip-362-corpus-gold-dataset`, writes generated files, and makes a local commit without pushing.
## RAGAS-Primary Update

`NGAIP-362` now treats RAGAS `TestsetGenerator` as the primary way to bootstrap candidate gold rows. Pydantic remains only for schema validation and promotion safety. Generated rows use RAGAS-native fields (`user_input`, `reference`, `retrieved_contexts`) plus PrattWise source metadata.

## Reasoning, Choices, and Code Breakdown

The main design choice is to separate gold-data validity from RAG quality scoring. `NGAIP-362` uses Pydantic because gold rows are input data that must be deterministic, reviewable, and safe to load. RAGAS is used for candidate generation because it can synthesize realistic question/reference pairs from source documents, but generated rows are still candidates until humans approve them.

Rejected alternatives:

- Fully manual gold-set creation only: too slow to bootstrap enough examples for retrieval and answer metrics.
- Auto-promoting RAGAS output to gold: risky because generated examples can be wrong, ambiguous, or poorly sourced.
- Token-overlap-only data generation: insufficient for semantic RAG evaluation and not aligned with RAGAS-first strategy.

Code/file breakdown:

- `config/gold_schema.py`: defines `GoldRow`, validates required fields, and converts rows to RAGAS-compatible sample dictionaries.
- `config/ci_gold.jsonl`: one tiny fixture for fast CI smoke checks.
- `config/sample_gold.jsonl`: five sanitized rows for local harness testing before approved corpus data exists.
- `gold_dataset.py`: loads JSONL, validates rows, converts rows to RAGAS datasets, and promotes reviewed candidates into the official gold set.
- `golden_test_generator.py`: loads LangChain/LanceDB documents, attaches knowledge graph context, runs RAGAS `TestsetGenerator`, and normalizes version-dependent RAGAS output.
- `test_gold_dataset_generation.py`: verifies schema conversion, fixture validity, KG context attachment, and RAGAS testset normalization without live model calls.

This breakdown keeps `NGAIP-362` focused on corpus and gold-set ownership while letting `NGAIP-363` own the runtime evaluator and model factory.

## Runtime Setup and Test Playbook

Run from the backend repository root on the runtime machine, where `manage.py` lives. The transfer script creates or switches to `ngaip-362-corpus-gold-dataset` from the local-only base branch `main-backup-for-mac-claude-repo-04-07-2026`.

```cmd
cd C:\path\to\ENCHS-PW-GenAI-Backend
py -3 C:\path\to\rag_eval\evals\ngaip-362-transfer.py
```

On macOS/Linux use:

```bash
cd /path/to/ENCHS-PW-GenAI-Backend
python3 /path/to/rag_eval/evals/ngaip-362-transfer.py
```

Set up dependencies with `uv` before running tests:

```cmd
uv add ragas datasets lancedb
uv add langchain==0.3.10 langchain-community==0.3.4 langchain-core==0.3.21 langchain-openai==0.2.11
uv add --dev pytest pytest-django pytest-asyncio
uv sync --group dev
```

The transfer script writes both `ci_gold.jsonl` and `sample_gold.jsonl`. Use `ci_gold.jsonl` for tiny smoke checks and `sample_gold.jsonl` for a fuller local fixture before real approved corpus data exists.

```cmd
uv run pytest tests/app_retrieval/test_gold_dataset_generation.py -v
uv run python -c "from app_retrieval.evaluation.gold_dataset import load_gold_file; print(len(load_gold_file('app_retrieval/evaluation/config/sample_gold.jsonl')))"
```

The generated test file is under `tests/app_retrieval/`, which can be ignored by some repo rules. The transfer script force-adds generated tests automatically. If you edit or stage manually, use:

```cmd
git add app_retrieval/evaluation/config/gold_schema.py app_retrieval/evaluation/gold_dataset.py app_retrieval/evaluation/golden_test_generator.py app_retrieval/evaluation/config/ci_gold.jsonl app_retrieval/evaluation/config/sample_gold.jsonl
git add -f tests/app_retrieval/test_gold_dataset_generation.py
git commit -m "NGAIP-362: Apply transfer script changes"
```
