# NGAIP-412 v2 — async RAGAS POC runner

**Script:** `eval_v2/ngaip-412-transfer-v2.py`  
**Branch:** `ngaip-412-rag-eval-harness-poc-v2`  
**Commit message:** `NGAIP-412: Apply v2 async RAGAS POC changes`

## What it does

Adds **`app_retrieval/evaluation/poc_async_ragas_eval.py`**:

- **`run_poc(gold_file, retrieve, answer, *, llm=None, embeddings=None)`** — async: load gold rows (`load_gold_file`), **`collect_ragas_cases`**, then **`aevaluate_cases`** with **`faithfulness`**, **`context_precision`**, **`answer_relevancy`**.
- **`run_poc_sync(...)`** — `asyncio.run(run_poc(...))` for scripts/notebooks.

Tests: **`tests/app_retrieval/test_poc_async_ragas_eval.py`** — smoke check that `run_poc_sync` is callable.

## Prerequisites

- **NGAIP-362** (`gold_dataset.load_gold_file`).
- **NGAIP-363** (`async_ragas_runner`).

## How to run

```bash
cd /path/to/Pratt-Backend
uv run python /path/to/rag_eval/eval_v2/ngaip-412-transfer-v2.py
```

## How to test manually

```bash
uv run pytest tests/app_retrieval/test_poc_async_ragas_eval.py -v
```

## Notes

- The POC does **not** start the HTTP server; you inject **`retrieve`** and **`answer`** coroutines (e.g. calling your retrieval stack in-process).
- For a real eval, pass non-`None` **`llm`** / **`embeddings`** compatible with RAGAS.
