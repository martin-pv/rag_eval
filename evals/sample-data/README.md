# Sample Golden Set

`sample_gold.jsonl` is a 50-row sanitized golden set for local RAG evaluation smoke tests and larger harness dry runs.

It is intentionally generic and does not represent Pratt & Whitney proprietary source material. Use it to verify:

- `GoldRow` schema validation.
- RAGAS dataset conversion.
- Harness/report plumbing with mocked or fixture retrieval.
- Manual RAGAS scoring once a retriever returns matching contexts.

The generated backend location is:

`app_retrieval/evaluation/config/sample_gold.jsonl`

The generated sample config is:

`app_retrieval/evaluation/config/eval_sample.yaml`
