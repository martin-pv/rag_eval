# NGAIP-366 v2 — response accuracy

**Script:** `eval_v2/ngaip-366-transfer-v2.py`  
**Branch:** `ngaip-366-response-accuracy-metric-v2`  
**Commit message:** `NGAIP-366: Apply v2 RAGAS response accuracy changes`

## What it does

Adds **`app_retrieval/evaluation/metrics/response_accuracy_v2.py`**:

- Constant **`RESPONSE_ACCURACY_METRICS`**: `answer_correctness`, `answer_relevancy`, `faithfulness`.
- **`score_response_accuracy(cases, *, llm=None, embeddings=None)`** — **`aevaluate_cases`** with that bundle.

Tests: **`tests/app_retrieval/test_response_accuracy_v2.py`** asserts the metric list.

## Prerequisites

- **NGAIP-363**.

## How to run

```bash
cd /path/to/Pratt-Backend
uv run python /path/to/rag_eval/eval_v2/ngaip-366-transfer-v2.py
```

## How to test manually

```bash
uv run pytest tests/app_retrieval/test_response_accuracy_v2.py -v
```

## Notes

- Same transfer scaffolding as 364/365 (LF, optional `uv run pytest`).
