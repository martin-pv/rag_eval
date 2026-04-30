# Phase 1

ZenHub tickets in this phase:

- `zh-61` – accept optional `temperature` on `/streaming_response/`
- `zh-63` – AutoSAM CORS prod origin in `app/settings.py`
- `zh-64` – stuck-processing assets cleanup management command
- `zh-65` – folder validation guardrail (`call_does_not_raise_when_folders_exist`, etc.)
- `zh-67` – structured-output / `response_format` plumbing on chatstream

Each ticket has two files:

| Transfer script | Ticket summary |
| --- | --- |
| `zh-61-transfer.py` | `zh-61-ticket-summary.md` |
| `zh-63-transfer.py` | `zh-63-ticket-summary.md` |
| `zh-64-transfer.py` | `zh-64-ticket-summary.md` |
| `zh-65-transfer.py` | `zh-65-ticket-summary.md` |
| `zh-67-transfer.py` | `zh-67-ticket-summary.md` |

## Running a ticket

Run the transfer script from the Pratt-Backend repo root (the directory that contains `manage.py`):

```bat
cd C:\path\to\Pratt-Backend
py -3 path\to\rag_eval\evals\phase-1\zh-63-transfer.py
```

Each script:

1. Switches to or creates a ticket-named branch from `main`.
2. Applies the patch (idempotent — safe to re-run).
3. Generates a focused `tests/...` file and force-adds it (`git add -f`).
4. Runs `pytest` on the generated test file.
5. Commits locally without pushing.

## Server entry point

The Pratt-Backend is async (Django Channels). Manual API smoke tests use:

```bat
uvicorn app.wsgi:application --lifespan --host=0.0.0.0 --port=8000 --workers 1
```

`manage.py` still handles migrations, management commands, shell access, and pytest.
