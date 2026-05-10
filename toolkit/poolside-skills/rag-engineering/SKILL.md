---
name: rag-engineering
description: Engineering patterns for retrieval-augmented generation—chunking, hybrid retrieval, context budgets, citations, vector stores (e.g. LanceDB), and pairing neural eval (RAGAS) with deterministic checks. Use when designing pipelines, refactoring app_retrieval, or reasoning about PrattWise RAG architecture beyond a single evaluate() call.
---

# RAG engineering patterns

## Retrieval

- **Chunking:** balance **small chunks** (precision, less noise) vs **large chunks** (more context, more irrelevant tokens). Align **chunk boundaries** with structure (headings, tables) when the parser allows.  
- **Hybrid search:** combine **dense** (embedding) + **sparse** (BM25/keyword) when exact tokens (part numbers, codes) matter.  
- **top_k vs budget:** increasing `k` improves recall but hurts latency and may confuse the LLM; enforce a **max token budget** for `context` assembly.  
- **Deduplication:** near-duplicate chunks waste budget; dedupe by chunk id or similarity before prompt assembly.

## Generation

- **Prompt contract:** require the model to **cite chunk ids** or **quote minimally** when citations are required.  
- **No context / low confidence:** prefer explicit **“not found in sources”** behavior over confident hallucination for enterprise RAG.  
- **System prompts:** scope what the assistant may infer beyond retrieved text (see research-assistant style tickets).

## Evaluation layer

- **RAGAS** for semantic quality trends; **deterministic** checks for IDs, spans, regex facts, or schema compliance.  
- Log **retrieved ids** per turn for debugging (“wrong chunk” vs “wrong answer”).

## Storage (PrattWise-shaped)

- Vector tables (e.g. **LanceDB**) should retain **stable `doc_id` / `chunk_id`** metadata for eval hooks and citation UX.  
- **Re-ingestion** changes chunk boundaries → expect **eval drift**; re-baseline gold sets.

## Security and correctness

- Treat retrieved docs as **untrusted input** for XSS/CSRF only in web rendering; for LLM injection, sanitize or separate instructions from user-controlled doc text where feasible.  
- **Access control:** retrieval must respect **folder/asset ACLs** as in production.

## Where this program lives

- Backend: **`app_retrieval`** (ingestion, search, assets).  
- Transfer scripts: **`rag_eval/eval_v2`** (RAGAS harness, gold schema).  
- Use **`ragas-evaluation`** skill when working primarily with **metric definitions and Dataset rows**.
