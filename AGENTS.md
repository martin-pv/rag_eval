# rag_eval — agent instructions

This repository holds **evaluation and transfer tooling** (RAGAS, ZenHub-style scripts) for **PrattWise / Pratt-Backend**. It is **not** the Django backend; generated code is meant to be applied **into** the backend repo.

## Working directory

- **Transfer scripts** assume **`Path.cwd()` is the Pratt-Backend repository root** (the tree that contains `manage.py` / `app_retrieval`, etc.). Run them from there, not from `rag_eval/`.

  ```bash
  cd /path/to/Pratt-Backend
  uv run python /path/to/rag_eval/eval_v2/ngaip-362-transfer-v2.py
  ```

- **`rag_eval`** path can be a clone, worktree, or symlink — only the script path matters.

## Layout

| Path | Purpose |
|------|---------|
| `eval_v2/` | NGAIP **v2** RAGAS transfer scripts + `sample_gold_v2.jsonl` + [docs](./eval_v2/docs/README.md) |
| `evals/` | Ticket transfer scripts, runbooks, ZenHub (`zh-*`), NGAIP v1-style (`ngaip-*`), reference snippets |
| `scripts/` | Sync / worktree helpers |
| `toolkit/` | **Poolside skills**, workflow notes, copy-paste setup ([README](./toolkit/README.md)) |

## Conventions

- Prefer **`uv run python`** / **`uv run pytest`** when `uv` is available; several scripts fall back to `python -m pytest`.
- Do **not** commit API keys, tokens, or tenant-specific config. Use env / backend settings only.
- Keep changes **ticket-scoped**; avoid unrelated refactors in generated backend files.
- v2 **merge order** and per-ticket behavior: see `eval_v2/docs/README.md`.

## Poolside / IDE

- Copy or symlink skills from `toolkit/poolside-skills/` into `~/.config/poolside/skills/` or `.poolside/skills/` (see `toolkit/POOLSIDE.md`).
- This file is the repo-level **`AGENTS.md`** for tools that read it (e.g. Poolside).
