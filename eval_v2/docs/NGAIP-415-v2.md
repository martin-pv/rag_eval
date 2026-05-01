# NGAIP-415 v2 — RAGAS-primary report schema

**Script:** `eval_v2/ngaip-415-transfer-v2.py`  
**Branch:** `ngaip-415-metrics-success-criteria-v2`  
**Commit message:** `NGAIP-415: Apply v2 RAGAS report schema changes`

## What it does

Adds **`app_retrieval/evaluation/report_schema_v2.py`**:

- **`RAGAS_PRIMARY_METRICS`** — canonical list: `faithfulness`, `answer_relevancy`, `answer_correctness`, `context_precision`, `context_recall`.
- **`DETERMINISTIC_SUPPLEMENTS`** — names for non-RAGAS checks (e.g. `source_id_recall`, `citation_span_match`, `token_overlap`).
- **`RagasReport`** dataclass: ticket id, `metric_scores`, `case_count`, `evaluator_model`, UTC `created_at`, optional `deterministic_supplements` dict; **`to_dict()`** adds `ragas_primary_metrics` and sorted keys for supplements used.

Tests: **`tests/app_retrieval/test_report_schema_v2.py`** — constructs a report and asserts dict shape / primary metric list.

## Prerequisites

- None from other v2 tickets for **imports**; logically you use this **after** you have metric scores to persist. Can merge independently of 412 if you only need the schema types.

## How to run

```bash
cd /path/to/Pratt-Backend
uv run python /path/to/rag_eval/eval_v2/ngaip-415-transfer-v2.py
```

## How to test manually

```bash
uv run pytest tests/app_retrieval/test_report_schema_v2.py -v
```

## Notes

- Useful for aligning dashboards, JSON exports, or “success criteria” docs with the same metric names as the runner defaults in **363**.
