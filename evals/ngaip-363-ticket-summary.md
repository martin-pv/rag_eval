# NGAIP-363 - Build RAG Evaluation Harness

## Ticket

NGAIP-363 builds the reusable Pratt-Backend harness that runs RAG evaluations against gold data, selected retrievers, and metric modules. It is the execution layer for NGAIP-362, NGAIP-364, NGAIP-365, NGAIP-366, and NGAIP-415.

## Solution

This worktree creates the `app_retrieval/evaluation/` package, Django management command, retriever adapters, reporter scaffolding, metric stubs/adapters, config fixtures, and tests. The transfer script adds RAGAS dependencies and generated harness files, and now bootstraps the ticket branch from current `main` before applying changes.

## Reasoning

The harness should run in-process instead of through HTTP. In-process execution avoids auth and networking complexity, uses the real Django models/settings, and still exercises production retrieval functions. RAGAS is the primary evaluator framework for NGAIP RAG metrics, while deterministic PrattWise-specific adapters handle metadata checks that RAGAS cannot infer.

## Choices

- Use `python manage.py rag_eval run --config ...` for Django-native execution.
- Keep retriever selection configurable: semantic, keyword, and hybrid.
- Emit both `report.json` and `report.csv` for machine validation and stakeholder review.
- Gate live RAGAS/model calls through config so CI can run on redacted fixtures without credentials.
- Keep branch setup inside `ngaip-363-transfer.py` so runtime deployment starts from current `main`.
