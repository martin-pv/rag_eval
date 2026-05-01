# NGAIP-364 v2 — citation accuracy

**Script:** `eval_v2/ngaip-364-transfer-v2.py`  
**Branch:** `ngaip-364-citation-accuracy-metric-v2`  
**Commit message:** `NGAIP-364: Apply v2 RAGAS citation accuracy changes`

## What it does

Adds **`app_retrieval/evaluation/metrics/citation_accuracy_v2.py`**:

- **`source_id_recall(expected, actual)`** — deterministic overlap of source IDs (supplemental).
- **`score_citation_accuracy(cases, …)`** — async **`aevaluate_cases`** with **`faithfulness`** + **`context_precision`**.
- **`judge_citation_support(...)`** — async **`DiscreteMetric`** “pass/fail” judgment on whether retrieved context supports the response.

Tests: **`tests/app_retrieval/test_citation_accuracy_v2.py`** (deterministic recall only in the generated stub).

## Prerequisites

- **NGAIP-363** merged (or same tree): imports **`async_ragas_runner`** and **`ragas_factory_v2`**.
- **`app_retrieval/evaluation/metrics/__init__.py`** created/touched by the script.

## How to run

```bash
cd /path/to/Pratt-Backend
uv run python /path/to/rag_eval/eval_v2/ngaip-364-transfer-v2.py
```

## How to test manually

Uses **`uv run pytest`** when `uv` is on `PATH`, else **`python -m pytest`**:

```bash
uv run pytest tests/app_retrieval/test_citation_accuracy_v2.py -v
```

## Notes

- Generated files use **LF** via `write_bytes`.
- Extending tests to cover `score_citation_accuracy` / `judge_citation_support` usually requires mocked LLM/RAGAS calls.
