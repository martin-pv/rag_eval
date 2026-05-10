---
name: rag-debugging-workflow
description: Systematic debugging when RAG answers are wrong or evaluations look off. Use before changing models—check retrieval, context assembly, prompts, and gold data alignment; ties RAGAS metric symptoms to likely root causes.
---

# RAG debugging workflow

Follow **top-down**: confirm what the model **saw**, then whether it **reasoned**, then whether **metrics** are trustworthy.

## 1. Reproduce with frozen inputs

- Capture **query**, **final context strings** (after assembly), **model output**, and **retrieved ids**.  
- Re-run **the same contexts** in a minimal prompt harness to separate retrieval from generation.

## 2. Retrieval checks

| Symptom | Likely causes |
|---------|----------------|
| Answer refers to irrelevant topic | Wrong chunks ranked high; embedding mismatch; query preprocessing bug. |
| “Not found” but doc exists | Chunk too small/large; ACL filtering; wrong collection/table; stale index. |
| Missing obvious keyword hit | No hybrid/BM25; tokenizer/stemming; language mismatch. |

**Actions:** print **top-k scores**, inspect **chunk text**, try **query variants**, verify **filters** (`where` clauses, folder scopes).

## 3. Context assembly

- **Ordering:** putting unrelated chunks first can steal attention.  
- **Truncation:** tail truncation may drop the relevant sentence.  
- **Deduplication / formatting:** bullets vs raw paste changes model behavior.

## 4. Generation

- Compare answers **with** and **without** retrieved context (sanity). If similar, model may be **ignoring** context → tighten instructions or penalize non-grounding.  
- Check **temperature**, **tool use**, and **system prompt** scope.

## 5. RAGAS / eval harness

- If **faithfulness** is low but humans disagree, verify **`retrieved_contexts`** in the eval row **match** production assembly.  
- If **context_recall** only is bad, gold **reference_contexts** or retrieval may be misaligned.  
- Small **N** in the eval set → noisy aggregates; quote confidence qualitatively.

## 6. Gold / labels

- Wrong **gold_doc_id** or **reference_contexts** → metrics punish the pipeline unfairly. Spot-check **10–20** rows manually.

## Escalation

- Persistent retrieval bugs → indexing/pipeline ownership.  
- Persistent judge noise → swap evaluator model or add **deterministic** metrics.  
- See **`rag-engineering`** and **`ragas-evaluation`** for design and metric details.
