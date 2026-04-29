# NGAIP-412 - RAG Evaluation Harness Design POC

## Ticket

NGAIP-412 is the design spike for the RAG evaluation harness. It proves the basic evaluation flow with synthetic data and documents the architecture that NGAIP-363 productionizes.

## Solution

This worktree adds the ADR, a small notebook-style proof of concept, and overlap-scorer tests. The POC is intentionally limited: it demonstrates data flow and testing shape, while production harness logic belongs in NGAIP-363 and metric implementations belong in NGAIP-364, NGAIP-365, and NGAIP-366.

## Reasoning

The spike reduces risk before building the full harness. It gives the team a concrete flow to discuss: gold data, retriever output, metrics, and reports. After the 2026-04-28 decision, the overlap scorer is treated as a diagnostic/CI helper rather than the primary RAG evaluation strategy.

## Choices

- Keep the POC isolated from production code.
- Document design decisions in `docs/rag_eval_adr.md`.
- Use synthetic data so the POC can run without controlled corpus access.
- Carry forward only the useful testing/reporting patterns into NGAIP-363.
- Keep branch setup inside `ngaip-412-transfer.py` so Windows runtime deployment starts from local `main-backup-for-mac-claude-repo-04-07-2026`.
