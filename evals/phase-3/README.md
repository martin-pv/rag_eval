# Phase 3

ZenHub tickets in this phase:

- `zh-62` – hybrid keyword + semantic RAG routing in `app_retrieval/data_assets/search.py` and `views_search.py`

| Transfer script | Ticket summary |
| --- | --- |
| `zh-62-transfer.py` | `zh-62-ticket-summary.md` |

## Running

Run from the Pratt-Backend repo root:

```bat
cd C:\path\to\Pratt-Backend
py -3 path\to\rag_eval\evals\phase-3\zh-62-transfer.py
```

The script:

1. Switches to or creates `zh-62-hybrid-rag` from `main`.
2. Adds `_normalize_scores()` and `hybrid_search_folder()` to `data_assets/search.py`.
3. Imports `hybrid_search_folder` into `views_search.py`.
4. Generates `tests/app_retrieval/test_hybrid_search.py` (12 tests across `TestNormalizeScores`, `TestHybridSearchFolder`, `TestHybridIntegration`) and force-adds it.
5. Runs `pytest -m "not integration"` on the generated tests.
6. Commits locally without pushing.

## Why this is its own phase

Phase 3 is gated on Phase 1 (chatstream/temperature/structured-output landings) and Phase 2 (assistant fixtures + sources persistence) because hybrid retrieval is exercised by both the chat path and any assistant whose system prompt references retrieval strategy (e.g., zh-74's Research Assistant, which is documented to align with zh-62 hybrid routing). Run Phase 1 + Phase 2 first.

## Server entry point

The Pratt-Backend is async (Django Channels). End-to-end smoke for hybrid routing uses:

```bat
uvicorn app.wsgi:application --lifespan --host=0.0.0.0 --port=8000 --workers 1
```

Then:

```
GET /ws/search/folders/<pk>/?search_query=engine&keyword_search=hybrid
```

`manage.py` still handles migrations, management commands, shell access, and pytest.
