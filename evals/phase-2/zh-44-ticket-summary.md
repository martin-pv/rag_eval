# ZH-44 - Persist Sources on User ChatResponse

## Ticket Purpose

ZH-44 ensures user-sent messages preserve attachment source context. When a user sends a message with uploaded `asset_ids`, the user `ChatResponse` should persist a `sources` list so refresh/restart keeps document linkage.

## Generated Files and Code Changes

`zh-44-transfer.py` creates or updates:

- `app_chatbot/views/chatstream.py`
- `tests/app_chatbot/test_chatstream_sources.py`

## Reasoning, Choices, and Justification

The design stores attachment sources on the user message at creation time rather than reconstructing them later. This matches the product requirement: the user message itself should remember which documents were attached.

Rejected alternatives:

- Recomputing sources from request payload during history rendering: impossible after refresh because request payload is gone.
- Persisting only assistant citations: misses the user-side context link.
- Accepting every `asset_id` shape blindly: booleans, zero, negative values, and non-numeric strings can corrupt source metadata.

## Code Breakdown

- `_build_attachment_sources(asset_ids)`: normalizes positive integer and numeric-string asset IDs into `{"source_type": "attachment", "asset_id": id}` records.
- `ChatResponse.objects.acreate(...)`: now passes `sources=attachment_sources` for the user message.
- Test file: covers source normalization and verifies the user-message `acreate` call receives `sources`.

## Runtime Setup and Test Playbook

Run from the backend repository root on the runtime machine, where `manage.py` lives unless the ticket says otherwise.

```cmd
cd C:\path\to\ENCHS-PW-GenAI-Backend
py -3 C:\path\to\rag_eval\evals\zh-44-transfer.py
```

On macOS/Linux:

```bash
cd /path/to/ENCHS-PW-GenAI-Backend
python3 /path/to/rag_eval/evals/phase-2/zh-44-transfer.py
```


Run tests:

```cmd
uv sync --group dev
uv run pytest tests/app_chatbot/test_chatstream_sources.py -v
```

Manual integration smoke test:

1. POST a chat message with `asset_ids`.
2. Fetch conversation history.
3. Confirm the user message JSON includes `sources` with `source_type: attachment` and the expected `asset_id` values.

## Git Add and Commit Guidance

This ticket generates a test under `tests/`, so force-add it if `.gitignore` blocks tests.

```cmd
git add app_chatbot/views/chatstream.py
git add -f tests/app_chatbot/test_chatstream_sources.py
git commit -m "ZH-44: persist attachment sources on user messages"
```
