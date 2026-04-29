# RAGAS Implementation Runbook for NGAIP RAG Evaluation

## Purpose

This runbook describes how to implement the NGAIP RAG evaluation tickets on the actual runtime computer using a RAGAS-first approach.

The intended branch model is:

- One parent integration branch for the whole RAGAS evaluation effort.
- One sub-branch per NGAIP ticket.
- Each ticket branch should be created locally from the RAGAS parent branch, not directly from `main`, after the parent branch has been created from the local backend backup branch.

The transfer scripts in this repository are still useful as repeatable generators, but the actual runtime machine should use Git branches and commits to preserve each ticket as reviewable work.

## High-Level Decision

Use the `ragas` library as the primary evaluator framework for semantic RAG quality:

- Context relevance should use RAGAS context metrics.
- Grounding should use RAGAS faithfulness/grounding metrics.
- Response quality should use RAGAS answer correctness and answer relevancy metrics.

Keep deterministic PrattWise-specific checks where RAGAS does not know enough about backend metadata:

- Gold dataset schema validation.
- Source `asset_id` matching.
- Citation precision and recall.
- Hallucinated citation detection.
- Token-overlap diagnostics for cheap CI smoke tests and original acceptance-criteria compatibility.

## Why RAGAS

RAGAS is better than pure token overlap for this program because the RAG answers and retrieved contexts can be semantically correct without sharing exact words. The evaluation needs to answer questions like "did the retrieved context support the reference answer?" and "is this generated answer grounded?" Those are semantic judgments, and RAGAS provides standard metrics for them.

RAGAS does not replace every backend-specific check. PrattWise still needs deterministic validation for metadata and source linkage because RAGAS does not understand PrattWise `asset_id`, page/span references, folder ids, `ChatResponse.sources`, or internal citation structures unless we adapt those fields into its input format.

## Branch Strategy

### Parent Branch

Create one parent branch for all RAGAS evaluation work:

```cmd
cd path\to\Pratt-Backend\backend
git switch main-backup-for-mac-claude-repo-04-07-2026
git switch -c ragas-rag-evaluation
```

This branch should contain shared setup that every ticket needs:

- Dependency setup for `ragas`, `datasets`, `pytest`, `pytest-django`, and `pytest-asyncio`.
- Shared evaluation package directories.
- Shared RAGAS adapter utilities.
- Shared report metadata fields.
- Shared test fixtures.

Commit the parent setup locally:

```cmd
git add pyproject.toml uv.lock requirements.txt pytest.ini app_retrieval tests
git commit -m "NGAIP: Add RAGAS evaluation foundation"
```

Do not publish unless the team explicitly wants this branch on GitHub.

### Ticket Branches

Create sub-branches from the parent branch:

```cmd
git switch ragas-rag-evaluation
git switch -c ngaip-362-corpus-gold-dataset
```

After finishing a ticket:

```cmd
git add app_retrieval tests
git commit -m "NGAIP-362: Add gold dataset schema and fixtures"
git switch ragas-rag-evaluation
git merge --no-ff ngaip-362-corpus-gold-dataset
```

Repeat for:

- `ngaip-363-rag-evaluation-harness`
- `ngaip-415-metrics-success-criteria`
- `ngaip-365-context-relevancy-metric`
- `ngaip-364-citation-accuracy-metric`
- `ngaip-366-response-accuracy-metric`

Recommended implementation order:

1. `NGAIP-362`
2. `NGAIP-363`
3. `NGAIP-415`
4. `NGAIP-365`
5. `NGAIP-364`
6. `NGAIP-366`

The order matters because 362 provides the gold data contract, 363 provides the harness, 415 defines the metric/report contract, and the metric tickets plug into that foundation.

## Dependency Setup

The backend uses `uv sync`, so dependencies should be declared in `pyproject.toml` and locked through `uv`, not installed only into the current environment.

From the backend project directory:

```cmd
cd path\to\Pratt-Backend\backend
uv add ragas datasets
uv add --dev pytest pytest-django pytest-asyncio
uv sync --group dev
```

If the runtime machine needs pinned versions, start with:

```cmd
uv add ragas>=0.2.0 datasets>=2.14.0
uv add --dev pytest==8.3.3 pytest-django==4.9.0 pytest-asyncio==0.23.8
uv sync --group dev
```

Validate that Django pytest setup works:

```cmd
uv run pytest --version
uv run pytest tests/app_retrieval -v
```

The backend already has `pytest.ini` with:

```ini
[pytest]
DJANGO_SETTINGS_MODULE = app.settings
```

Normal Django tests do not require `python manage.py runserver`. Start the server only for true HTTP end-to-end tests that call `localhost`.

## RAGAS Configuration

Add an evaluator section to the RAG evaluation config so live model calls are explicit and reproducible:

```yaml
evaluator:
  framework: ragas
  enabled: false
  provider: azure_openai
  model: ${AZURE_OPENAI_EVAL_DEPLOYMENT}
  embeddings: ${AZURE_OPENAI_EMBEDDING_DEPLOYMENT}
  temperature: 0
  timeout_seconds: 120
  max_retries: 2
```

Recommended behavior:

- `enabled: false` for default CI and local structural tests.
- `enabled: true` only when credentials and evaluator deployment are available.
- Record evaluator metadata in every `report.json`.

Report metadata should include:

```json
{
  "metrics_spec_version": "ngaip-415-ragas-v1",
  "evaluator": {
    "framework": "ragas",
    "provider": "azure_openai",
    "model": "deployment-name",
    "temperature": 0
  }
}
```

## Can RAGAS Evaluations Run as Django Tests?

Yes, but split them into two categories.

### Structural Django Tests

These should always run in CI:

- Gold schema validation.
- Config parsing.
- RAGAS adapter input shaping.
- Report JSON/CSV field output.
- Token-overlap diagnostic behavior.
- Citation metadata calculations.

These tests should not call a live LLM.

Example:

```cmd
uv run pytest tests/app_retrieval -v
```

### Live RAGAS Smoke Tests

These can run as Django tests, but should be gated by config or environment variables:

```cmd
set RUN_RAGAS_LIVE=1
set AZURE_OPENAI_EVAL_DEPLOYMENT=...
set AZURE_OPENAI_API_KEY=...
uv run pytest tests/app_retrieval/test_ragas_live.py -v
```

Use `pytest.mark.skipif` so these tests skip when credentials are missing.

Recommended rule:

- CI should prove the harness and adapters are correct without secrets.
- A manual or scheduled smoke run should prove live RAGAS scoring works against a small approved gold dataset.

## Script Generation Requirements

Each transfer script should:

- Check the current branch with `git branch --show-current`.
- Continue if already on the expected ticket branch.
- Switch to the expected ticket branch if it already exists locally.
- Create the expected branch from the configured base branch if it does not exist.
- Write or update only files owned by that ticket.
- Stage only files written or touched by that script.
- Create a local commit with a ticket-specific message.
- Never run `git push`, `git fetch`, or `git pull`.

Commit messages should be explicit:

- `NGAIP-362: Add gold dataset schema and fixtures`
- `NGAIP-363: Add RAG evaluation harness`
- `NGAIP-415: Add RAGAS metrics contract`
- `NGAIP-365: Add RAGAS context relevancy metrics`
- `NGAIP-364: Add citation and grounding metrics`
- `NGAIP-366: Add RAGAS response accuracy metrics`

If generating scripts from the `rag_eval` repository, copy the relevant `evals/ngaip-*-transfer.py` script to the runtime backend root, run it from that root, inspect the diff, then keep or amend the generated local commit.

## Ticket Checklist

### NGAIP-362: Gold Corpus and Dataset

Goal: define the reference data that RAGAS and deterministic metrics will consume.

Implementation checklist:

- Add `app_retrieval/evaluation/config/gold_schema.py`.
- Add `app_retrieval/evaluation/config/gold_schema.md`.
- Add redacted CI fixture such as `ci_gold.jsonl`.
- Add `app_retrieval/evaluation/gold_loader.py`.
- Add tests for valid rows, missing fields, invalid JSON, extra fields, and optional spans/chunk ids.

Use Pydantic here.

Justification:

- `NGAIP-362` is not an evaluator metric ticket; it is a data-contract ticket.
- Pydantic is appropriate for validating gold rows before they are passed into RAGAS.
- The backend already includes `pydantic==2.9.2` in `requirements.txt` and uses Pydantic in existing backend code.
- RAGAS still needs clean structured input, and Pydantic helps guarantee that input.

RAGAS relationship:

- Do not replace the 362 schema with RAGAS.
- Convert validated `GoldRow` objects into RAGAS dataset rows later in the harness.
- Required RAGAS fields usually include question/user input, retrieved contexts, generated answer, and reference/ground-truth answer.

Done when:

- Gold fixture loads successfully.
- Invalid rows fail with useful errors.
- Tests run under Django/pytest without live RAGAS credentials.

### NGAIP-363: RAG Evaluation Harness

Goal: create the reusable Django-native harness that loads gold data, runs retrievers, invokes metrics, and writes reports.

Implementation checklist:

- Add `app_retrieval/evaluation/` package.
- Add config loader.
- Add Django management command, for example `python manage.py rag_eval run --config ...`.
- Add retriever adapters for semantic, keyword, and hybrid modes.
- Add metric registry.
- Add JSON and CSV reporters.
- Add RAGAS adapter helpers that map PrattWise data into RAGAS inputs.
- Add tests for config loading, command wiring, fake retriever flow, metric registry, and report output.

RAGAS-specific requirements:

- Add `ragas` and `datasets` dependencies.
- Create an adapter layer rather than scattering RAGAS calls through each command.
- Keep live RAGAS calls disabled unless config says they are enabled.

Done when:

- A redacted fixture can run end-to-end through the harness with fake/deterministic metrics.
- Reports include placeholders or real fields compatible with 415.
- RAGAS dependencies are installed and importable.

### NGAIP-415: Metrics and Success Criteria

Goal: define the metric contract used by all reports and ticket implementations.

Implementation checklist:

- Add `metrics_spec.yaml`.
- Add `eval_report.schema.json`.
- Add a human-readable metrics document.
- Include RAGAS metric ids and deterministic adapter ids.
- Include `metrics_spec_version`.
- Include evaluator metadata requirements.
- Add tests that validate required metric ids and report schema structure.

Recommended metric ids:

- `ragas_context_precision`
- `ragas_context_recall`
- `ragas_faithfulness`
- `ragas_answer_correctness`
- `ragas_answer_relevancy`
- `citation_precision`
- `citation_recall`
- `hallucination_rate`
- `token_overlap_at_k`

Justification:

- RAGAS metrics should be the primary semantic metrics.
- Deterministic metrics should remain for metadata and cheap CI.
- Thresholds should be calibrated on the 362 gold corpus before final sign-off.

Done when:

- Reports can declare the metric spec version.
- Every metric ticket knows which field names to output.
- Schema tests fail if report contracts drift.

### NGAIP-365: Context Relevancy

Goal: measure whether retrieved contexts are useful for answering each gold question.

Implementation checklist:

- Replace the 363 context metric stub.
- Implement RAGAS context precision and context recall through the shared adapter.
- Keep token overlap as a diagnostic metric.
- Record evaluator metadata in `report.json`.
- Add unit tests for adapter input shape and deterministic token overlap.
- Add a gated live RAGAS smoke test if credentials are available.

RAGAS behavior:

- Use retrieved chunks as `contexts`.
- Use gold answer or reference answer as the reference.
- Use generated answer where required by the selected RAGAS metric.

Justification:

- Context relevance is semantic, so token overlap should not be the primary score.
- Token overlap stays useful for CI and for explaining retrieval misses.

Done when:

- Report output includes RAGAS context fields.
- Structural tests pass without credentials.
- Live smoke test can run when enabled.

### NGAIP-364: Citation Accuracy and Grounding

Goal: measure whether citations and grounding are correct.

Implementation checklist:

- Replace the 363 citation metric stub.
- Add deterministic citation precision and recall.
- Add hallucinated citation detection.
- Add RAGAS faithfulness/grounding as the semantic grounding metric.
- Add tests for correct source, wrong source, missing citation, and hallucinated citation.

RAGAS behavior:

- Use RAGAS faithfulness to check whether the answer is supported by retrieved contexts.
- Do not rely on RAGAS for PrattWise source metadata validation.

Justification:

- RAGAS can judge semantic grounding.
- PrattWise code must still validate `asset_id`, source references, and citation metadata.

Done when:

- Reports include both semantic grounding and deterministic citation metadata fields.
- Wrong-source citations fail deterministic tests.

### NGAIP-366: Response Accuracy

Goal: measure answer quality against the gold answer.

Implementation checklist:

- Replace the 363 response metric stub.
- Implement RAGAS answer correctness.
- Implement RAGAS answer relevancy if supported by the installed version.
- Include RAGAS faithfulness where useful for answer grounding.
- Keep human annotation export for calibration.
- Add structural tests for adapter inputs and report outputs.
- Add gated live smoke tests for evaluator scoring.

Justification:

- Response accuracy is semantic and should use RAGAS as the automated evaluator path.
- Human calibration remains necessary for threshold sign-off and stakeholder confidence.

Done when:

- Reports include response quality RAGAS scores.
- Annotation export remains available.
- Live scoring can be run manually with credentials.

## RAGAS Adapter Shape

Keep one adapter layer responsible for converting PrattWise evaluation rows into RAGAS-compatible examples.

The adapter should accept:

- `question`
- `answer`
- `ground_truth` or `reference`
- `contexts`
- optional source metadata for deterministic checks

The adapter should produce the input format required by the installed RAGAS version. RAGAS APIs change between versions, so isolate imports and API calls in one file, for example:

```text
app_retrieval/evaluation/ragas_adapter.py
```

Benefits:

- Easier upgrades when RAGAS changes metric names or signatures.
- Easier unit testing without live model calls.
- Cleaner separation between PrattWise retrieval objects and evaluator library inputs.

## Django Test Plan

Default test command:

```cmd
uv run pytest tests/app_retrieval -v
```

Suggested test groups:

- `test_gold_loader.py`: no RAGAS calls.
- `test_eval_config.py`: no RAGAS calls.
- `test_ragas_adapter.py`: no live LLM; verify input mapping.
- `test_metric_context_relevancy.py`: deterministic plus mocked RAGAS.
- `test_metric_citation_accuracy.py`: deterministic plus mocked RAGAS faithfulness.
- `test_metric_response_accuracy.py`: mocked RAGAS scoring.
- `test_ragas_live.py`: skipped unless `RUN_RAGAS_LIVE=1`.

Example skip policy:

```python
import os
import pytest

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_RAGAS_LIVE") != "1",
    reason="Live RAGAS evaluation requires credentials",
)
```

## Report Checklist

Every report should include:

- Run id.
- Timestamp.
- Git branch and commit if available.
- Config path.
- Gold dataset path or dataset id.
- Retriever mode.
- `metrics_spec_version`.
- RAGAS evaluator provider/model/deployment.
- Per-question scores.
- Aggregate scores.
- Any skipped metrics with reason.

Every per-question score should include fields from 415, even if some are `null` or skipped because live evaluation was disabled.

## Final Implementation Checklist

- Create `ragas-rag-evaluation` from `main-backup-for-mac-claude-repo-04-07-2026`.
- Add dependencies through `uv add`, then run `uv sync --group dev`.
- Confirm `uv run pytest --version`.
- Implement 362 data contract with Pydantic validation.
- Implement 363 harness and RAGAS adapter layer.
- Implement 415 metric/report contract.
- Implement 365 RAGAS context metrics and token-overlap diagnostic.
- Implement 364 RAGAS faithfulness plus deterministic citation metadata checks.
- Implement 366 RAGAS answer metrics plus human annotation export.
- Add Django tests for structural behavior.
- Add gated live RAGAS smoke tests.
- Generate `report.json` and `report.csv`.
- Confirm reports include evaluator metadata.
- Keep ticket commits local unless publishing is explicitly approved.

## Answer to the Pydantic Question for NGAIP-362

Yes, using Pydantic for `NGAIP-362` is reasonable.

`NGAIP-362` defines and validates the gold dataset. That is a schema/data-contract problem, not a metric-evaluation problem. RAGAS should consume the validated dataset later, but RAGAS should not be used as the schema validator.

The backend already has Pydantic in `requirements.txt`, and some backend code already imports Pydantic. The repo is mostly Django models for persisted database objects, but Pydantic is appropriate for non-persisted structured inputs such as JSONL evaluation rows.

Recommended split:

- Pydantic validates `GoldRow`.
- The harness converts `GoldRow` into RAGAS examples.
- RAGAS scores context relevance, faithfulness, answer correctness, and answer relevancy.
- Deterministic PrattWise code scores source metadata and cheap diagnostics.
