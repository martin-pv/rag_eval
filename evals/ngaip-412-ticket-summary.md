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
