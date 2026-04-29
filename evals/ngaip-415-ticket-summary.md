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
- LanceDB/vector-store provenance, including table/source metadata where available

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
## RAGAS-Primary Update

`NGAIP-415` success criteria should describe RAGAS metrics as the primary contract for retrieval, citation grounding, and response quality. Deterministic PrattWise checks are retained as supplemental diagnostics for metadata/source integrity and CI triage.

## Reasoning, Choices, and Code Breakdown

The main design choice is to make `NGAIP-415` the contract ticket: it defines metric IDs, report schema, evaluator metadata, provenance, and threshold policy while other tickets implement the calculations. This prevents each metric from inventing its own report format.

Rejected alternatives:

- Hardcoding thresholds inside metric modules: makes calibration and stakeholder approval difficult.
- Leaving report shape implicit: causes downstream consumers and screenshots to drift across tickets.
- RAGAS-only report fields: insufficient because PrattWise deterministic citation/source diagnostics also need a schema.

Code/file breakdown:

- `metrics_spec.yaml`: lists RAGAS-primary metrics, deterministic supplements, target direction, owner ticket, and draft threshold status.
- `eval_report.schema.json`: validates report structure including evaluator metadata, provenance, aggregate scores, per-row results, and pass/fail summary.
- `docs/metrics_spec.md`: human-readable explanation of the metric catalog and success criteria.
- `test_metrics_spec.py`: validates YAML/JSON syntax and contract assumptions.

This ticket is where reviewers should look to understand what “passing RAG evaluation” means, while the actual scoring code remains in the metric/harness tickets.

## Runtime Setup and Test Playbook

Run from the backend repository root after `NGAIP-362` and `NGAIP-363` have established the gold data and harness shape. The transfer script creates or switches to `ngaip-415-metrics-success-criteria` from the local-only base branch.

```cmd
cd C:\path\to\ENCHS-PW-GenAI-Backend
py -3 C:\path\to\rag_eval\evals\ngaip-415-transfer.py
uv sync --group dev
```

Run schema and metrics-spec checks:

```cmd
uv run python -c "import yaml; yaml.safe_load(open('app_retrieval/evaluation/config/metrics_spec.yaml')); print('YAML OK')"
uv run python -c "import json; json.load(open('app_retrieval/evaluation/config/eval_report.schema.json')); print('JSON OK')"
uv run pytest tests/app_retrieval/test_metrics_spec.py -v
```

After `NGAIP-363` can emit a sample report, validate that the report contains the fields owned by this ticket: evaluator metadata, testset provenance, aggregate scores, and pass/fail summary.

Manual staging must force-add generated tests:

```cmd
git add app_retrieval/evaluation/config/metrics_spec.yaml app_retrieval/evaluation/config/eval_report.schema.json docs/metrics_spec.md
git add -f tests/app_retrieval/test_metrics_spec.py
git commit -m "NGAIP-415: Apply transfer script changes"
```

Keep thresholds marked draft until calibrated against approved `NGAIP-362` gold data and stakeholder sign-off. The sample golden set is only for plumbing validation.
