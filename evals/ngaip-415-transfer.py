"""ngaip-415-transfer.py — cross-platform transfer script (Windows/macOS/Linux).
Run from repo root: python ngaip-415-transfer.py

Produces 4 files (no Python source code — YAML, JSON schema, Markdown, pytest):
  ENCHS-PW-GenAI-Backend/app_retrieval/evaluation/config/metrics_spec.yaml
  ENCHS-PW-GenAI-Backend/app_retrieval/evaluation/config/eval_report.schema.json
  ENCHS-PW-GenAI-Backend/docs/metrics_spec.md
  ENCHS-PW-GenAI-Backend/tests/app_retrieval/test_metrics_spec.py

Safe to run twice — all writes overwrite cleanly.
"""
import ast
import json
import subprocess
from pathlib import Path

BRANCH = "ngaip-415-metrics-success-criteria"
COMMIT_MESSAGE = "NGAIP-415: Apply transfer script changes"
BASE_BRANCH = "main"
BACKEND = Path.cwd()


def git(*args):
    subprocess.run(["git", *args], check=True)


def git_or(*args):
    return subprocess.run(["git", *args], check=False).returncode == 0


def current_branch() -> str:
    return subprocess.check_output(
        ["git", "branch", "--show-current"],
        text=True,
    ).strip()


def ensure_ticket_branch() -> None:
    """Ensure this transfer runs on its local ticket branch; never push/publish."""
    print(f"[415-transfer] Preparing branch: {BRANCH} from local {BASE_BRANCH}")
    if current_branch() == BRANCH:
        print(f"[415-transfer] Already on ticket branch: {BRANCH}")
        return
    if git_or("rev-parse", "--verify", f"refs/heads/{BRANCH}"):
        git("switch", BRANCH)
        return
    git("switch", BASE_BRANCH)
    git("switch", "-c", BRANCH)

# ---------------------------------------------------------------------------
# Local commit helper (no push/publish)
# ---------------------------------------------------------------------------

def _path_from_join_expr(node: ast.AST) -> str | None:
    parts: list[str] = []
    cur = node
    while isinstance(cur, ast.BinOp) and isinstance(cur.op, ast.Div):
        right = cur.right
        if isinstance(right, ast.Constant) and isinstance(right.value, str):
            parts.append(right.value)
        else:
            return None
        cur = cur.left
    if isinstance(cur, ast.Name) and cur.id in {"BACKEND", "ROOT"}:
        return "/".join(reversed(parts))
    return None


def _transfer_paths_from_this_script() -> list[str]:
    tree = ast.parse(Path(__file__).read_text(encoding="utf-8"), filename=__file__)
    targets: set[str] = set()
    assigned_paths: dict[str, str] = {}
    writer_calls = {"ensure", "touch", "append_if_missing", "patch"}

    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        path = _path_from_join_expr(node.value)
        if not path:
            continue
        for target in node.targets:
            if isinstance(target, ast.Name):
                assigned_paths[target.id] = path.replace("\\", "/")

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name) and node.args and func.id in writer_calls:
            first_arg = node.args[0]
            if isinstance(first_arg, ast.Name):
                path = assigned_paths.get(first_arg.id)
            else:
                path = _path_from_join_expr(first_arg)
            if path:
                targets.add(path.replace("\\", "/"))
        elif isinstance(func, ast.Attribute) and func.attr == "write_text":
            receiver = func.value
            if isinstance(receiver, ast.Name):
                path = assigned_paths.get(receiver.id)
            else:
                path = _path_from_join_expr(receiver)
            if path:
                targets.add(path.replace("\\", "/"))

    return sorted(targets)


def commit_transfer_changes() -> None:
    repo_root = globals().get("BACKEND", globals().get("ROOT", Path.cwd()))
    paths = _transfer_paths_from_this_script()
    if not paths:
        print("[transfer] No generated paths found to commit.")
        return

    existing_paths = [p for p in paths if (repo_root / p).exists()]
    if not existing_paths:
        print("[transfer] No generated files exist to commit.")
        return

    print(f"[transfer] Staging {len(existing_paths)} generated file(s) for local commit...")
    git("add", "--", *existing_paths)
    staged = subprocess.run(
        ["git", "diff", "--cached", "--quiet", "--", *existing_paths],
        cwd=repo_root,
        check=False,
    )
    if staged.returncode == 0:
        print("[transfer] No changes to commit.")
        return
    git("commit", "-m", COMMIT_MESSAGE, "--", *existing_paths)
    print(f"[transfer] Created local commit: {COMMIT_MESSAGE}")

def ensure(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def touch(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch()


# ---------------------------------------------------------------------------
# Branch setup
# ---------------------------------------------------------------------------
ensure_ticket_branch()

# ---------------------------------------------------------------------------
# Directories and __init__ files
# ---------------------------------------------------------------------------
print("[NGAIP-415] Creating directories...")
touch(BACKEND / "tests" / "__init__.py")
touch(BACKEND / "tests" / "app_retrieval" / "__init__.py")

# ---------------------------------------------------------------------------
# metrics_spec.yaml
# ---------------------------------------------------------------------------
METRICS_SPEC_YAML = """\
# metrics_spec.yaml — NGAIP-415
# RAG Evaluation: Metrics and Success Criteria
#
# Status: DRAFT — thresholds TBD pending NGAIP-362 calibration corpus
# Sign-off required: Adam Thomas + Dave Ferguson before blocking 364/365/366
# Never hardcode threshold values from this file in Python — read at runtime.

version: "1.0-draft"
spec_status: DRAFT
owner_ticket: NGAIP-415
calibration_corpus: "NGAIP-362 (pending — thresholds will be updated post-calibration)"

top_k_sweep:
  values: [1, 3, 5]
  seed: 42
  note: "Same seed applied across all K values for comparability. Each K run is independent."

# ---------------------------------------------------------------------------
# Metric definitions
# ---------------------------------------------------------------------------
# Fields per entry:
#   id              unique snake_case identifier (referenced by harness and metric modules)
#   display_name    human-readable label
#   category        retrieval | citation | generation | operational
#   definition      plain-language description
#   formula         pseudocode / mathematical expression
#   parameters      per-metric knobs (tau, k, etc.)
#   threshold       pass/fail criteria — all TBD until NGAIP-362 calibration
#   measurement     automatic | human | "automatic + human calibration"
#   owner_ticket    the implementation story responsible for this metric
# ---------------------------------------------------------------------------

metrics:

  # -------------------------------------------------------------------------
  # RETRIEVAL METRICS  (owner: NGAIP-365)
  # -------------------------------------------------------------------------

  - id: retrieval_precision_at_k
    display_name: "Retrieval Precision@K"
    category: retrieval
    definition: >
      Fraction of the top-K retrieved chunks that overlap a gold span above the
      RAGAS context precision score for whether retrieved chunks are useful for answering the question. Token overlap is retained only as a CI diagnostic.
    formula: >
      precision@k = |{ c in retrieved[:k] : token_overlap(c.context, gold_spans) > tau }| / k
    parameters:
      k: [1, 3, 5]
      tau: "TBD — token overlap threshold, calibrated on NGAIP-362 pilot rows"
    threshold:
      pass: "TBD"
      fail: "TBD"
      direction: higher_is_better
    measurement: "RAGAS primary + deterministic diagnostic"
    owner_ticket: NGAIP-365

  - id: retrieval_recall_at_k
    display_name: "Retrieval Recall@K"
    category: retrieval
    definition: >
      Fraction of gold spans that are covered by at least one of the top-K retrieved
      RAGAS context recall score for whether the retrieved context covers the reference answer. Token overlap is retained only as a CI diagnostic.
    formula: >
      recall@k = |{ s in gold_spans : any(token_overlap(c.context, s) > tau for c in retrieved[:k]) }|
                 / |gold_spans|
    parameters:
      k: [1, 3, 5]
      tau: "TBD"
    threshold:
      pass: "TBD"
      fail: "TBD"
      direction: higher_is_better
    measurement: "RAGAS primary + deterministic diagnostic"
    owner_ticket: NGAIP-365

  - id: context_relevancy_at_k
    display_name: "Context Relevancy@K"
    category: retrieval
    definition: >
      RAGAS context relevancy/precision score over the retrieved context supplied to the answer. Diagnostic token overlap may also be reported for CI triage:
      top-K retrieved chunk tokens. Chosen formula: token overlap (not character IoU) —
      resolved in NGAIP-415 to match the POC implementation in NGAIP-412.
    formula: >
      context_relevancy@k =
        |tokens(union(c.context for c in retrieved[:k])) ∩ tokens(join(gold_spans))|
        / |tokens(join(gold_spans))|
      where tokens(text) = set(text.lower().split())
    parameters:
      k: [1, 3, 5]
    threshold:
      pass: "TBD"
      fail: "TBD"
      direction: higher_is_better
    measurement: "RAGAS primary + deterministic diagnostic"
    owner_ticket: NGAIP-365

  - id: hit_rate_at_k
    display_name: "Hit Rate@K"
    category: retrieval
    definition: >
      Binary per-question score: 1 if at least one top-K chunk overlaps a gold span
      above tau, else 0. Averaged across all evaluation questions. Maps directly to
      the "hit-rate" KPI in the Jira acceptance criteria.
    formula: >
      hit_rate@k = mean([
        1 if any(token_overlap(c.context, gold_spans) > tau for c in retrieved[:k]) else 0
        for q in questions
      ])
    parameters:
      k: [1, 3, 5]
      tau: "TBD"
    threshold:
      pass: "TBD"
      fail: "TBD"
      direction: higher_is_better
    measurement: "RAGAS primary + deterministic diagnostic"
    owner_ticket: NGAIP-365

  # -------------------------------------------------------------------------
  # CITATION METRICS  (owner: NGAIP-364)
  # -------------------------------------------------------------------------

  - id: citation_precision
    display_name: "Citation Precision"
    category: citation
    definition: >
      Fraction of model-generated citations whose asset_id + text span overlaps a
      gold citation span above the character-overlap threshold tau. Measures whether
      the model cites the right source at the right location.
    formula: >
      citation_precision =
        |{ c in model_citations : any(char_overlap(c.span, g.span) > tau for g in gold_citations) }|
        / |model_citations|
    parameters:
      tau: "TBD — character overlap threshold on citation spans"
      span_fields: ["asset_id", "citation_index", "source_type"]
    threshold:
      pass: "TBD"
      fail: "TBD"
      direction: higher_is_better
    measurement: "RAGAS faithfulness primary + deterministic citation diagnostic"
    owner_ticket: NGAIP-364
    notes: >
      Citation shape from ChatResponse.sources — align parser with asset_id,
      citation_index, source_type conventions in app_chatbot/models.py.
      Score only assistant-role citations; exclude user-attachment sources.

  - id: citation_recall
    display_name: "Citation Recall"
    category: citation
    definition: >
      Fraction of gold citations that are recovered by at least one model citation
      at sufficient span overlap. Measures how many required sources the model cited.
    formula: >
      citation_recall =
        |{ g in gold_citations : any(char_overlap(c.span, g.span) > tau for c in model_citations) }|
        / |gold_citations|
    parameters:
      tau: "TBD"
    threshold:
      pass: "TBD"
      fail: "TBD"
      direction: higher_is_better
    measurement: "RAGAS faithfulness primary + deterministic citation diagnostic"
    owner_ticket: NGAIP-364

  - id: hallucination_rate
    display_name: "Hallucination Rate"
    category: citation
    definition: >
      Fraction of model citations where the cited asset_id was NOT present in the
      retrieved set for that query. A citation is hallucinated when the model
      references a source it never retrieved.
    formula: >
      hallucination_rate =
        |{ c in model_citations : c.asset_id not in { r.asset_id for r in retrieved_set } }|
        / |model_citations|
    parameters:
      note: >
        TBD — confirm with Adam + Dave whether gold membership is also required
        (strict AND: not-in-retrieved AND not-in-gold) vs. simpler OR condition.
        Current definition uses not-in-retrieved only (permissive, easier to automate).
    threshold:
      pass: "TBD"
      fail: "TBD"
      direction: lower_is_better
    measurement: "RAGAS faithfulness primary + deterministic citation diagnostic"
    owner_ticket: NGAIP-364

  # -------------------------------------------------------------------------
  # GENERATION / RESPONSE QUALITY METRICS  (owner: NGAIP-366)
  # -------------------------------------------------------------------------

  - id: response_accuracy
    display_name: "Response Accuracy"
    category: generation
    definition: >
      LLM-as-judge composite score (0.0–1.0): mean of three binary/partial subscores —
      factuality (claims are true), completeness (covers gold answer), grounding
      (claims traceable to retrieved context). Maps to "grounded answer percentage" KPI.
    formula: >
      response_accuracy = (factuality + completeness + grounding) / 3
      where each subscore: 0 = fail, 0.5 = partial, 1 = pass
    judge:
      model: "Same Azure OpenAI deployment as production"
      temperature: 0.0
      prompt_version: "v1 — TBD, prompt hash stored in report.json per run"
    threshold:
      pass: ">= 0.70  (NGAIP-366 baseline target)"
      fail: "< 0.70"
      inter_rater_reliability_kappa: ">= 0.70 (Cohen's kappa, human calibration N >= 30)"
      direction: higher_is_better
    measurement: "RAGAS answer correctness/relevancy primary + human calibration"
    owner_ticket: NGAIP-366

  - id: faithfulness
    display_name: "Faithfulness / Grounding"
    category: generation
    definition: >
      Fraction of factual claims in the model answer that can be traced to at least
      one retrieved chunk. Sub-dimension of response_accuracy (grounding subscore).
    formula: >
      faithfulness =
        |{ claim in answer : grounded(claim, retrieved_chunks) }| / |claims(answer)|
      where grounded() is determined by the LLM-as-judge grounding subscore.
    threshold:
      pass: "TBD"
      fail: "TBD"
      direction: higher_is_better
    measurement: "RAGAS faithfulness primary"
    owner_ticket: NGAIP-366

  # -------------------------------------------------------------------------
  # OPERATIONAL / INFRASTRUCTURE METRICS  (owner: NGAIP-363)
  # -------------------------------------------------------------------------

  - id: freshness_days
    display_name: "Source Freshness (days)"
    category: operational
    definition: >
      Mean age in days of source documents cited in the model answer, measured from
      the document's last_modified_date to the eval run date. Lower is fresher.
    formula: >
      freshness_days = mean([
        (eval_run_date - asset.last_modified_date).days
        for asset in cited_assets
      ])
    threshold:
      pass: "TBD"
      fail: "TBD"
      direction: lower_is_better
    measurement: automatic
    owner_ticket: NGAIP-363

  - id: latency_p95_ms
    display_name: "Latency P95 (ms)"
    category: operational
    definition: >
      95th-percentile end-to-end wall-clock latency in milliseconds: from query
      submission to final token received. For streaming responses, final token = last
      chunk. Captures worst-case user-visible wait time.
    formula: >
      latency_p95_ms = percentile(end_to_end_latencies_ms, 95)
    threshold:
      pass: "TBD"
      fail: "TBD"
      direction: lower_is_better
    measurement: automatic
    owner_ticket: NGAIP-363

  - id: latency_ttfc_ms
    display_name: "Time-to-First-Chunk P95 (ms)"
    category: operational
    definition: >
      95th-percentile latency from query submission to first streamed chunk received.
      Secondary latency metric for streaming responses; lower is better.
    formula: >
      latency_ttfc_ms = percentile(ttfc_latencies_ms, 95)
    parameters:
      note: "Streaming responses only. Non-streaming queries produce no ttfc value."
    threshold:
      pass: "TBD"
      fail: "TBD"
      direction: lower_is_better
    measurement: automatic
    owner_ticket: NGAIP-363

  - id: cost_per_query_usd
    display_name: "Cost per Query (USD)"
    category: operational
    definition: >
      Total Azure OpenAI spend per query: sum of input token cost, output token cost,
      embedding token cost, and rerank operation cost. All components included.
    formula: >
      cost_per_query_usd =
        (input_tokens  * price_per_input_token)
        + (output_tokens * price_per_output_token)
        + (embed_tokens  * price_per_embed_token)
        + (rerank_calls  * price_per_rerank_call)
    parameters:
      pricing_source: "Azure OpenAI portal — update prices in harness config before each eval run"
    threshold:
      pass: "TBD"
      fail: "TBD"
      direction: lower_is_better
    measurement: automatic
    owner_ticket: NGAIP-363
"""

ensure(
    BACKEND / "app_retrieval" / "evaluation" / "config" / "metrics_spec.yaml",
    METRICS_SPEC_YAML,
)
print("[NGAIP-415] Created: app_retrieval/evaluation/config/metrics_spec.yaml")

# ---------------------------------------------------------------------------
# eval_report.schema.json — built as a dict and serialized via json.dumps
# ---------------------------------------------------------------------------
print("[NGAIP-415] Writing eval_report.schema.json...")

schema = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "$id": "eval_report.schema.json",
    "title": "RAG Eval Report",
    "description": (
        "Schema for report.json produced by the NGAIP-363 harness. "
        "Versioned here (NGAIP-415) so metric owners can depend on a stable contract."
    ),
    "type": "object",
    "required": [
        "eval_version",
        "metrics_spec_version",
        "config",
        "timestamp",
        "results",
        "aggregate_scores",
    ],
    "additionalProperties": False,
    "properties": {
        "eval_version": {
            "type": "string",
            "description": "Harness version string (semver). Set by NGAIP-363.",
        },
        "metrics_spec_version": {
            "type": "string",
            "description": (
                "Version from metrics_spec.yaml used during this run. "
                "Must match the checked-in spec version."
            ),
        },
        "evaluator": {
            "type": "object",
            "description": "RAGAS evaluator metadata used for this run.",
            "properties": {
                "framework": {"type": "string"},
                "provider": {"type": "string"},
                "model": {"type": "string"},
                "embeddings": {"type": "string"},
                "temperature": {"type": "number"},
                "ragas_version": {"type": "string"},
            },
            "additionalProperties": True,
        },
        "testset_provenance": {
            "type": "object",
            "description": "How gold/candidate rows were generated and reviewed.",
            "properties": {
                "generator": {"type": "string"},
                "candidate_file": {"type": "string"},
                "gold_file": {"type": "string"},
                "review_required": {"type": "boolean"},
                "uses_knowledge_graph_context": {"type": "boolean"},
            },
            "additionalProperties": True,
        },
        "config": {
            "type": "object",
            "description": (
                "Full eval run config: retriever_type, top_k, model, seed, "
                "gold file path, folder_ids."
            ),
            "required": ["retriever_type", "top_k", "seed", "gold_file"],
            "properties": {
                "retriever_type": {
                    "type": "string",
                    "enum": ["semantic", "keyword", "hybrid"],
                },
                "top_k": {"type": "integer", "minimum": 1},
                "seed": {"type": "integer"},
                "gold_file": {"type": "string"},
                "model": {"type": "string"},
                "folder_ids": {"type": "array", "items": {"type": "string"}},
            },
        },
        "timestamp": {
            "type": "string",
            "format": "date-time",
            "description": "ISO-8601 UTC timestamp of when the eval run completed.",
        },
        "results": {
            "type": "array",
            "description": "One entry per question in the gold dataset.",
            "items": {
                "type": "object",
                "required": ["question_id", "question", "retrieved_count", "scores"],
                "additionalProperties": False,
                "properties": {
                    "question_id": {"type": "string"},
                    "question": {"type": "string"},
                    "retrieved_count": {"type": "integer", "minimum": 0},
                    "latency_ms": {
                        "type": "number",
                        "description": (
                            "End-to-end wall-clock latency for this question in milliseconds."
                        ),
                    },
                    "ttfc_ms": {
                        "type": "number",
                        "description": (
                            "Time-to-first-chunk in milliseconds (streaming responses only)."
                        ),
                    },
                    "cost_usd": {
                        "type": "number",
                        "description": (
                            "Total cost for this question (input + output + embed + rerank)."
                        ),
                    },
                    "content_type": {
                        "type": "string",
                        "description": "Source modality tag such as text, table, ocr, graph, or mixed.",
                    },
                    "source_metadata": {
                        "type": "array",
                        "items": {"type": "object"},
                    },
                    "knowledge_graph_context": {
                        "type": ["array", "null"],
                        "items": {"type": "string"},
                    },
                    "scores": {
                        "type": "object",
                        "description": (
                            "Per-metric scores for this question. "
                            "Keys are metric IDs from metrics_spec.yaml."
                        ),
                        "properties": {
                            "retrieval_precision_at_k": {
                                "type": "number",
                                "minimum": 0,
                                "maximum": 1,
                            },
                            "retrieval_recall_at_k": {
                                "type": "number",
                                "minimum": 0,
                                "maximum": 1,
                            },
                            "context_relevancy_at_k": {
                                "type": "number",
                                "minimum": 0,
                                "maximum": 1,
                            },
                            "hit_rate_at_k": {
                                "type": "number",
                                "minimum": 0,
                                "maximum": 1,
                            },
                            "citation_precision": {
                                "type": "number",
                                "minimum": 0,
                                "maximum": 1,
                            },
                            "citation_recall": {
                                "type": "number",
                                "minimum": 0,
                                "maximum": 1,
                            },
                            "hallucination_rate": {
                                "type": "number",
                                "minimum": 0,
                                "maximum": 1,
                            },
                            "response_accuracy": {
                                "type": "number",
                                "minimum": 0,
                                "maximum": 1,
                            },
                            "faithfulness": {
                                "type": "number",
                                "minimum": 0,
                                "maximum": 1,
                            },
                            "freshness_days": {"type": "number", "minimum": 0},
                        },
                        "additionalProperties": True,
                    },
                    "judge_prompt_hash": {
                        "type": "string",
                        "description": (
                            "SHA-256 of the LLM-as-judge prompt used for response_accuracy. "
                            "Required when judge scores are present."
                        ),
                    },
                },
            },
        },
        "aggregate_scores": {
            "type": "object",
            "description": (
                "Aggregated scores across all questions. "
                "Keys match metric IDs in metrics_spec.yaml."
            ),
            "properties": {
                "retrieval_precision_at_k": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 1,
                },
                "retrieval_recall_at_k": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 1,
                },
                "context_relevancy_at_k": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 1,
                },
                "hit_rate_at_k": {"type": "number", "minimum": 0, "maximum": 1},
                "citation_precision": {"type": "number", "minimum": 0, "maximum": 1},
                "citation_recall": {"type": "number", "minimum": 0, "maximum": 1},
                "hallucination_rate": {"type": "number", "minimum": 0, "maximum": 1},
                "response_accuracy": {"type": "number", "minimum": 0, "maximum": 1},
                "faithfulness": {"type": "number", "minimum": 0, "maximum": 1},
                "freshness_days_mean": {"type": "number", "minimum": 0},
                "latency_p95_ms": {"type": "number", "minimum": 0},
                "latency_ttfc_p95_ms": {"type": "number", "minimum": 0},
                "cost_per_query_usd_mean": {"type": "number", "minimum": 0},
            },
            "additionalProperties": True,
        },
        "pass_fail_summary": {
            "type": "object",
            "description": (
                "Optional: per-metric pass/fail verdict against thresholds in "
                "metrics_spec.yaml. Populated once thresholds are finalized (post NGAIP-362)."
            ),
            "additionalProperties": {
                "type": "object",
                "required": ["score", "threshold", "passed"],
                "properties": {
                    "score": {"type": "number"},
                    "threshold": {},
                    "passed": {"type": "boolean"},
                },
            },
        },
    },
}

schema_path = (
    BACKEND / "app_retrieval" / "evaluation" / "config" / "eval_report.schema.json"
)
schema_path.parent.mkdir(parents=True, exist_ok=True)
schema_path.write_text(json.dumps(schema, indent=2), encoding="utf-8")
print(f"[NGAIP-415] Created: {schema_path.relative_to(BACKEND)}")

# ---------------------------------------------------------------------------
# docs/metrics_spec.md
# ---------------------------------------------------------------------------
METRICS_SPEC_MD = """\
# RAG Evaluation: Metrics and Success Criteria

**Ticket:** NGAIP-415
**Status:** DRAFT — thresholds TBD pending NGAIP-362 calibration corpus
**Sign-off required:** Adam Thomas + Dave Ferguson
**Blocks:** NGAIP-364 (citation), NGAIP-365 (context relevancy), NGAIP-366 (response accuracy)
**Machine-readable spec:** `app_retrieval/evaluation/config/metrics_spec.yaml`

---

## Top-K Sweep Protocol

All retrieval metrics are evaluated at K = **1, 3, 5**.
Same random seed (**42**) applied across all K values for comparability.
Each K run is fully independent (no shared state between runs).

---

## Metric Definitions

### Retrieval Metrics (owner: NGAIP-365)

| Metric | Definition | Formula | Threshold | Measurement |
|--------|-----------|---------|-----------|-------------|
| **Retrieval Precision@K** | Fraction of top-K chunks overlapping a gold span above tau | `|{c in retrieved[:k] : overlap(c, gold) > tau}| / k` | TBD | Automatic |
| **Retrieval Recall@K** | Fraction of gold spans covered by at least one top-K chunk | `|{s in gold : any(overlap(c, s) > tau for c in retrieved[:k])}| / |gold|` | TBD | Automatic |
| **Context Relevancy@K** | RAGAS context precision/recall over retrieved contexts; token overlap is diagnostic only | `ragas.evaluate(..., context metrics)` | TBD | RAGAS primary |
| **Hit Rate@K** | Binary per-question: 1 if any top-K chunk hits gold, averaged across questions | `mean([1 if any overlap > tau else 0 for q in questions])` | TBD | Automatic |

**Formula choice — Context Relevancy:** Token overlap selected (not character IoU). Resolved in NGAIP-415; consistent with NGAIP-412 POC implementation.

**Tau (overlap threshold):** TBD — to be calibrated on NGAIP-362 pilot rows.

---

### Citation Metrics (owner: NGAIP-364)

| Metric | Definition | Formula | Threshold | Measurement |
|--------|-----------|---------|-----------|-------------|
| **Citation Precision** | Fraction of model citations overlapping a gold citation span above tau | `|{c in model_cites : any(char_overlap(c, g) > tau for g in gold_cites)}| / |model_cites|` | TBD | Automatic |
| **Citation Recall** | Fraction of gold citations recovered by the model | `|{g in gold_cites : any(char_overlap(c, g) > tau for c in model_cites)}| / |gold_cites|` | TBD | Automatic |
| **Hallucination Rate** | Fraction of citations where `asset_id` was not in the retrieved set | `|{c : c.asset_id not in retrieved_asset_ids}| / |model_cites|` | TBD | Automatic |

**Hallucination definition (open item):** Current definition: `asset_id not in retrieved_set` for that query. Strict alternative: also require `not in gold`. AND vs OR to be confirmed with Adam + Dave before NGAIP-364 implementation starts.

**Citation shape:** Align parser with `ChatResponse.sources` — fields `asset_id`, `citation_index`, `source_type` from `app_chatbot/models.py`. Score assistant-role citations only.

---

### Generation / Response Quality Metrics (owner: NGAIP-366)

| Metric | Definition | Formula | Threshold | Measurement |
|--------|-----------|---------|-----------|-------------|
| **Response Accuracy** | LLM-as-judge composite: factuality + completeness + grounding averaged | `(factuality + completeness + grounding) / 3` (each 0/0.5/1) | >= 0.70 (target) | Auto + human calibration |
| **Faithfulness** | RAGAS faithfulness score: answer claims grounded in retrieved chunks | `ragas.evaluate(..., Faithfulness)` | TBD | RAGAS primary |

**Judge model:** Same Azure OpenAI deployment as production, temperature 0.0.
**Prompt versioning:** Prompt hash stored in `report.json` per eval run.
**Inter-rater reliability target:** Cohen's kappa >= 0.70 (human calibration, N >= 30 items).
**Baseline target:** Response accuracy >= 70%; if not met, follow-up story required with root-cause.

---

### Operational Metrics (owner: NGAIP-363)

| Metric | Definition | Formula | Threshold | Measurement |
|--------|-----------|---------|-----------|-------------|
| **Source Freshness (days)** | Mean age of cited documents from last_modified_date to eval run date | `mean([(eval_date - asset.last_modified_date).days for asset in cited])` | TBD | Automatic |
| **Latency P95 (ms)** | 95th-percentile end-to-end wall-clock latency, query to final token | `percentile(latencies_ms, 95)` | TBD | Automatic |
| **Time-to-First-Chunk P95 (ms)** | P95 latency from query to first streamed chunk (streaming only) | `percentile(ttfc_ms, 95)` | TBD | Automatic |
| **Cost per Query (USD)** | Sum of input + output + embedding + rerank costs per query | `(in_tok * p_in) + (out_tok * p_out) + (emb_tok * p_emb) + (rerank * p_rerank)` | TBD | Automatic |

**Latency measurement:** End-to-end (query submission to last token). Streaming: final chunk defines end time.
**Cost components:** All four included — input tokens, output tokens, embedding tokens, rerank calls.
**Pricing source:** Azure OpenAI portal — update `harness config` before each eval run.

---

## Owner Mapping

| Owner Ticket | Metrics |
|-------------|---------|
| NGAIP-365 | retrieval_precision_at_k, retrieval_recall_at_k, context_relevancy_at_k, hit_rate_at_k |
| NGAIP-364 | citation_precision, citation_recall, hallucination_rate |
| NGAIP-366 | response_accuracy, faithfulness |
| NGAIP-363 | freshness_days, latency_p95_ms, latency_ttfc_ms, cost_per_query_usd |

---

## Open Items (Required Before Sign-off)

| # | Item | Owner |
|---|------|-------|
| 1 | Pin tau (token overlap threshold) after NGAIP-362 pilot row review | Adam Thomas |
| 2 | Confirm hallucination AND vs OR condition | Adam Thomas + Dave Ferguson |
| 3 | Set numeric pass/fail thresholds post-calibration (NGAIP-362) | Adam Thomas |
| 4 | Lock LLM-as-judge prompt v1 and record hash | NGAIP-366 |
| 5 | Confirm Azure OpenAI pricing figures for cost_per_query formula | NGAIP-363 |
| 6 | Pin PDF/export of this doc in Jira NGAIP-415 | Martin Petrov |
"""

ensure(BACKEND / "docs" / "metrics_spec.md", METRICS_SPEC_MD)
print("[NGAIP-415] Created: docs/metrics_spec.md")

# ---------------------------------------------------------------------------
# tests/app_retrieval/test_metrics_spec.py
# ---------------------------------------------------------------------------
TEST_METRICS_SPEC_PY = '''\
"""
Structural validation tests for metrics_spec.yaml and eval_report.schema.json (NGAIP-415).

These tests verify the spec and schema are well-formed and internally consistent —
not that any metric implementation is correct (that belongs in 364/365/366).
Run from the ENCHS-PW-GenAI-Backend/ directory:
    pytest tests/app_retrieval/test_metrics_spec.py -v
"""
import json
import pathlib
import pytest
import yaml

SPEC_PATH = pathlib.Path(__file__).parents[3] / "app_retrieval/evaluation/config/metrics_spec.yaml"

REQUIRED_METRIC_FIELDS = {"id", "display_name", "category", "definition", "formula", "threshold", "measurement", "owner_ticket"}
VALID_CATEGORIES = {"retrieval", "citation", "generation", "operational"}
VALID_OWNER_TICKETS = {"NGAIP-363", "NGAIP-364", "NGAIP-365", "NGAIP-366"}
VALID_MEASUREMENT_PREFIXES = ("automatic", "human", "llm", "ragas")
EXPECTED_TOP_K_VALUES = [1, 3, 5]
EXPECTED_TOP_K_SEED = 42
EXPECTED_METRIC_IDS = {
    "retrieval_precision_at_k",
    "retrieval_recall_at_k",
    "context_relevancy_at_k",
    "hit_rate_at_k",
    "citation_precision",
    "citation_recall",
    "hallucination_rate",
    "response_accuracy",
    "faithfulness",
    "freshness_days",
    "latency_p95_ms",
    "latency_ttfc_ms",
    "cost_per_query_usd",
}


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def spec():
    assert SPEC_PATH.exists(), f"metrics_spec.yaml not found at {SPEC_PATH}"
    with SPEC_PATH.open() as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="module")
def metrics(spec):
    return spec["metrics"]


# ---------------------------------------------------------------------------
# Top-level spec structure
# ---------------------------------------------------------------------------

def test_spec_file_exists():
    assert SPEC_PATH.exists()


def test_spec_parses_as_valid_yaml(spec):
    assert spec is not None
    assert isinstance(spec, dict)


def test_spec_has_version_field(spec):
    assert "version" in spec
    assert spec["version"]


def test_spec_has_status_field(spec):
    assert "spec_status" in spec
    assert spec["spec_status"]


def test_spec_is_draft(spec):
    assert "DRAFT" in spec["spec_status"].upper(), (
        "Spec must remain DRAFT until Adam + Dave sign off after NGAIP-362 calibration."
    )


def test_spec_has_owner_ticket(spec):
    assert spec.get("owner_ticket") == "NGAIP-415"


def test_spec_has_calibration_corpus(spec):
    assert "calibration_corpus" in spec


def test_top_k_sweep_values(spec):
    assert spec["top_k_sweep"]["values"] == EXPECTED_TOP_K_VALUES


def test_top_k_sweep_seed(spec):
    assert spec["top_k_sweep"]["seed"] == EXPECTED_TOP_K_SEED


def test_metrics_list_is_present(spec):
    assert "metrics" in spec
    assert isinstance(spec["metrics"], list)
    assert len(spec["metrics"]) > 0


# ---------------------------------------------------------------------------
# Per-metric field validation
# ---------------------------------------------------------------------------

def test_all_metrics_have_required_fields(metrics):
    for m in metrics:
        missing = REQUIRED_METRIC_FIELDS - set(m.keys())
        assert not missing, f"Metric \'{m.get(\'id\', \'?\')}\' missing fields: {missing}"


def test_all_metric_ids_are_snake_case(metrics):
    for m in metrics:
        mid = m["id"]
        assert mid == mid.lower(), f"Metric id \'{mid}\' must be lowercase snake_case"
        assert " " not in mid, f"Metric id \'{mid}\' must not contain spaces"


def test_no_duplicate_metric_ids(metrics):
    ids = [m["id"] for m in metrics]
    assert len(ids) == len(set(ids)), f"Duplicate metric IDs found: {[i for i in ids if ids.count(i) > 1]}"


def test_all_metric_categories_are_valid(metrics):
    for m in metrics:
        assert m["category"] in VALID_CATEGORIES, (
            f"Metric \'{m[\'id\']}\' has unknown category \'{m[\'category\']}\'. "
            f"Expected one of {VALID_CATEGORIES}."
        )


def test_all_owner_tickets_are_valid(metrics):
    for m in metrics:
        assert m["owner_ticket"] in VALID_OWNER_TICKETS, (
            f"Metric \'{m[\'id\']}\' has unexpected owner_ticket \'{m[\'owner_ticket\']}\'. "
            f"Expected one of {VALID_OWNER_TICKETS}."
        )


def test_all_measurements_have_valid_prefix(metrics):
    for m in metrics:
        measurement = str(m["measurement"]).lower()
        assert any(measurement.startswith(p) for p in VALID_MEASUREMENT_PREFIXES), (
            f"Metric \'{m[\'id\']}\' measurement \'{m[\'measurement\']}\' does not start with "
            f"one of {VALID_MEASUREMENT_PREFIXES}."
        )


def test_all_thresholds_have_pass_and_fail(metrics):
    for m in metrics:
        threshold = m["threshold"]
        assert "pass" in threshold, f"Metric \'{m[\'id\']}\' threshold missing \'pass\' key"
        assert "fail" in threshold, f"Metric \'{m[\'id\']}\' threshold missing \'fail\' key"


def test_no_hardcoded_numeric_thresholds(metrics):
    """All thresholds must be TBD strings in DRAFT status — no numeric values yet."""
    skip_ids = {"response_accuracy"}  # 366 already has a 0.70 target in Jira
    for m in metrics:
        if m["id"] in skip_ids:
            continue
        for key in ("pass", "fail"):
            value = str(m["threshold"][key]).strip().upper()
            assert value.startswith("TBD"), (
                f"Metric \'{m[\'id\']}\' threshold.{key} = \'{m[\'threshold\'][key]}\' — "
                "must be \'TBD\' until NGAIP-362 calibration is complete."
            )


def test_all_metrics_have_direction(metrics):
    """Each threshold block should declare whether higher or lower is better."""
    for m in metrics:
        assert "direction" in m["threshold"], (
            f"Metric \'{m[\'id\']}\' threshold is missing \'direction\' "
            "(expected \'higher_is_better\' or \'lower_is_better\')."
        )


def test_direction_values_are_valid(metrics):
    valid_directions = {"higher_is_better", "lower_is_better"}
    for m in metrics:
        direction = m["threshold"].get("direction")
        assert direction in valid_directions, (
            f"Metric \'{m[\'id\']}\' has invalid direction \'{direction}\'. "
            f"Expected one of {valid_directions}."
        )


# ---------------------------------------------------------------------------
# Category-to-owner consistency
# ---------------------------------------------------------------------------

CATEGORY_OWNER_MAP = {
    "retrieval": "NGAIP-365",
    "citation": "NGAIP-364",
    "generation": "NGAIP-366",
    "operational": "NGAIP-363",
}


def test_category_owner_consistency(metrics):
    for m in metrics:
        expected_owner = CATEGORY_OWNER_MAP[m["category"]]
        assert m["owner_ticket"] == expected_owner, (
            f"Metric \'{m[\'id\']}\' category=\'{m[\'category\']}\' should be owned by "
            f"{expected_owner}, got \'{m[\'owner_ticket\']}\'."
        )


# ---------------------------------------------------------------------------
# Coverage — all expected metrics are present
# ---------------------------------------------------------------------------

def test_all_expected_metrics_present(metrics):
    actual_ids = {m["id"] for m in metrics}
    missing = EXPECTED_METRIC_IDS - actual_ids
    assert not missing, f"Expected metrics missing from spec: {missing}"


# ---------------------------------------------------------------------------
# RAGAS evaluator and generated testset provenance in report schema
# ---------------------------------------------------------------------------

def test_eval_report_schema_allows_evaluator_metadata():
    schema_path = pathlib.Path(__file__).parents[3] / "app_retrieval/evaluation/config/eval_report.schema.json"
    schema = json.loads(schema_path.read_text())
    assert "evaluator" in schema["properties"]
    assert "ragas_version" in schema["properties"]["evaluator"]["properties"]


def test_eval_report_schema_allows_testset_and_graph_provenance():
    schema_path = pathlib.Path(__file__).parents[3] / "app_retrieval/evaluation/config/eval_report.schema.json"
    schema = json.loads(schema_path.read_text())
    assert "testset_provenance" in schema["properties"]
    result_props = schema["properties"]["results"]["items"]["properties"]
    assert "knowledge_graph_context" in result_props
    assert "source_metadata" in result_props


# ---------------------------------------------------------------------------
# Retrieval metrics use top_k_sweep values
# ---------------------------------------------------------------------------

def test_retrieval_metrics_reference_k_parameter(metrics):
    retrieval_metrics = [m for m in metrics if m["category"] == "retrieval"]
    for m in retrieval_metrics:
        params = m.get("parameters", {})
        assert "k" in params, (
            f"Retrieval metric \'{m[\'id\']}\' must declare a \'k\' parameter "
            "matching the top_k_sweep values."
        )
        assert params["k"] == EXPECTED_TOP_K_VALUES, (
            f"Retrieval metric \'{m[\'id\']}\' k={params[\'k\']} must match "
            f"top_k_sweep.values={EXPECTED_TOP_K_VALUES}."
        )


# ---------------------------------------------------------------------------
# Hallucination rate — direction check (lower is better)
# ---------------------------------------------------------------------------

def test_hallucination_rate_direction_is_lower_is_better(metrics):
    hallucination = next(m for m in metrics if m["id"] == "hallucination_rate")
    assert hallucination["threshold"]["direction"] == "lower_is_better"


# ---------------------------------------------------------------------------
# Response accuracy — judge model is set
# ---------------------------------------------------------------------------

def test_response_accuracy_has_judge_config(metrics):
    ra = next(m for m in metrics if m["id"] == "response_accuracy")
    assert "judge" in ra, "response_accuracy must declare a \'judge\' configuration block"
    assert "model" in ra["judge"]
    assert "temperature" in ra["judge"]


def test_response_accuracy_judge_temperature_is_zero(metrics):
    ra = next(m for m in metrics if m["id"] == "response_accuracy")
    assert ra["judge"]["temperature"] == 0.0, (
        "LLM-as-judge temperature must be 0.0 for deterministic scoring."
    )
'''

ensure(
    BACKEND / "tests" / "app_retrieval" / "test_metrics_spec.py",
    TEST_METRICS_SPEC_PY,
)
print("[NGAIP-415] Created: tests/app_retrieval/test_metrics_spec.py")

commit_transfer_changes()

print("")
print("[NGAIP-415] Done. Verify with:")
print("  cd ENCHS-PW-GenAI-Backend")
print("  python -c \"import yaml; yaml.safe_load(open('app_retrieval/evaluation/config/metrics_spec.yaml')); print('YAML OK')\"")
print("  python -c \"import json; json.load(open('app_retrieval/evaluation/config/eval_report.schema.json')); print('JSON OK')\"")
print("  pytest tests/app_retrieval/test_metrics_spec.py -v")
