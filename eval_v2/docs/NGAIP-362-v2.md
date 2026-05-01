# NGAIP-362 v2 — gold dataset & RAGAS testset plumbing

**Script:** `eval_v2/ngaip-362-transfer-v2.py`  
**Branch:** `ngaip-362-corpus-gold-dataset-v2`  
**Commit message:** `NGAIP-362: Apply v2 RAGAS gold dataset changes`

## What it does

Transfers the **v2 gold corpus contract** and helpers into `app_retrieval/evaluation/`:

| File | Role |
|------|------|
| `app_retrieval/evaluation/config/gold_schema.py` | Pydantic `GoldRow`: question, gold answer, doc/chunk ids, optional `reference_contexts`, RAGAS-oriented `to_ragas_record()`. |
| `app_retrieval/evaluation/gold_dataset.py` | Load JSONL → `GoldRow`, convert to RAGAS records / Hugging Face `Dataset`, append approved candidates to gold file. |
| `app_retrieval/evaluation/golden_test_generator.py` | Async-friendly wrapper around RAGAS `TestsetGenerator` + optional **knowledge-graph context** stitched into `Document` text. |
| `app_retrieval/evaluation/lancedb_loader.py` | `load_lancedb_documents(db_path, table_name, …)` → `list[langchain_core.documents.Document]` for testset generation from PrattWise LanceDB. |
| `app_retrieval/evaluation/config/sample_gold.jsonl` | Copy of bundled **`sample_gold_v2.jsonl`** (50 rows; used by tests). |

It also ensures `__init__.py` files exist under `app_retrieval/`, `app_retrieval/evaluation/`, `app_retrieval/evaluation/config/`, and `tests/app_retrieval/`, then adds **`tests/app_retrieval/test_gold_dataset_v2.py`** (unit tests; LanceDB tested with mocks).

## Prerequisites

- **Pratt-Backend** repo root as cwd.
- **`main`** branch available; script creates/switches to `ngaip-362-corpus-gold-dataset-v2`.
- Python packages: **`pydantic`**, **`datasets`**, **`langchain_core`**, **`ragas`** (for imports in generated code paths), **`pytest`**.

## How to run

```bash
cd /path/to/Pratt-Backend
uv run python /path/to/rag_eval/eval_v2/ngaip-362-transfer-v2.py
# or: python eval_v2/ngaip-362-transfer-v2.py
```

The script writes files, runs pytest on `tests/app_retrieval/test_gold_dataset_v2.py`, then **`git add`** + **`git commit`** (local only). Tests are force-added if gitignored.

## How to test manually

```bash
cd /path/to/Pratt-Backend
uv run pytest tests/app_retrieval/test_gold_dataset_v2.py -v
```

Checks: sample gold row count (≥50), RAGAS record shape, KG text attachment, mocked LanceDB → `Document` shape.

## Notes

- This script’s `write()` helper may use `write_text` in some repo snapshots; **364+** use `write_bytes` for LF on Windows. If you need consistent LF everywhere, align 362 with the same pattern or rely on `.gitattributes` (see main `eval_v2/README.md`).
- **`sample_gold_v2.jsonl`** must sit **next to** the script; the script reads it at runtime.
