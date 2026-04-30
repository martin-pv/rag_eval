# ZH-64 - Files Stuck in Processing Watchdog

## Ticket Purpose

ZH-64 adds a Celery watchdog task that finds assets stuck in `in_progress` past a stale threshold and resets them to `error` so they can be retried or reprocessed.

## Generated Files and Code Changes

`zh-64-transfer.py` creates:

- `app_background/tasks/stuck_processing_watchdog.py`
- `tests/app_retrieval/test_stuck_processing.py`

## Reasoning, Choices, and Justification

A watchdog is a safety net for dropped Celery jobs, mid-process failures, or deadlocks that leave assets permanently stuck. It is intentionally conservative: old `in_progress` assets become `error`, making the failure visible and recoverable rather than silently retrying in a loop.

Rejected alternatives:

- Automatically requeueing stuck assets: could repeat the same failing processing path without visibility.
- Manual DB cleanup only: slow and error-prone during production incidents.
- Running without Dave confirmation: the ticket notes Dave may already have a lighter reprocess fix.

## Code Breakdown

- `reset_stuck_assets(stale_minutes=60)`: Celery task that filters stale `Asset(status="in_progress")` rows and updates them to `error`.
- Logging: records how many assets were reset and the cutoff used.
- Tests: verify stale query behavior, status update, and fresh assets remaining untouched.

## Runtime Setup and Test Playbook

Run from the backend repository root on the runtime machine, where `manage.py` lives unless the ticket says otherwise.

```cmd
cd C:\path\to\ENCHS-PW-GenAI-Backend
py -3 C:\path\to\rag_eval\evals\zh-64-transfer.py
```

On macOS/Linux:

```bash
cd /path/to/ENCHS-PW-GenAI-Backend
python3 /path/to/rag_eval/evals/phase-1/zh-64-transfer.py
```


Confirm with Dave that the watchdog is still needed before running.

Run tests:

```cmd
uv sync --group dev
uv run pytest tests/app_retrieval/test_stuck_processing.py -v
uv run python manage.py check
```

Manual Celery smoke test:

```cmd
uv run python manage.py shell -c "from app_background.tasks.stuck_processing_watchdog import reset_stuck_assets; print(reset_stuck_assets(stale_minutes=60))"
```

If approved for production, add a Celery Beat schedule separately after review.

## Git Add and Commit Guidance

This ticket generates a test, so force-add it if needed.

```cmd
git add app_background/tasks/stuck_processing_watchdog.py
git add -f tests/app_retrieval/test_stuck_processing.py
git commit -m "ZH-64: add stuck processing watchdog"
```
