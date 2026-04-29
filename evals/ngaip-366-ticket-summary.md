# NGAIP-366 - Implement Response Accuracy Metric

## Ticket Purpose

NGAIP-366 scores generated RAG answer quality against the approved gold set. It covers factual correctness, answer relevancy, completeness, and grounding, with human calibration retained for stakeholder sign-off.

## Runbook Decision

Use RAGAS answer metrics as the automated response-quality path:

- answer correctness
- answer relevancy
- faithfulness

Keep human annotation and calibration because thresholds and judge behavior must be validated against the P&W gold set before results become release gates.

## RAGAS Role

The implementation should adapt harness rows into RAGAS inputs:

- question/user input
- model answer
- reference/gold answer
- retrieved contexts

RAGAS can evaluate whether the answer is semantically correct and grounded in retrieved context. It should run through the shared evaluator config and model factory owned by `NGAIP-363`.

## Human Calibration Role

This ticket should preserve a human review/export path so stakeholders can compare RAGAS scores against human judgment. Human calibration should check:

- whether RAGAS scores align with reviewer labels
- whether answer correctness thresholds are too strict or too permissive
- whether prompt/model changes affect score stability
- whether P&W-specific answer expectations need rubric adjustments

## Expected Files

This ticket should update response metric code, typically under:

- `app_retrieval/evaluation/metrics/response_accuracy.py`
- `tests/app_retrieval/test_response_accuracy.py`

If annotation export is implemented here, it should also produce a reviewer-friendly CSV/JSONL that includes:

- question
- model answer
- gold answer
- retrieved contexts
- RAGAS scores
- evaluator metadata
- human label fields

## Report Requirements

Reports should include:

- response metric scores per question
- aggregate scores
- evaluator framework/provider/model/deployment
- judge temperature
- prompt or rubric version/hash when applicable
- RAGAS version

`NGAIP-415` owns the exact report schema; this ticket must write to that contract.

## Source Modality Handling

For PDFs, tables, OCR, and mixed source parts, RAGAS evaluates the textual/markdown representation included in retrieved context. Response accuracy should not claim visual reasoning correctness unless the source pipeline produced reliable textual context from those visual parts.

Keep `content_type` and source metadata in rows so poor answers can be traced to text, table, OCR, graph, or mixed-source failures.

## Validation

Run CI-safe tests first:

```cmd
uv run pytest tests/app_retrieval/test_response_accuracy.py -v
```

Tests should cover:

- correct answer receives high score from mocked RAGAS path
- irrelevant answer receives low score
- empty context is handled safely
- evaluator metadata is attached to results
- human annotation export includes required fields

Live RAGAS tests should be opt-in and require Azure OpenAI credentials.

## Branching and Commit Behavior

The runtime implementation should branch from `ragas-rag-evaluation` after `NGAIP-362`, `NGAIP-363`, and `NGAIP-415` are available. The transfer script still supports local repeatable use by bootstrapping from local `main-backup-for-mac-claude-repo-04-07-2026`, switching or creating `ngaip-366-response-accuracy-metric`, applying files, and committing locally without pushing.
## RAGAS-Primary Update

`NGAIP-366` should use RAGAS answer correctness, answer/response relevancy, and faithfulness as the primary response accuracy metrics. Human annotation remains a calibration and adjudication path, not the default evaluator.

## Reasoning, Choices, and Code Breakdown

The main design choice is to use RAGAS answer correctness, answer relevancy, and faithfulness as the automated response-quality path, while preserving human calibration for thresholds. Automated judges are useful for repeatability, but stakeholder sign-off is still needed before scores become release gates.

Rejected alternatives:

- Exact-match answer scoring: too brittle for natural-language answers with equivalent phrasing.
- Human review only: high quality but not repeatable enough for regular regression testing.
- RAGAS scores without calibration: risky because judge strictness and domain expectations need to be validated on the approved corpus.

Code/file breakdown:

- `metrics/response_accuracy.py`: thin metric module that delegates answer correctness/relevancy/faithfulness to the shared RAGAS adapter.
- `tests/test_response_accuracy.py`: covers correct, irrelevant, and poorly grounded answers with mocked RAGAS responses.
- Optional annotation export: reviewer-facing rows containing question, model answer, gold answer, contexts, RAGAS scores, and human labels.
- `eval_report.schema.json` from `NGAIP-415`: defines how response scores and evaluator metadata are reported.

This keeps automated response evaluation repeatable while leaving threshold policy and final acceptance criteria to calibrated stakeholder review.

## Runtime Setup and Test Playbook

Run from the backend repository root after `NGAIP-362`, `NGAIP-363`, and `NGAIP-415` have been applied. The transfer script creates or switches to `ngaip-366-response-accuracy-metric` from the local-only base branch.

```cmd
cd C:\path\to\ENCHS-PW-GenAI-Backend
py -3 C:\path\to\rag_eval\evals\ngaip-366-transfer.py
uv sync --group dev
```

Run CI-safe tests first. These should mock RAGAS/model calls and verify answer/reference/context conversion plus report metadata:

```cmd
uv run pytest tests/app_retrieval/test_response_accuracy.py -v
uv run pytest tests/app_retrieval/test_eval_harness.py -v
```

Use the sample golden set for a local harness run once the evaluator and retriever path are available:

```cmd
uv run python manage.py rag_eval run --config app_retrieval/evaluation/config/eval_sample.yaml
```

Live RAGAS answer correctness/relevancy needs evaluator credentials. Human calibration exports, if implemented in this ticket, should be reviewed before any threshold is used as a release gate.

Manual staging must force-add generated tests:

```cmd
git add app_retrieval/evaluation/metrics/response_accuracy.py
git add -f tests/app_retrieval/test_response_accuracy.py
git commit -m "NGAIP-366: Apply transfer script changes"
```
