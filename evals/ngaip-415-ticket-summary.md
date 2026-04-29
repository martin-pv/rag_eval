# NGAIP-415 - RAG Evaluation Metrics and Success Criteria

## Ticket Purpose

NGAIP-415 owns the metric catalog, report schema, threshold policy, and stakeholder success criteria for the RAG evaluation program. It is the contract that `NGAIP-363` emits and `NGAIP-364`, `NGAIP-365`, and `NGAIP-366` implement against.

## Runbook Decision

Use RAGAS-first semantics for RAG quality, with deterministic PrattWise checks retained where backend metadata matters.

Primary semantic RAGAS areas:

- context precision and context recall for retrieval relevance
- faithfulness/grounding for whether the answer is supported by retrieved context
- answer correctness and answer relevancy for response quality

Deterministic PrattWise areas:

- `asset_id` and source identity checks
- citation precision and recall
- hallucinated citation detection
- token-overlap diagnostics for cheap CI and acceptance-criteria compatibility

## Generated Files

`ngaip-415-transfer.py` should generate:

- `app_retrieval/evaluation/config/metrics_spec.yaml`
- `app_retrieval/evaluation/config/eval_report.schema.json`
- `docs/metrics_spec.md`
- `tests/app_retrieval/test_metrics_spec.py`

## Report Schema Ownership

This ticket owns report fields for:

- `eval_version`
- `metrics_spec_version`
- `config`
- `evaluator`
- `testset_provenance`
- `timestamp`
- `results`
- `aggregate_scores`
- `pass_fail_summary`

The schema should include evaluator metadata so RAGAS-backed scores can be reproduced:

- evaluator framework
- provider
- model/deployment
- embeddings deployment
- temperature
- RAGAS version

It should also include generated testset provenance:

- generator name
- candidate testset file
- promoted gold file
- review requirement
- whether KG context was used

## Source and Modality Provenance

Because PrattWise handles PDFs, OCR, tables, and mixed source parts, report rows should preserve:

- `content_type`
- `source_metadata`
- `knowledge_graph_context`

RAGAS evaluates the text/markdown/context representation provided to the model. The metrics contract should allow reports to break out scores by source modality so failures in OCR/table handling are visible.

## Threshold Policy

Keep thresholds draft until calibration on the `NGAIP-362` corpus. `NGAIP-415` should record the target, direction, and sign-off status, but final numeric gates should wait for calibration and Adam/Dave approval.

Response accuracy may carry the existing Jira target, but semantic thresholds for RAGAS metrics should remain reviewable until a representative gold set exists.

## Implementation Dependencies

This ticket depends on:

- `NGAIP-362` for gold data and candidate/gold provenance.
- `NGAIP-363` for harness config and report emission.
- `NGAIP-365` for context metrics.
- `NGAIP-364` for citation metrics.
- `NGAIP-366` for response quality metrics.

## Validation

Run structural checks:

```cmd
uv run python -c "import yaml; yaml.safe_load(open('app_retrieval/evaluation/config/metrics_spec.yaml')); print('YAML OK')"
uv run python -c "import json; json.load(open('app_retrieval/evaluation/config/eval_report.schema.json')); print('JSON OK')"
uv run pytest tests/app_retrieval/test_metrics_spec.py -v
```

These tests validate the contract, not metric correctness. Metric correctness belongs in the implementation tickets.

## Branching and Commit Behavior

The runtime implementation should branch from the shared `ragas-rag-evaluation` parent after `NGAIP-362` and `NGAIP-363` are in place. The transfer script still supports repeatable local use by bootstrapping from local `main-backup-for-mac-claude-repo-04-07-2026`, switching or creating `ngaip-415-metrics-success-criteria`, applying files, and committing locally without pushing.
