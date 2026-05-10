# Workflow — rag_eval ↔ Pratt-Backend

**Windows** is the primary environment called out for this program; commands below show **cmd/PowerShell** first.

## Prerequisites

- **Git for Windows** on `PATH` (transfer scripts run `git switch`, `git commit`).
- Backend dev env with **pytest** and imports used by generated tests (`ragas`, `langchain_core`, `pydantic`, `datasets`, etc.) — typically **`uv sync --extra dev`** or your team’s setup.
- **Python launcher** `py -3` available (recommended on Windows so `sys.executable` matches what you expect).

## Run a v2 transfer script

**Always** set the current directory to the **Pratt-Backend root** before running (example: `C:\work\Pratt-Backend`).

**PowerShell / cmd:**

```bat
cd /d C:\work\Pratt-Backend
git switch main
uv run python C:\work\rag_eval\eval_v2\ngaip-362-transfer-v2.py
```

If you are not using `uv`:

```bat
cd /d C:\work\Pratt-Backend
git switch main
py -3 C:\work\rag_eval\eval_v2\ngaip-362-transfer-v2.py
```

The script creates a **feature branch**, writes files under **`app_retrieval/`** and **`tests/`**, runs **pytest**, and makes a **local commit** (no push).

### v2 merge order

See **[eval_v2/docs/README.md](../eval_v2/docs/README.md)**. Summary: **362 → 363 → 364/365/366 → 412 → 415** (metrics after harness).

## Run ZenHub / `evals/` transfers

Scripts live under **`evals/`** (including **`phase-*`** subfolders on current branches). Same rule: **`cwd` = backend root** unless the script docstring says otherwise.

## pytest / uv

Many scripts use **`uv run pytest`** when `shutil.which("uv")` succeeds; otherwise they use **`sys.executable -m pytest`** (on Windows that is usually the interpreter that launched the transfer script — prefer **`py -3 -m pytest`** when running manually without `uv`).

**Examples (from backend root):**

```bat
cd /d C:\work\Pratt-Backend
uv run pytest tests\app_retrieval\test_gold_dataset_v2.py -v
```

```bat
cd /d C:\work\Pratt-Backend
py -3 -m pytest tests\app_retrieval\test_gold_dataset_v2.py -v
```

## Windows — line endings and subprocess

The v2 transfer scripts avoid **`shell=True`** and use list arguments for `subprocess`; several use **`write_bytes`** so generated files stay **LF** on Windows. Details: **[eval_v2/README.md](../eval_v2/README.md)** (“Running on Windows”).
