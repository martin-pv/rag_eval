# eval_v2 RAGAS Transfer Scripts

These are second-pass transfer scripts for the NGAIP RAG evaluation tickets. They keep the ticket split, but use RAGAS more directly and lean into async orchestration because PrattWise retrieval and chat paths are async-heavy.

## Review Takeaways

- `wilsonIs/langchain-business-rag` keeps evaluation compact: collect RAG outputs, build `Dataset.from_list(...)`, call `ragas.evaluate(...)`, and wrap LangChain LLM/embedding objects with `LangchainLLMWrapper` and `LangchainEmbeddingsWrapper`.
- `vibrantlabsai/ragas` documents newer async/custom metric flows with `AsyncOpenAI`, `llm_factory`, and `DiscreteMetric`, which fits PrattWise-specific citation judgments that RAGAS does not natively know.
- V2 keeps RAGAS metrics primary: `context_precision`, `context_recall`, `faithfulness`, `answer_relevancy`, and `answer_correctness`. Deterministic source-id checks stay supplemental.

## Backend integration

- `ngaip-363-transfer-v2.py` ships a ModelHub-aware `ragas_factory_v2.py`: `EvaluatorModelConfig.provider` accepts `openai`, `azure_openai`, or `modelhub_azure_openai`. The `modelhub_azure_openai` path **reuses the existing PrattWise plumbing** instead of duplicating it:
  - **Token mint** — already handled by `app_background.background_tasks.modelhub.periodic_modelhub_processor` (started in `app_background/apps.py`). It performs the `client_credentials` POST to `MODELHUB_TOKEN_ENDPOINT` every ~10–15 minutes and stores the result in Django's cache as `MODELHUB_TOKEN`.
  - **Token consume** — the v2 factory calls `await cache.aget("MODELHUB_TOKEN", None)` (same call pattern as `app_chatbot/utils.py`, `app_chatbot/views/chatstream.py`, `app_retrieval/api_lancedb.py`, and `app_core/utils.py`) and assembles `Authorization: Bearer …` + `api-key` + `Ocp-Apim-Subscription-Key` exactly like `OpenAIStreamGenerator` does. No second cache, no second mint.
  - Settings come from `app.settings_intellisense.settings` first, then env vars (`OPENAI_API_LLM_KEY`, `OPENAI_API_LLM_ENDPOINT`).
- `ngaip-362-transfer-v2.py` writes `app_retrieval/evaluation/lancedb_loader.py`. `load_lancedb_documents(db_path, table_name)` returns `list[langchain_core.documents.Document]`, so testset generation reads from the existing PrattWise LanceDB vector store rather than a JSONL fixture.
- All v2 scripts touch the parent `app_retrieval/__init__.py` chain so pytest collection works on a clean clone.

## Scripts

**Per-script docs (what each ticket writes, prerequisites, merge order, manual pytest):** see **[eval_v2/docs/README.md](./docs/README.md)** and the linked `NGAIP-*-v2.md` pages.

Run from the backend repo root. Every script branches from `main`, writes ticket-scoped files, runs generated pytests, force-adds generated tests, and creates a local commit without pushing.

- `sample_gold_v2.jsonl` - 50-row sanitized fixture used by the 362/363 v2 scripts.
- `ngaip-362-transfer-v2.py` - gold schema, sample set install, async RAGAS testset candidate generation.
- `ngaip-363-transfer-v2.py` - async RAGAS runner, LangChain wrappers, `AsyncOpenAI`/`DiscreteMetric` support.
- `ngaip-412-transfer-v2.py` - async POC runner for validating the end-to-end RAGAS path.
- `ngaip-415-transfer-v2.py` - report schema and success criteria for RAGAS-primary metrics.
- `ngaip-365-transfer-v2.py` - context relevancy metric using RAGAS context metrics.
- `ngaip-364-transfer-v2.py` - citation accuracy using faithfulness plus async discrete citation judgment.
- `ngaip-366-transfer-v2.py` - response accuracy using answer correctness/relevancy plus faithfulness.

## Running on Windows

These scripts are written for the Windows runtime where Pratt-Backend lives. They have no shell-isms, no `~`, no `os.path.join` traps — `subprocess.run` always uses list arguments (no `shell=True`), and `Path` lets forward-slash strings work because pathlib normalizes separators.

**Two Windows-specific things the scripts already handle for you:**

1. **LF line endings on generated files.** Python's text mode on Windows translates `\n` to `\r\n` when writing. The shared `write()` helper in every v2 transfer script uses `target.write_bytes(content.encode("utf-8"))` instead of `write_text`, so the generated `.py` modules and `sample_gold.jsonl` keep `LF` regardless of platform. The JSONL append in `gold_dataset.py` uses `Path.open("a", encoding="utf-8", newline="\n")` for the same reason. This keeps git diffs clean across platforms; you do not need `core.autocrlf` set explicitly.
2. **Python launcher.** The scripts shell out via `sys.executable`, so the same interpreter that runs the transfer script is used for `pytest`. Invoke them with whichever launcher you have on PATH:

   ```bat
   py -3 evals\eval_v2\ngaip-363-transfer-v2.py
   :: or
   python evals\eval_v2\ngaip-363-transfer-v2.py
   ```

**Prerequisites on the runtime machine:**

- Git for Windows installed and on PATH (the scripts call `git switch`, which needs git ≥ 2.23 — Git for Windows ships ≥ 2.40).
- `pytest` available in the same environment as `sys.executable`. If you use `uv`, the scripts assume `uv sync --extra dev` (or your repo's equivalent) has put pytest into `.venv\Scripts`. Several transfer scripts call **`uv run pytest`** when `uv` is on `PATH` (see **docs/README.md**); others always use `python -m pytest` inside the script.
- `BACKEND = Path.cwd()` — run each script from the Pratt-Backend repo root, not from the `eval_v2` directory. Example flow:

   ```bat
   cd C:\path\to\Pratt-Backend
   git switch main
   py -3 path\to\rag_eval\eval_v2\ngaip-362-transfer-v2.py
   :: 362 creates ngaip-362-corpus-gold-dataset-v2 branch, writes files, runs pytest, commits locally
   git switch main
   git merge --no-ff ngaip-362-corpus-gold-dataset-v2
   py -3 path\to\rag_eval\eval_v2\ngaip-363-transfer-v2.py
   :: ...repeat for 364, 365, 366, 412, 415
   ```

**Optional but recommended:** add `* text=auto eol=lf` to the backend repo's `.gitattributes` so that any contributor on a different platform (or a misconfigured `core.autocrlf=true` user) doesn't accidentally re-introduce CRLF into the evaluation files. The transfer scripts already write LF, so this is belt-and-suspenders.

## Server entry point (ASGI / uvicorn)

The Pratt-Backend is async (Django Channels), so the API server runs under **uvicorn**, not `manage.py runserver`. The canonical local command is:

```bat
uvicorn app.wsgi:application --lifespan --host=0.0.0.0 --port=8000 --workers 1
```

Implications for the v2 evaluation flow:

- **The transfer scripts and generated pytest suites do _not_ require the API server to be running.** They import the harness, factory, and metrics directly inside the test process and call `cache.aget("MODELHUB_TOKEN", ...)` against the in-process Django cache.
- **The ModelHub token refresh task (`app_background.background_tasks.modelhub.periodic_modelhub_processor`) only runs when the ASGI app boots.** If you need a fresh token in the cache for a long-running RAGAS evaluation against live ModelHub, start uvicorn first; otherwise the v2 factory will return `None` from `aget("MODELHUB_TOKEN")` and you must seed the cache yourself in the test (or pass `provider="openai"` / `provider="azure_openai"` and use a static API key).
- **`--workers 1` is the recommended setting for evaluation runs** because LanceDB and Django's in-process cache are per-process. With multiple workers each worker has its own cache and its own ModelHub token, which is fine for serving traffic but wastes mints during evaluation.
- **Migrations, management commands, and `pytest` still go through `manage.py`** — uvicorn only replaces the long-lived HTTP server. So `python manage.py migrate`, `python manage.py create_doc_builder_assistant`, and `python -m pytest` all keep working unchanged.
