# NGAIP-362 - Assemble Corpus and Gold Dataset

## Ticket

NGAIP-362 creates the evaluation corpus contract for the RAG evaluation program. The goal is to define gold questions, gold answers, source document identifiers, and optional citation spans/chunk ids so later tickets can score retrieval, citations, and response quality against a stable reference set.

## Solution

This worktree adds the evaluation gold-row schema, a redacted CI fixture, a schema document for annotators, a JSONL loader, and focused pytest coverage. The transfer script writes those files into the runtime backend under `app_retrieval/evaluation/` and now bootstraps the ticket branch from local `main-backup-for-mac-claude-repo-04-07-2026` before applying generated files.

## Reasoning

The RAGAS-based evaluator still needs a clean reference dataset. Keeping the gold schema strict with `extra="forbid"` catches malformed rows early and gives the downstream harness predictable inputs. The sanitized CI fixture avoids controlled P&W data while still proving parser and validation behavior.

## Choices

- Use JSONL for CI because it preserves arrays and structured fields without CSV parsing ambiguity.
- Keep source identity fields explicit: `gold_doc_id`, optional char spans, and optional chunk ids.
- Treat schema validation errors as `ValueError` with row context so transfer/runtime failures are actionable.
- Keep branch setup inside `ngaip-362-transfer.py` so the Windows runtime machine does not need manual ticket-branch prep.
