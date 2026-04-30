# Phase 2

ZenHub tickets in this phase:

- `zh-35` – GenAI Advanced Auth: registration API (`RegisterGenAIView`)
- `zh-44` – persist sources on user `ChatResponse`
- `zh-45` – add `xclass_level` (export-control classification) to Folder model + API
- `zh-73` – Document Builder management command
- `zh-74` – Research Assistant fixture + system instructions

Each ticket has two files:

| Transfer script | Ticket summary |
| --- | --- |
| `zh-35-transfer.py` | `zh-35-ticket-summary.md` |
| `zh-44-transfer.py` | `zh-44-ticket-summary.md` |
| `zh-45-transfer.py` | `zh-45-ticket-summary.md` |
| `zh-73-transfer.py` | `zh-73-ticket-summary.md` |
| `zh-74-transfer.py` | `zh-74-ticket-summary.md` |

## Running a ticket

Run the transfer script from the Pratt-Backend repo root:

```bat
cd C:\path\to\Pratt-Backend
py -3 path\to\rag_eval\evals\phase-2\zh-44-transfer.py
```

Each script:

1. Switches to or creates a ticket-named branch from `main`.
2. Applies the patch (idempotent).
3. Generates a focused `tests/...` file and force-adds it (`git add -f`).
4. Runs `pytest` on the generated test file.
5. Commits locally without pushing.

## Server entry point

The Pratt-Backend is async (Django Channels). Manual API smoke tests use:

```bat
uvicorn app.wsgi:application --lifespan --host=0.0.0.0 --port=8000 --workers 1
```

`manage.py` still handles migrations, management commands (incl. `create_doc_builder_assistant` from zh-73), shell access, and pytest.
