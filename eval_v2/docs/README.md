# eval_v2 transfer scripts — documentation index

These pages describe each **`ngaip-*-transfer-v2.py`** script: what it installs into **Pratt-Backend**, how to run it, and how to verify the result.

## Quick start (runtime machine)

1. Use the **Pratt-Backend** repository root as the current working directory (`BACKEND = Path.cwd()` in every script). On **Windows**, use **`cd /d D:\path`** in **cmd** when changing drives.
2. Ensure **Git** is on `PATH` (the scripts run `git switch`, `git add`, `git commit`).
3. Install backend dev dependencies so **pytest** (and imports like `ragas`, `langchain_core`, `pydantic`, `datasets`) resolve — e.g. `uv sync --extra dev` or your team’s equivalent.
4. Run a transfer script with the **same interpreter** you use for the backend (or use **`uv run python`** / **`uv run`** so the project venv is active).

Example (Unix):

```bash
cd /path/to/Pratt-Backend
git switch main
uv run python /path/to/rag_eval/eval_v2/ngaip-362-transfer-v2.py
```

Example (Windows — **cmd**; paths from [eval_v2 README](../README.md)):

```bat
cd /d C:\path\to\Pratt-Backend
git switch main
uv run python C:\path\to\rag_eval\eval_v2\ngaip-362-transfer-v2.py
```

If you do not use `uv`, use `py -3` instead of `python` so the launcher matches your install:

```bat
py -3 C:\path\to\rag_eval\eval_v2\ngaip-362-transfer-v2.py
```

## Pytest / `uv` behavior

- Several v2 scripts (**364, 365, 366, 412, 415**) run tests with **`uv run pytest …`** when `uv` is on `PATH`, otherwise **`python -m pytest …`** (same as `sys.executable`).
- **362** and **363** currently invoke **`sys.executable -m pytest`** in the embedded helpers (no `uv` branch in those copies). You can still run tests yourself with `uv run pytest <path>`.
- All subprocess pytest calls use **`cwd` = backend root**.

## Recommended branch / merge order

The scripts create **ticket-named branches** and **local commits** (no push). Merge in this order so modules and tests line up:

| Order | Ticket | Branch (from script)        | Doc |
|-------|--------|-----------------------------|-----|
| 1 | NGAIP-362 | `ngaip-362-corpus-gold-dataset-v2` | [NGAIP-362-v2.md](./NGAIP-362-v2.md) |
| 2 | NGAIP-363 | `ngaip-363-rag-evaluation-harness-v2` | [NGAIP-363-v2.md](./NGAIP-363-v2.md) |
| 3 | NGAIP-364–366 | metric branches (any order after 363) | [NGAIP-364-v2.md](./NGAIP-364-v2.md), [365](./NGAIP-365-v2.md), [366](./NGAIP-366-v2.md) |
| 4 | NGAIP-412 | `ngaip-412-rag-eval-harness-poc-v2` | [NGAIP-412-v2.md](./NGAIP-412-v2.md) |
| 5 | NGAIP-415 | `ngaip-415-metrics-success-criteria-v2` | [NGAIP-415-v2.md](./NGAIP-415-v2.md) |

**364 / 365 / 366** assume **`async_ragas_runner`** and **`ragas_factory_v2`** from **363** exist (they import them). **412** needs **362**’s **`gold_dataset`** and **363**’s runner stack.

## Per-ticket pages

- [NGAIP-362-v2.md](./NGAIP-362-v2.md) — Gold schema, dataset helpers, LanceDB loader, candidate generation, sample JSONL.
- [NGAIP-363-v2.md](./NGAIP-363-v2.md) — Async RAGAS runner, model factory (OpenAI / Azure / ModelHub), YAML eval config.
- [NGAIP-364-v2.md](./NGAIP-364-v2.md) — Citation accuracy metric bundle + discrete judgment hook.
- [NGAIP-365-v2.md](./NGAIP-365-v2.md) — Context relevancy metric set (RAGAS context + answer relevancy).
- [NGAIP-366-v2.md](./NGAIP-366-v2.md) — Response accuracy metric set.
- [NGAIP-412-v2.md](./NGAIP-412-v2.md) — End-to-end async POC runner (`run_poc` / `run_poc_sync`).
- [NGAIP-415-v2.md](./NGAIP-415-v2.md) — Report dataclass and RAGAS-primary vs deterministic supplement fields.

## More context

Architecture notes, ModelHub/cache behavior, Windows LF handling, and **uvicorn** vs **pytest** are in the parent **[eval_v2 README](../README.md)**.
