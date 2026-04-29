# ZH-67 - Structured JSON Streaming Output

## Ticket Purpose

ZH-67 ensures the `structured_output` request flag reaches `get_default_data()` so streaming OpenAI payloads request JSON-object output when needed.

## Generated Files and Code Changes

`zh-67-transfer.py` creates or updates:

- `app_chatbot/views/chatstream.py`
- `tests/app_chatbot/test_utils.py`

## Reasoning, Choices, and Justification

The smallest correct fix is to pass the already-parsed `structured_output` flag into `get_default_data`. The utility already owns response-format construction, so the view should not duplicate JSON-format logic.

Rejected alternatives:

- Building `response_format` directly in `chatstream.py`: duplicates `get_default_data` responsibility.
- Always enabling structured output: would break normal chat streaming.
- Adding a new endpoint: unnecessary because the existing request flag already exists.

## Code Breakdown

- One-line view patch: `get_default_data(stream=True, structured_output=structured_output)`.
- Tests: verify `structured_output=True` adds `response_format`, false/default omit it, stream flag is preserved, and required OpenAI keys remain present.

## Runtime Setup and Test Playbook

Run from the backend repository root on the runtime machine, where `manage.py` lives unless the ticket says otherwise.

```cmd
cd C:\path\to\ENCHS-PW-GenAI-Backend
py -3 C:\path\to\rag_eval\evals\zh-67-transfer.py
```

On macOS/Linux:

```bash
cd /path/to/ENCHS-PW-GenAI-Backend
python3 /path/to/rag_eval/evals/zh-67-transfer.py
```


Run tests:

```cmd
uv sync --group dev
uv run pytest tests/app_chatbot/test_utils.py -v
uv run python manage.py check
```

Manual smoke test: POST with `structured_output=true` and confirm the OpenAI payload contains `response_format: {"type": "json_object"}`.

## Git Add and Commit Guidance

This ticket generates a test, so force-add it if needed.

```cmd
git add app_chatbot/views/chatstream.py
git add -f tests/app_chatbot/test_utils.py
git commit -m "ZH-67: pass structured output flag into streaming payload"
```
