# ZH-61 - Temperature API for Streaming Responses

## Ticket Purpose

ZH-61 allows `/streaming_response/` callers to pass an optional `temperature` value that is forwarded into the OpenAI request payload while preserving existing behavior when the field is omitted.

## Generated Files and Code Changes

`zh-61-transfer.py` updates:

- `app_chatbot/views/chatstream.py` (two hunks: parse `temperature`, clamp into `data`)
- **`tests/app_chatbot/test_temperature_patch.py`** — six string-level regression tests that assert the patch text landed (no full DRF / async streaming harness required)

The script runs `pytest` on that file, then **`git add`** the chatstream file and **`git add -f`** the test file so it is staged even when `tests/` is listed in `.gitignore`.

### Where files land (paths)

All paths are under the **Django project root**: the directory that contains `app_chatbot/`, not necessarily your monorepo root.

| Layout | Example `cd` before `py -3 ...zh-61-transfer.py` | Test file |
| --- | --- | --- |
| Flat backend | `cd C:\path\to\ENCHS-PW-GenAI-Backend` | `tests/app_chatbot/test_temperature_patch.py` |
| `backend/` subfolder | `cd C:\path\to\YourRepo\backend` **or** stay at `YourRepo` (script auto-picks `backend/`) | same relative path **under** `backend/` |

If you run from the wrong folder, the script exits before writing tests — you will see **`chatstream.py` not found** and **no** `tests/...` file.

### If you already ran once without tests

Pull the latest `rag_eval` `phase-1/zh-61-transfer.py`, `cd` to the correct Django root (or repo root with a `backend/` child), and run again. The patch steps are idempotent; the test file is overwritten.

### Manual `git add -f` (optional)

If you prefer not to rely on the script’s commit step:

```cmd
git add app_chatbot/views/chatstream.py
git add -f tests/app_chatbot/test_temperature_patch.py
```

From a monorepo root where paths are `backend/...`, prefix with `backend/` (or run `git add` from `backend/` using paths the script prints).

## Reasoning, Choices, and Justification

The implementation parses temperature near the other request flags, converts it to `float`, ignores invalid values, and clamps valid values to OpenAI's supported `0.0` to `2.0` range. This keeps the API forgiving while preventing unsafe model parameters.

Rejected alternatives:

- Rejecting invalid temperature with `400`: more disruptive for an optional tuning field.
- Passing raw user input to OpenAI: unsafe and could break provider requests.
- Changing default temperature globally: would alter existing behavior for every caller.

## Code Breakdown

- Request parsing block: reads `request.data["temperature"]`, converts to float, and falls back to `None` on invalid input.
- Payload patch: after `get_default_data(stream=True)`, sets `data["temperature"]` only when a valid value is provided.
- Clamp: `max(0.0, min(2.0, temperature))` keeps the value provider-safe.

## Runtime Setup and Test Playbook

Run from the backend repository root on the runtime machine, where `manage.py` lives unless the ticket says otherwise.

```cmd
cd C:\path\to\ENCHS-PW-GenAI-Backend
py -3 C:\path\to\rag_eval\evals\zh-61-transfer.py
```

On macOS/Linux:

```bash
cd /path/to/ENCHS-PW-GenAI-Backend
python3 /path/to/rag_eval/evals/phase-1/zh-61-transfer.py
```


Run checks:

```cmd
uv sync --group dev
uv run python manage.py check
```

Manual smoke tests:

- POST without `temperature`; behavior should be unchanged.
- POST with `temperature=0.9`; OpenAI payload should contain `temperature: 0.9`.
- POST with `temperature=5.0`; OpenAI payload should contain `temperature: 2.0`.
- POST with invalid `temperature`; payload should omit the override.

## Git Add and Commit Guidance

No generated tests are created, so `git add -f` is not required.

```cmd
git add app_chatbot/views/chatstream.py
git commit -m "ZH-61: accept optional streaming temperature"
```
