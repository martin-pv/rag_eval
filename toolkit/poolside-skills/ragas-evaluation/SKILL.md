---
name: ragas-evaluation
description: RAGAS metrics, dataset schema, async evaluation, and common pitfalls for RAG quality scoring. Use when wiring ragas.evaluate, choosing metrics (faithfulness, context_precision, context_recall, answer_relevancy, answer_correctness), building Dataset rows, integrating LangChain LLM/embeddings wrappers, DiscreteMetric, or aligning with Pratt-Backend eval_v2 async_ragas_runner and gold_schema.
---

# RAGAS evaluation (engineering reference)

## Dataset shape (typical RAG row)

RAGAS expects records roughly like:

- **`user_input`** — question / query  
- **`response`** — model answer to score  
- **`retrieved_contexts`** — list of strings (chunks/snippets fed to the generator)  
- **`reference`** — gold answer or ground truth for answer-based metrics  

Missing or empty **`retrieved_contexts`** often collapses **context_precision / context_recall** or makes scores misleading. **Faithfulness** needs contexts that actually correspond to what the model saw.

## Core metrics (what they measure)

| Metric | Use when you care about… |
|--------|---------------------------|
| **context_precision** | Whether retrieved chunks are relevant to the question (precision in the retrieved set). |
| **context_recall** | Whether retrieval covered what the reference answer needed (recall vs reference). |
| **faithfulness** | Answer grounded in retrieved text (not hallucinating beyond context). |
| **answer_relevancy** | Answer addresses the question (semantic relevance). |
| **answer_correctness** | Closeness to reference answer (may need strong LLM judge + embeddings). |

Pick a **small subset** for iteration (e.g. faithfulness + context_precision) before running the full stack on large sets.

## Async / LangChain integration

- `ragas.evaluate` may be **sync** depending on version; calling it from async code often uses **`asyncio.to_thread(evaluate, dataset, metrics=..., llm=..., embeddings=...)`** (see Pratt-Backend **`async_ragas_runner`** pattern in `eval_v2`).  
- Wrap LangChain models with RAGAS **`LangchainLLMWrapper` / `LangchainEmbeddingsWrapper`** or use **`llm_factory`** with an **`AsyncOpenAI`** client when using the v2 factory style.

## Version and API drift

- Import paths differ across RAGAS versions (`ragas.testset` vs `ragas.testset.generator`). Guard with `try/except ImportError` when generating test sets.  
- Pin **`ragas`** in backend **`pyproject.toml`** / lockfile for reproducible eval numbers.

## Common pitfalls

1. **Contexts don’t match production** — scoring against paraphrased chunks while production uses different chunking → metrics don’t predict live quality.  
2. **Reference too short** — **answer_correctness** unstable if references omit nuance.  
3. **Multi-hop** — single-turn RAGAS rows may not capture tool use or multi-step reasoning; document scope.  
4. **Cost** — LLM-based metrics burn tokens; subsample or cache where appropriate.

## Program context

- **`eval_v2/docs/`** — per-ticket transfer docs and merge order.  
- **`rag-eval-v2-transfer`** skill — running `ngaip-*-transfer-v2.py` into the backend.

## Checklist before trusting scores

- [ ] Same **retriever** and **chunk format** as production (or document the gap).  
- [ ] **Non-empty** `retrieved_contexts` for every row.  
- [ ] **Gold/reference** quality reviewed (not placeholder text).  
- [ ] **Evaluator model** and temperature documented alongside scores.
