# NGAIP-365 - Implement Context Relevancy Metric

## Ticket

NGAIP-365 measures whether retrieved context is relevant to the gold reference for each evaluation question. The original acceptance criteria mentioned chunk-overlap scoring; the updated program decision is to use RAGAS as the primary RAG evaluator framework.

## Solution

This worktree owns context relevancy scoring for the harness. The updated direction is to report RAGAS context precision and context recall as primary metrics, while keeping token overlap as a secondary diagnostic and CI-friendly compatibility check for the original chunk-overlap acceptance criterion.

## Reasoning

Token overlap is cheap and deterministic, but it misses semantic matches and can reward superficial lexical overlap. RAGAS provides a stronger evaluator path for context usefulness while still allowing the harness to keep deterministic overlap for smoke tests and debugging retrieval regressions.

## Choices

- Use RAGAS context precision/recall as the primary context relevancy metrics.
- Keep `token_overlap_at_k` or equivalent as a secondary diagnostic field.
- Record evaluator provider/model/deployment metadata in reports for reproducibility.
- Avoid front-end dependencies; retrieve through Pratt-Backend harness adapters.
- Keep branch setup inside `ngaip-365-transfer.py` so Windows runtime deployment starts from `main-backup-for-mac-claude-repo-04-07-2026`.
