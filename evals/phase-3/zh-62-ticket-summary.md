# ZH-62 - Hybrid Keyword / Semantic RAG Routing

## Ticket Purpose

ZH-62 adds a hybrid retrieval path that combines semantic vector search with keyword search, normalizes scores, deduplicates chunks, and returns the best merged contexts.

## Generated Files and Code Changes

`zh-62-transfer.py` creates or updates:

- `app_retrieval/data_assets/search.py`
- `app_retrieval/views_search.py`
- `tests/app_retrieval/test_hybrid_search.py`

## Reasoning, Choices, and Justification

Hybrid search is needed because PrattWise users ask both conceptual questions and exact-heading questions. Semantic search handles meaning; keyword search handles section labels, part numbers, and exact terms. Merging both improves recall without abandoning the existing retrieval stack.

Rejected alternatives:

- Semantic-only retrieval: misses exact headings and identifiers.
- Keyword-only retrieval: misses paraphrased/conceptual queries.
- Concatenating results without normalization/deduplication: creates unstable ordering and duplicate chunks.

## Code Breakdown

- `_normalize_scores(results)`: maps each result set into a comparable `0.0` to `1.0` score range.
- `hybrid_search_folder(...)`: runs semantic and keyword search concurrently, dedupes by `(asset_id, start_idx)`, keeps the best normalized score, and returns top K.
- `views_search.py` patch: imports the hybrid function for API use.
- Tests: verify normalization, merging, deduplication, ordering, top K, and empty-result behavior.

## Runtime Setup and Test Playbook

Run from the backend repository root on the runtime machine, where `manage.py` lives unless the ticket says otherwise.

```cmd
cd C:\path\to\ENCHS-PW-GenAI-Backend
py -3 C:\path\to\rag_eval\evals\zh-62-transfer.py
```

On macOS/Linux:

```bash
cd /path/to/ENCHS-PW-GenAI-Backend
python3 /path/to/rag_eval/evals/phase-3/zh-62-transfer.py
```


Run tests:

```cmd
uv sync --group dev
uv run pytest tests/app_retrieval/test_hybrid_search.py -v
```

Manual smoke test:

1. Run a query with an exact section/part term.
2. Run a conceptual query.
3. Confirm hybrid results contain sensible contexts from both search styles and no duplicate chunks.

## Git Add and Commit Guidance

This ticket generates a test under `tests/`, so force-add it if needed.

```cmd
git add app_retrieval/data_assets/search.py app_retrieval/views_search.py
git add -f tests/app_retrieval/test_hybrid_search.py
git commit -m "ZH-62: add hybrid keyword semantic retrieval"
```
