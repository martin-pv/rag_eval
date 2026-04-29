# NGAIP-415 - RAG Evaluation Metrics and Success Criteria

## Ticket

NGAIP-415 defines the metric catalog, report schema, thresholds, and success criteria for the RAG evaluation program. It is the contract that NGAIP-363, NGAIP-364, NGAIP-365, and NGAIP-366 implement against.

## Solution

This worktree produces `metrics_spec.yaml`, `eval_report.schema.json`, a human-readable metrics document, and structural tests. The updated direction is RAGAS-first: context relevancy, grounding, and response quality should be expressed as RAGAS-backed metrics where possible, with deterministic PrattWise adapters retained for source/span metadata and CI diagnostics.

## Reasoning

A versioned metrics contract keeps the harness, reports, and stakeholder review aligned. RAGAS gives the program a standard evaluator framework, but PrattWise still needs explicit metadata checks for citations, source ids, and branch/runtime reproducibility.

## Choices

- Treat RAGAS metrics as primary for semantic RAG evaluation.
- Keep deterministic adapters for citation metadata and token-overlap diagnostics.
- Store evaluator metadata in report output: provider, deployment/model, temperature, and spec version.
- Leave numeric thresholds in review until calibration on the NGAIP-362 corpus.
- Keep branch setup inside `ngaip-415-transfer.py` so Windows runtime deployment starts from `main-backup-for-mac-claude-repo-04-07-2026`.
