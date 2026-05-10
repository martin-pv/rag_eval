---
name: rag-eval-v2-transfer
description: Apply NGAIP RAGAS v2 transfer scripts from rag_eval into Pratt-Backend. Use when working with eval_v2/ngaip-*-transfer-v2.py, gold datasets, RAGAS harness, citation/context/response metrics, POC runner, or report schema v2. Requires running scripts from the backend repo root with sample_gold_v2.jsonl beside the script.
---

# rag_eval v2 transfer (NGAIP)

## When to use

- Porting **v2** evaluation code: `eval_v2/ngaip-362-transfer-v2.py` through `ngaip-415-transfer-v2.py`.
- Reading or updating **`eval_v2/docs/`** per-ticket notes.

## Rules

1. **Current working directory** must be the **Pratt-Backend** root (contains application packages like `app_retrieval`, tests, `manage.py`).

2. Invoke with absolute or relative path to the script inside **rag_eval**:

   ```bash
   uv run python /path/to/rag_eval/eval_v2/ngaip-362-transfer-v2.py
   ```

3. **Do not move `sample_gold_v2.jsonl`** away from `eval_v2/` — scripts read it via `Path(__file__).with_name("sample_gold_v2.jsonl")`.

4. Respect **merge order**: 362 → 363 → metrics (364–366) → 412 → 415. See `eval_v2/docs/README.md`.

5. After a run, review the **local git branch** and commit; scripts do not `git push`.

## Verification

- Rerun the generated test module with `uv run pytest … -v` from the backend root.
- For behavior detail, open the matching `eval_v2/docs/NGAIP-*-v2.md` file.
