# Workflow — rag_eval ↔ Pratt-Backend

## Prerequisites

- **Git** on `PATH` (transfer scripts run `git switch`, `git commit`).
- Backend dev env with **pytest** and imports used by generated tests (`ragas`, `langchain_core`, `pydantic`, `datasets`, etc.) — typically **`uv sync --extra dev`** or your team’s setup.

## Run a v2 transfer script

Always from **Pratt-Backend root**:

```bash
cd /path/to/Pratt-Backend
git switch main
uv run python /path/to/rag_eval/eval_v2/ngaip-362-transfer-v2.py
```

The script creates a **feature branch**, writes files under **`app_retrieval/`** and **`tests/`**, runs **pytest**, and makes a **local commit** (no push).

### v2 merge order

See **[eval_v2/docs/README.md](../eval_v2/docs/README.md)**. Summary: **362 → 363 → 364/365/366 → 412 → 415** (metrics after harness).

## Run ZenHub / flat `evals/` transfers

Scripts live under **`evals/`** (and may use phase subfolders in other branches). Same rule: **`cwd` = backend root** unless the script docstring says otherwise.

## pytest / uv

Many scripts use **`uv run pytest`** when `shutil.which("uv")` succeeds; others use **`sys.executable -m pytest`**. To rerun manually:

```bash
cd /path/to/Pratt-Backend
uv run pytest path/to/test_file.py -v
```

## Windows

See **`eval_v2/README.md`** — LF line endings, `py -3`, no `shell=True` in subprocess lists.
