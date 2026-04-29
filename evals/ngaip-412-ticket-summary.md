# NGAIP-412 - RAG Evaluation Harness Design POC

## Ticket Purpose

NGAIP-412 is the design spike for the RAG evaluation harness. It proves the basic evaluation shape with synthetic data and documents the architecture that `NGAIP-363` productionizes.

## Runbook Decision

After the RAGAS-first decision, the original overlap scorer from this POC is no longer the main quality metric. It remains useful as:

- a deterministic CI smoke test
- a debugging diagnostic
- a simple baseline for stakeholder explanation
- a reference implementation for how metrics can plug into reports

Production semantic evaluation belongs to RAGAS-backed metric adapters in the later tickets.

## POC Scope

This ticket should stay isolated from production runtime logic. It can include:

- ADR/design notes
- synthetic fixtures
- small proof-of-concept scripts or notebook-style examples
- token overlap scorer tests
- basic report-shape examples

It should not become the long-term harness. `NGAIP-363` owns the production harness.

## Relationship to Later Tickets

The POC informs:

- `NGAIP-362`: gold data shape and fixture needs
- `NGAIP-363`: harness flow, config, runner, and reporting
- `NGAIP-415`: metric/report contract
- `NGAIP-365`: token overlap as a secondary diagnostic
- `NGAIP-364`: source/citation metadata checks
- `NGAIP-366`: answer quality report shape

## RAGAS Context

The main runbook says to use RAGAS for semantic RAG evaluation:

- context relevance
- faithfulness/grounding
- answer correctness
- answer relevancy
- candidate testset generation

`NGAIP-412` should document this architectural pivot so nobody treats the POC overlap scorer as the final production approach.

## Source Modality Note

The POC can use synthetic text fixtures only. Production tickets must handle PrattWise source representations for PDFs, OCR, tables, knowledge graph context, and mixed content. RAGAS evaluates the text/markdown/context provided to the model, not raw visual layout.

## Validation

Run only lightweight tests for the POC:

```cmd
uv run pytest tests/app_retrieval/test_overlap_scorer.py -v
```

These tests prove the diagnostic scorer and report shape. They do not prove production RAGAS behavior.

## Branching and Commit Behavior

The runtime implementation should preserve `NGAIP-412` as a completed design/POC branch. The transfer script still supports local repeatable use by bootstrapping from local `main-backup-for-mac-claude-repo-04-07-2026`, switching or creating the ticket branch, applying files, and committing locally without pushing.

## Reasoning, Choices, and Code Breakdown

The main design choice is to keep `NGAIP-412` as a design POC rather than evolve it into production code. Its overlap scorer and synthetic fixtures are useful for explaining the evaluation shape, but the RAGAS-first decision moved production work into `NGAIP-363` and the later metric tickets.

Rejected alternatives:

- Promoting the POC runner into production: would carry early assumptions forward and duplicate the real harness.
- Deleting the POC entirely: would lose useful architecture notes and baseline examples.
- Treating token overlap as final RAG quality: no longer matches the selected RAGAS-first approach.

Code/file breakdown:

- POC docs/ADR: explain the evaluation architecture and why it changed.
- Synthetic fixtures: demonstrate expected input/output shapes without relying on production data.
- Overlap scorer: retained only as a deterministic diagnostic and teaching baseline.
- POC tests: verify the overlap scorer/report shape, not production RAGAS behavior.

This ticket should help reviewers understand the evolution of the design, while `NGAIP-363` remains the implementation target.

## Runtime Setup and Test Playbook

Run from the backend repository root only when preserving or replaying the design POC. This ticket is not the production RAGAS harness; `NGAIP-363` owns that.

```cmd
cd C:\path\to\ENCHS-PW-GenAI-Backend
py -3 C:\path\to\rag_eval\evals\ngaip-412-transfer.py
uv sync --group dev
```

Run lightweight POC tests only:

```cmd
uv run pytest tests/app_retrieval/test_overlap_scorer.py -v
```

If the POC emits report examples, compare their shape to the `NGAIP-415` schema, but do not use overlap scores as production RAG quality gates.

Manual staging must force-add generated tests if they are under `tests/`:

```cmd
git add docs app_retrieval/evaluation
git add -f tests/app_retrieval/test_overlap_scorer.py
git commit -m "NGAIP-412: Apply transfer script changes"
```
