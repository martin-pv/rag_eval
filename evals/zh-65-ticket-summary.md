# ZH-65 - Deduplicate Folders / Fix exists() Bug

## Ticket Purpose

ZH-65 fixes two issues in the `assets_search` folder extension: inverted folder existence logic and duplicated folder names in generated tool descriptions.

## Generated Files and Code Changes

`zh-65-transfer.py` creates or updates:

- `app_extensions/extensions_standard/assets_search/api_folders.py`
- `tests/app_extensions/test_folder_dedup.py`

## Reasoning, Choices, and Justification

The bug fix is surgical because extension code is shared by chat tools. The `exists() == 0` pattern is logically confusing and inverted under `not`; replacing it with `if not folders.exists():` matches the intended behavior. Deduping by primary key prevents repeated folder names when querysets yield duplicates.

Rejected alternatives:

- Rewriting the whole extension: unnecessary and higher risk.
- Deduping by folder name only: different folders can share names; primary key is safer.
- Leaving duplicate descriptions: harms tool-selection prompts and user clarity.

## Code Breakdown

- Existence fix: changes the no-folder guard to `if not folders.exists():`.
- Dedup fix: builds `folder_names` through an async loop with `seen_pks`.
- Tests: verify valid folders no longer raise, missing folders still raise, and duplicate PKs appear once.

## Runtime Setup and Test Playbook

Run from the backend repository root on the runtime machine, where `manage.py` lives unless the ticket says otherwise.

```cmd
cd C:\path\to\ENCHS-PW-GenAI-Backend
py -3 C:\path\to\rag_eval\evals\zh-65-transfer.py
```

On macOS/Linux:

```bash
cd /path/to/ENCHS-PW-GenAI-Backend
python3 /path/to/rag_eval/evals/zh-65-transfer.py
```


Run tests:

```cmd
uv sync --group dev
uv run pytest tests/app_extensions/test_folder_dedup.py -v
uv run python manage.py check
```

Manual smoke test: ask the assets search tool to describe/search duplicate folder selections and confirm folder names are not repeated.

## Git Add and Commit Guidance

This ticket generates a test, so force-add it if needed.

```cmd
git add app_extensions/extensions_standard/assets_search/api_folders.py
git add -f tests/app_extensions/test_folder_dedup.py
git commit -m "ZH-65: fix folder existence and dedup folder descriptions"
```
