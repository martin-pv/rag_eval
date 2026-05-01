# NGAIP-365 v2 — context relevancy

**Script:** `eval_v2/ngaip-365-transfer-v2.py`  
**Branch:** `ngaip-365-context-relevancy-metric-v2`  
**Commit message:** `NGAIP-365: Apply v2 RAGAS context relevancy changes`

## What it does

Adds **`app_retrieval/evaluation/metrics/context_relevancy_v2.py`**:

- Constant **`CONTEXT_RELEVANCY_METRICS`**: `context_precision`, `context_recall`, `answer_relevancy`.
- **`score_context_relevancy(cases, *, llm=None, embeddings=None)`** — delegates to **`aevaluate_cases`** with those metrics.

Tests: **`tests/app_retrieval/test_context_relevancy_v2.py`** asserts the metric list.

## Prerequisites

- **NGAIP-363** (async runner + `default_metrics`).

## How to run

```bash
cd /path/to/Pratt-Backend
uv run python /path/to/rag_eval/eval_v2/ngaip-365-transfer-v2.py
```

## How to test manually

```bash
uv run pytest tests/app_retrieval/test_context_relevancy_v2.py -v
```

## Notes

- LF via `write_bytes`; pytest via `uv` when available (same pattern as 364).
