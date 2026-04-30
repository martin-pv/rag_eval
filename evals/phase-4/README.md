# Phase 4

ZenHub tickets planned for this phase:

- `zh-57` – _placeholder, transfer script not yet authored_
- `zh-59` – _placeholder, transfer script not yet authored_

When the transfer scripts land, the layout will mirror the other phases:

| Transfer script | Ticket summary |
| --- | --- |
| `zh-57-transfer.py` | `zh-57-ticket-summary.md` |
| `zh-59-transfer.py` | `zh-59-ticket-summary.md` |

## Conventions to follow when adding scripts

To stay consistent with phases 1–3, each new transfer script must:

1. Branch from `main` (`git switch main`, then `git switch -c zh-NN-<slug>`).
2. Use the shared helpers (`patch`, `ensure`, `touch`) and `subprocess.run([...], check=True)` — no `shell=True`.
3. Write generated files with `Path.write_bytes(content.encode("utf-8"))` to keep LF endings on Windows runtimes.
4. Generate at least 3 goal-driven tests (string-level checks are fine where Django setup would be heavyweight) and force-add them via `git add -f`.
5. Run `pytest` on the generated test file before committing.
6. Commit locally with the message format `ZH-NN: <imperative summary>` and **do not push**.

See `evals/phase-1/zh-67-transfer.py` and `evals/phase-2/zh-44-transfer.py` for the cleanest reference implementations.

## Server entry point

The Pratt-Backend is async (Django Channels). Any HTTP-end-to-end checks should start the server with:

```bat
uvicorn app.wsgi:application --lifespan --host=0.0.0.0 --port=8000 --workers 1
```

`manage.py runserver` is **not** the entry point on this backend.
