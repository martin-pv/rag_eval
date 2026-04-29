# NGAIP-362 - Assemble Corpus and Gold Dataset

## Ticket Purpose

NGAIP-362 owns the evaluation corpus and gold dataset contract for the RAG evaluation program. It defines how approved PrattWise/Samba source material becomes validated gold rows with questions, reference answers, source identifiers, optional spans, chunk ids, tags, and generation provenance.

This ticket comes first in the implementation order because every downstream metric depends on a stable reference set:

1. `NGAIP-362`
2. `NGAIP-363`
3. `NGAIP-415`
4. `NGAIP-365`
5. `NGAIP-364`
6. `NGAIP-366`

## Runbook Decision

Use RAGAS for generating candidate testset rows from approved documents, but do not treat generated rows as gold automatically. RAGAS candidates must be reviewed by a human before promotion into the official gold JSONL file.

Pydantic is still used here because it validates the gold data schema. RAGAS evaluates RAG quality; Pydantic validates that the evaluation data is well-formed before the harness uses it.

## Generated Files

`ngaip-362-transfer.py` should generate:

- `app_retrieval/evaluation/config/gold_schema.py`
- `app_retrieval/evaluation/config/gold_schema.md`
- `app_retrieval/evaluation/config/ci_gold.jsonl`
- `app_retrieval/evaluation/gold_loader.py`
- `app_retrieval/evaluation/langchain_document_loader.py`
- `app_retrieval/evaluation/knowledge_graph_context.py`
- `app_retrieval/evaluation/testset_generator.py`
- `app_retrieval/evaluation/golden_test_generator.py`
- `app_retrieval/evaluation/gold_promoter.py`
- focused tests in `tests/app_retrieval/`

## Golden Set Flow

1. Use the existing PrattWise LanceDB vector store as the primary source of approved chunks.
2. Load LanceDB rows into LangChain `Document` objects with `asset_id`, `chunk_id`, content type, and source metadata.
3. Keep JSONL export loading only as an offline/redacted fallback.
4. Load or construct knowledge graph context for the same corpus.
5. Serialize KG nodes and relationships into readable context text.
6. Attach KG context to the LangChain documents before candidate generation.
7. Run the RAGAS `TestsetGenerator` to create candidate questions, reference answers, and supporting context.
8. Write candidates to `candidate_testset.jsonl`.
9. Human reviewers mark each candidate `approved`, `edited`, or `rejected`.
10. Promote only approved/edited candidates through `gold_promoter.py`.
11. Validate promoted rows with `GoldRow` before the official gold JSONL is used by the harness.

## LanceDB Loader Requirement

The loader should use `lancedb` to read the existing vector-store table and `langchain_core.documents.Document` as the adapter object for RAGAS. It should not create a separate vector store for evaluation. It must map the real table text field, preserve source metadata, and avoid copying vector columns into metadata.

## RAGAS Role

RAGAS is used for candidate testset generation, not for schema enforcement. The generated candidate rows should preserve:

- `candidate_id`
- question
- reference answer
- supporting context
- source metadata
- knowledge graph context
- generator metadata, including RAGAS version
- review status

## Non-Text Source Handling

For PDFs, tables, OCR, and mixed content, this ticket should preserve the retrieval system's text or markdown representation. RAGAS evaluates the text context that PrattWise provides to the model. It should not be expected to judge raw visuals unless the document pipeline converts those visuals into trustworthy textual/structured context.

Use `content_type` or metadata tags such as `text`, `table`, `ocr`, `graph`, or `mixed` so later reports can separate performance by source modality.

## Dependencies

This ticket depends on the shared RAGAS branch setup:

```cmd
uv add ragas datasets lancedb
uv add langchain langchain-core langchain-openai langchain-community
uv add --dev pytest pytest-django pytest-asyncio
uv sync --group dev
```

## Validation

Run structural tests first, without live model calls:

```cmd
uv run pytest tests/app_retrieval/test_gold_loader.py -v
uv run pytest tests/app_retrieval/test_langchain_document_loader.py -v
uv run pytest tests/app_retrieval/test_knowledge_graph_context.py -v
uv run pytest tests/app_retrieval/test_testset_generator.py -v
uv run pytest tests/app_retrieval/test_gold_promoter.py -v
```

Only run live RAGAS generation after Azure OpenAI settings and approved source documents are available.

## Branching and Commit Behavior

The runtime implementation should start from the parent `ragas-rag-evaluation` branch when available. The transfer script still bootstraps from local `main-backup-for-mac-claude-repo-04-07-2026` for repeatable transfer use, creates or switches to `ngaip-362-corpus-gold-dataset`, writes generated files, and makes a local commit without pushing.
