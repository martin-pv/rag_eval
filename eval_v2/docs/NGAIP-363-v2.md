# NGAIP-363 v2 — async RAGAS harness & model factory

**Script:** `eval_v2/ngaip-363-transfer-v2.py`  
**Branch:** `ngaip-363-rag-evaluation-harness-v2`  
**Commit message:** `NGAIP-363: Apply v2 async RAGAS harness changes`

## What it does

Installs the **async-first evaluation harness** and **LLM/embeddings factory** used by the other v2 metric modules:

| File | Role |
|------|------|
| `app_retrieval/evaluation/async_ragas_runner.py` | `collect_ragas_cases`: async retrieve + answer per `GoldRow`; `aevaluate_cases`: builds `Dataset` and calls `ragas.evaluate` in a thread; `default_metrics()` maps names to RAGAS metric objects (`faithfulness`, `answer_relevancy`, `answer_correctness`, `context_precision`, `context_recall`). |
| `app_retrieval/evaluation/ragas_factory_v2.py` | `EvaluatorModelConfig`, `build_async_openai_client`, `build_ragas_async_llm`, `DiscreteMetric` helpers, optional **ModelHub** token flow (file cache + `requests` client_credentials) and header shape aligned with APIM. |
| `app_retrieval/evaluation/config/eval_config_v2.py` | YAML-loaded `EvalV2Config` (gold path, output dir, metric list, model, top_k). |
| `app_retrieval/evaluation/config/sample_gold.jsonl` | Refreshed from **`sample_gold_v2.jsonl`** next to the script (same fixture as 362). |

Adds **`tests/app_retrieval/test_async_ragas_runner_v2.py`**: default metrics, discrete metric builder, async case collection, ModelHub headers (mocked token).

## Prerequisites

- Merge **NGAIP-362** first if you need the same `GoldRow` / package layout in one long-lived branch; the 363 script only **touches** overlapping paths (`sample_gold.jsonl`) and expects `app_retrieval.evaluation.config.gold_schema` to exist for imports.
- Dependencies: **`ragas`**, **`openai`**, **`datasets`**, **`pyyaml`**, **`pytest`**, **`unittest.mock`**.

## How to run

```bash
cd /path/to/Pratt-Backend
uv run python /path/to/rag_eval/eval_v2/ngaip-363-transfer-v2.py
```

Then inspect the local commit on `ngaip-363-rag-evaluation-harness-v2`.

## How to test manually

```bash
uv run pytest tests/app_retrieval/test_async_ragas_runner_v2.py -v
```

## Notes

- **ModelHub / cache:** Full token lifecycle is documented in the parent **`eval_v2/README.md`**. Eval runs that need a live token may require **uvicorn** so background mint runs, or use `provider="openai"` / Azure with static keys.
- The script body may duplicate a `SAMPLE_GOLD_JSONL = …` assignment; harmless at runtime but worth cleaning in the script if you edit it.
- Pytest invocation in the embedded helper may be **`python -m pytest`** only; you can still use **`uv run pytest`** manually.
