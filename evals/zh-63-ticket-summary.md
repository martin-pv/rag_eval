# ZH-63 - Production CORS for AutoSAM Origin

## Ticket Purpose

ZH-63 allows the production AutoSAM origin to call the PrattWise backend by updating Django CORS settings and adding regression coverage for allowed and blocked origins.

## Generated Files and Code Changes

`zh-63-transfer.py` creates or updates:

- `app/settings.py`
- `tests/test_cors.py`

## Reasoning, Choices, and Justification

CORS should be explicit and reviewed because it controls browser access from production domains. The script intentionally prompts for confirmation with Dave before running because the exact origin and any already-merged fix must be verified.

Rejected alternatives:

- Allowing `*` broadly: too permissive for production authenticated APIs.
- Skipping tests: CORS regressions are easy to reintroduce during settings changes.
- Hardcoding without confirmation: risky because production hostname details were still being coordinated.

## Code Breakdown

- `AUTOSAM_ORIGIN`: the production origin to allow, currently `https://autosam.prattwhitney.com` pending confirmation.
- Settings patch: adds the origin to `CORS_ALLOWED_ORIGINS` or regex settings where present.
- Tests: verify allowed origin receives CORS headers and unknown origins do not.

## Runtime Setup and Test Playbook

Run from the backend repository root on the runtime machine, where `manage.py` lives unless the ticket says otherwise.

```cmd
cd C:\path\to\ENCHS-PW-GenAI-Backend
py -3 C:\path\to\rag_eval\evals\zh-63-transfer.py
```

On macOS/Linux:

```bash
cd /path/to/ENCHS-PW-GenAI-Backend
python3 /path/to/rag_eval/evals/zh-63-transfer.py
```


The script is interactive. Type `yes` only after confirming the exact production origin and whether Dave already merged a fix.

Run tests:

```cmd
uv sync --group dev
uv run pytest tests/test_cors.py -v
uv run python manage.py check
```

Manual smoke test from a browser or curl OPTIONS request should confirm the production origin receives `Access-Control-Allow-Origin`.

## Git Add and Commit Guidance

This ticket generates a test, so force-add it if needed.

```cmd
git add app/settings.py
git add -f tests/test_cors.py
git commit -m "ZH-63: allow AutoSAM production CORS origin"
```
