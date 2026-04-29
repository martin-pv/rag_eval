# NGAIP-364 - Implement Citation Accuracy Metric

## Ticket

NGAIP-364 implements citation and grounding checks for RAG answers. The ticket focuses on whether assistant citations point to valid retrieved/gold sources and whether unsupported source references are reported as hallucinations.

## Solution

This worktree replaces the citation metric stub with deterministic citation precision, citation recall, and hallucination-rate helpers, plus tests for wrong-source and hallucinated-citation behavior. Under the updated RAGAS-first decision, these deterministic checks complement RAGAS faithfulness/grounding rather than replacing it.

## Reasoning

RAGAS can evaluate whether an answer is grounded in the retrieved context, but it does not understand PrattWise-specific citation metadata such as `asset_id`, page/span references, and `ChatResponse.sources`. Citation precision/recall must therefore remain a metadata-aware adapter in Pratt-Backend.

## Choices

- Use RAGAS faithfulness/grounding as the semantic grounding layer.
- Keep `citation_precision`, `citation_recall`, and `hallucination_rate` deterministic for source metadata.
- Define hallucination as cited `asset_id` not present in retrieved sources unless NGAIP-415 changes the rule.
- Include a wrong-page/wrong-source regression test because that is the key acceptance-risk case.
- Keep branch setup inside `ngaip-364-transfer.py` so Windows runtime deployment starts from local `main-backup-for-mac-claude-repo-04-07-2026`.
