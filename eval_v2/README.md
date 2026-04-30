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

Run from the backend repo root. Every script branches from `main`, writes ticket-scoped files, runs generated pytests, force-adds generated tests, and creates a local commit without pushing.

- `sample_gold_v2.jsonl` - 50-row sanitized fixture used by the 362/363 v2 scripts.
- `ngaip-362-transfer-v2.py` - gold schema, sample set install, async RAGAS testset candidate generation.
- `ngaip-363-transfer-v2.py` - async RAGAS runner, LangChain wrappers, `AsyncOpenAI`/`DiscreteMetric` support.
- `ngaip-412-transfer-v2.py` - async POC runner for validating the end-to-end RAGAS path.
- `ngaip-415-transfer-v2.py` - report schema and success criteria for RAGAS-primary metrics.
- `ngaip-365-transfer-v2.py` - context relevancy metric using RAGAS context metrics.
- `ngaip-364-transfer-v2.py` - citation accuracy using faithfulness plus async discrete citation judgment.
- `ngaip-366-transfer-v2.py` - response accuracy using answer correctness/relevancy plus faithfulness.
