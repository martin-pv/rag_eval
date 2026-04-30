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

## Where tests live and `git add -f`

| Ticket | Generated test file(s) | Staged with |
| --- | --- | --- |
| zh-61 | `tests/app_chatbot/test_temperature_patch.py` | `git add -f` after `pytest` |
| zh-63 | `tests/test_cors.py` | `git add -f` |
| zh-64 | `tests/app_retrieval/test_stuck_processing.py` | `git add -f` |
| zh-65 | (embedded in script; path in script output) | per script |
| zh-67 | under `tests/app_chatbot/` (see script) | `git add -f` if present |

**zh-61** always prints the absolute path to the test file and explicitly logs `git add -f …` so you can copy-paste if your repo ignores `tests/`.

Not every script in this folder follows the same branch/checkout pattern — open the `zh-*-transfer.py` header for its exact behavior.

## Django project root vs. monorepo layout

Some checkouts keep Django under a **`backend/`** subfolder (e.g. `YourRepo/backend/app_chatbot/...`). **zh-61** auto-detects that: if `app_chatbot/views/chatstream.py` is not in the current directory but exists under `./backend/`, it uses `backend/` as the Django root for patching, tests, and pytest. **Git** commands still use paths relative to `git rev-parse --show-toplevel` so `git add` works from a monorepo root.

Other phase-1 scripts may still require you to `cd` into the same folder as `manage.py` / `app_chatbot/` — check each script’s error message.

## Running a ticket

Run from the **Django project root** (the directory that contains `manage.py` and `app_chatbot/`), or from the monorepo root when the script supports it (zh-61 does for `backend/` children):

```bat
cd C:\path\to\...\backend
py -3 path\to\rag_eval\evals\phase-1\zh-61-transfer.py
```

Example for a flat clone:

```bat
cd C:\path\to\ENCHS-PW-GenAI-Backend
py -3 path\to\rag_eval\evals\phase-1\zh-63-transfer.py
```

Each script typically:

1. Applies the patch (idempotent — safe to re-run where documented).
2. Writes or updates a focused `tests/...` module.
3. Runs `pytest` on that file (when dependencies are installed).
4. Stages changes; **generated tests use `git add -f`** when `tests/` might be gitignored.
5. May commit locally without pushing (behavior varies by ticket — zh-61 commits if there is anything staged).

## Server entry point

The Pratt-Backend is async (Django Channels). Manual API smoke tests use:

```bat
uvicorn app.wsgi:application --lifespan --host=0.0.0.0 --port=8000 --workers 1
```

`manage.py` still handles migrations, management commands, shell access, and pytest.
