# NGAIP-366 - Implement Response Accuracy Metric

## Ticket

NGAIP-366 scores the quality of generated RAG answers, including factuality, completeness, and grounding. The ticket also keeps a human calibration path with inter-rater reliability expectations for stakeholder sign-off.

## Solution

This worktree adds response-accuracy scoring and annotation export support. Under the updated RAGAS-first decision, automated response scoring should use RAGAS answer correctness, answer relevancy, and faithfulness metrics where available, while the human rubric remains the calibration and sign-off layer.

## Reasoning

Answer quality is too semantic for token overlap or citation metadata alone. RAGAS provides a standard automated judge path, but human calibration remains important because thresholds, evaluator prompts, and model behavior must be validated against the P&W gold set.

## Choices

- Use RAGAS metrics as the automated response-quality path.
- Preserve human annotation exports for dual-rater calibration.
- Keep response accuracy threshold sign-off tied to NGAIP-415 and the NGAIP-362 calibration corpus.
- Record judge/evaluator metadata in report output for reproducibility.
- Keep branch setup inside `ngaip-366-transfer.py` so Windows runtime deployment starts from `main-backup-for-mac-claude-repo-04-07-2026`.
