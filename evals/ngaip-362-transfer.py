#!/usr/bin/env python3
# ngaip-362-transfer.py
# Transfers NGAIP-362 gold corpus dataset files to the runtime machine.
# Idempotent: safe to run multiple times.
# Run from: ENCHS-PW-GenAI-Backend/ project root on the target machine.
# Do NOT commit this script.
# Cross-platform replacement for ngaip-362-transfer.sh

import ast
import subprocess
from pathlib import Path


BRANCH = "ngaip-362-corpus-gold-dataset"
COMMIT_MESSAGE = "NGAIP-362: Apply transfer script changes"
BASE_BRANCH = "main-backup-for-mac-claude-repo-04-07-2026"


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
    print(f"[362-transfer] Preparing branch: {BRANCH} from local {BASE_BRANCH}")
    if current_branch() == BRANCH:
        print(f"[362-transfer] Already on ticket branch: {BRANCH}")
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
    obsolete_paths = list(globals().get("OBSOLETE_PATHS", []))
    commit_paths = sorted(set(existing_paths + obsolete_paths))
    if not commit_paths:
        print("[transfer] No generated files exist to commit.")
        return

    print(f"[transfer] Staging {len(existing_paths)} generated file(s) for local commit...")
    if existing_paths:
        git("add", "--", *existing_paths)
    staged = subprocess.run(
        ["git", "diff", "--cached", "--quiet", "--", *commit_paths],
        cwd=repo_root,
        check=False,
    )
    if staged.returncode == 0:
        print("[transfer] No changes to commit.")
        return
    git("commit", "-m", COMMIT_MESSAGE, "--", *commit_paths)
    print(f"[transfer] Created local commit: {COMMIT_MESSAGE}")

def ensure(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def touch(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch()


def patch(path, old, new, label="patch"):
    src = path.read_text(encoding="utf-8")
    if old not in src:
        print(f"[SKIP] {label}")
        return
    path.write_text(src.replace(old, new, 1), encoding="utf-8")
    print(f"[OK] {label}")


def append_if_missing(path, line):
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    if line.strip() not in text:
        with path.open("a", encoding="utf-8") as f:
            f.write(line if line.endswith("\n") else line + "\n")
        print(f"[OK] Appended: {line.strip()}")
    else:
        print(f"[SKIP] Already present: {line.strip()}")


# ---------------------------------------------------------------------------
# Resolve CWD — script must be run from the backend project root
# (where manage.py lives).
# ---------------------------------------------------------------------------
ROOT = Path.cwd()

print(f"[362-transfer] Starting transfer into: {ROOT}")
ensure_ticket_branch()

# ---------------------------------------------------------------------------
# Create directories
# ---------------------------------------------------------------------------
print("[362-transfer] Creating directories...")
(ROOT / "app_retrieval" / "evaluation" / "config").mkdir(parents=True, exist_ok=True)
(ROOT / "tests" / "app_retrieval").mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Package __init__ files (empty, idempotent)
# ---------------------------------------------------------------------------
touch(ROOT / "app_retrieval" / "evaluation" / "__init__.py")
touch(ROOT / "app_retrieval" / "evaluation" / "config" / "__init__.py")
touch(ROOT / "tests" / "app_retrieval" / "__init__.py")
print("[362-transfer] Ensured: __init__.py files")

# ---------------------------------------------------------------------------
# app_retrieval/evaluation/config/gold_schema.py
# ---------------------------------------------------------------------------
GOLD_SCHEMA_PY = """\
from pydantic import BaseModel, ConfigDict
from typing import Literal, Optional


class GoldRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question_id: str
    question: str
    gold_answer: str
    gold_doc_id: str                                    # asset_id from Pratt-Backend
    gold_span_start: Optional[int] = None               # char offset in content_item text
    gold_span_end: Optional[int] = None
    gold_chunk_ids: Optional[list[str]] = None          # LanceDB chunk row keys (alternative to char spans)
    difficulty: Optional[Literal["easy", "medium", "hard"]] = None
    tags: Optional[list[str]] = None
"""

ensure(ROOT / "app_retrieval" / "evaluation" / "config" / "gold_schema.py", GOLD_SCHEMA_PY)
print("[362-transfer] Created: app_retrieval/evaluation/config/gold_schema.py")

# ---------------------------------------------------------------------------
# app_retrieval/evaluation/config/gold_schema.md
# ---------------------------------------------------------------------------
GOLD_SCHEMA_MD = """\
# Gold Dataset CSV Schema

Column specification for the external gold Q/A CSV (stored in the private GitHub gold repo per NGAIP-362 ACs).

| Column | Type | Required | Example | Notes |
|--------|------|----------|---------|-------|
| `question_id` | string | YES | `q-001` | Unique identifier. Use stable slug format. |
| `question` | string | YES | `What is the maintenance interval for the HPT blade?` | Natural-language question answerable from the corpus. |
| `gold_answer` | string | YES | `The HPT blade requires inspection every 3,000 cycles.` | Complete, self-contained reference answer. |
| `gold_doc_id` | string | YES | `asset-0a1b2c3d` | `asset_id` from Pratt-Backend (stable across ingestion). |
| `gold_span_start` | int | NO | `1240` | Character offset (0-based) in the content_item's raw text where the answer span begins. Omit if using chunk IDs. |
| `gold_span_end` | int | NO | `1312` | Character offset where the answer span ends (exclusive). Omit if using chunk IDs. |
| `gold_chunk_ids` | string (JSON array) | NO | `["chunk-abc","chunk-def"]` | LanceDB row keys covering the answer. Alternative to char offsets. |
| `difficulty` | string | NO | `easy` | One of: `easy`, `medium`, `hard`. |
| `tags` | string (JSON array) | NO | `["maintenance","HPT"]` | Free-form topic tags for filtering. |

## Notes

- Either `gold_span_start`/`gold_span_end` OR `gold_chunk_ids` should be populated for citation scoring (NGAIP-364). Both may be populated for redundancy.
- `gold_doc_id` must match the `asset_id` as stored in Pratt-Backend after ingestion through the production pipeline.
- The JSONL variant (used by `gold_dataset.py` and CI fixtures) encodes `gold_chunk_ids` and `tags` as native JSON arrays rather than serialized strings.
"""

ensure(ROOT / "app_retrieval" / "evaluation" / "config" / "gold_schema.md", GOLD_SCHEMA_MD)
print("[362-transfer] Created: app_retrieval/evaluation/config/gold_schema.md")

# ---------------------------------------------------------------------------
# app_retrieval/evaluation/config/ci_gold.jsonl
# ---------------------------------------------------------------------------
CI_GOLD_JSONL = (
    '{"question_id":"ci-001","question":"What is the maintenance interval for component X?",'
    '"gold_answer":"Component X requires maintenance every 500 flight hours.",'
    '"gold_doc_id":"ci-asset-001","difficulty":"easy","tags":["maintenance"]}\n'
    '{"question_id":"ci-002","question":"What materials are approved for repair of section Y?",'
    '"gold_answer":"Section Y repairs must use titanium alloy grade 5.",'
    '"gold_doc_id":"ci-asset-002","difficulty":"medium","tags":["materials","repair"]}\n'
)

ensure(ROOT / "app_retrieval" / "evaluation" / "config" / "ci_gold.jsonl", CI_GOLD_JSONL)
print("[362-transfer] Created: app_retrieval/evaluation/config/ci_gold.jsonl")

# ---------------------------------------------------------------------------
# Consolidated NGAIP-362 generated modules
# ---------------------------------------------------------------------------
OBSOLETE_PATHS = ['app_retrieval/evaluation/gold_loader.py', 'app_retrieval/evaluation/langchain_document_loader.py', 'app_retrieval/evaluation/knowledge_graph_context.py', 'app_retrieval/evaluation/testset_generator.py', 'app_retrieval/evaluation/gold_promoter.py', 'tests/app_retrieval/test_gold_loader.py', 'tests/app_retrieval/test_langchain_document_loader.py', 'tests/app_retrieval/test_knowledge_graph_context.py', 'tests/app_retrieval/test_testset_generator.py', 'tests/app_retrieval/test_gold_promoter.py', 'tests/app_retrieval/test_golden_test_generator.py']


def remove_obsolete_generated_files() -> None:
    print("[362-transfer] Removing obsolete split NGAIP-362 files if present...")
    git("rm", "--ignore-unmatch", "--", *OBSOLETE_PATHS)


remove_obsolete_generated_files()

# ---------------------------------------------------------------------------
# app_retrieval/evaluation/gold_dataset.py
# ---------------------------------------------------------------------------
GOLD_DATASET_PY = 'from __future__ import annotations\n\nimport json\nfrom pathlib import Path\n\nfrom app_retrieval.evaluation.config.gold_schema import GoldRow\n\n\nPROMOTABLE_STATUSES = {"approved", "edited"}\n\n\ndef load_gold_file(path: str | Path) -> list[GoldRow]:\n    """Load and validate a gold JSONL file. Raises ValueError on bad rows."""\n    rows: list[GoldRow] = []\n    with Path(path).open(encoding="utf-8") as handle:\n        for i, line in enumerate(handle, start=1):\n            line = line.strip()\n            if not line:\n                continue\n            try:\n                rows.append(GoldRow.model_validate_json(line))\n            except Exception as exc:\n                raise ValueError(f"Invalid gold row at line {i}: {exc}") from exc\n    return rows\n\n\ndef promote_candidates_to_gold(candidate_path: Path, gold_path: Path) -> list[GoldRow]:\n    """Promote reviewed RAGAS-generated candidates into the official gold set."""\n    promoted: list[GoldRow] = []\n    for line in candidate_path.read_text(encoding="utf-8").splitlines():\n        if not line.strip():\n            continue\n        row = json.loads(line)\n        if row.get("review_status") not in PROMOTABLE_STATUSES:\n            continue\n        source_metadata = row.get("source_metadata") or []\n        first_source = source_metadata[0] if source_metadata else {}\n        gold_row = GoldRow(\n            question_id=row.get("question_id") or row["candidate_id"],\n            question=row["question"],\n            gold_answer=row["reference_answer"],\n            gold_doc_id=first_source.get("asset_id", "unknown"),\n            gold_chunk_ids=[item["chunk_id"] for item in source_metadata if item.get("chunk_id")] or None,\n            tags=row.get("tags"),\n        )\n        promoted.append(gold_row)\n\n    gold_path.parent.mkdir(parents=True, exist_ok=True)\n    with gold_path.open("w", encoding="utf-8") as handle:\n        for row in promoted:\n            handle.write(row.model_dump_json(exclude_none=True) + "\\n")\n    return promoted\n'
ensure(ROOT / "app_retrieval" / "evaluation" / "gold_dataset.py", GOLD_DATASET_PY)
print("[362-transfer] Created: app_retrieval/evaluation/gold_dataset.py")

# ---------------------------------------------------------------------------
# app_retrieval/evaluation/golden_test_generator.py
# ---------------------------------------------------------------------------
GOLDEN_TEST_GENERATOR_PY = 'from __future__ import annotations\n\nimport json\nfrom collections.abc import Iterable, Sequence\nfrom importlib.metadata import version\nfrom pathlib import Path\nfrom typing import Any\n\nfrom langchain_core.documents import Document\n\n\nDEFAULT_TEXT_FIELDS = ("text", "content", "chunk", "body", "page_content")\nVECTOR_FIELDS = {"vector", "embedding", "embeddings"}\nREQUIRED_JSONL_FIELDS = {"asset_id", "text"}\n\n\ndef _row_to_document(\n    row: dict[str, Any],\n    *,\n    text_fields: Sequence[str] = DEFAULT_TEXT_FIELDS,\n    source_line: int | None = None,\n) -> Document:\n    """Convert a LanceDB/export row into the LangChain Document shape RAGAS expects."""\n    text_field = next((field for field in text_fields if row.get(field)), None)\n    if text_field is None:\n        raise ValueError(f"Row is missing a text field; tried {list(text_fields)}")\n    metadata = {\n        key: value\n        for key, value in row.items()\n        if key != text_field and key not in VECTOR_FIELDS\n    }\n    metadata["text_field"] = text_field\n    if source_line is not None:\n        metadata["source_line"] = source_line\n    return Document(page_content=str(row[text_field]), metadata=metadata)\n\n\ndef load_lancedb_documents(\n    db_path: str | Path,\n    table_name: str,\n    *,\n    limit: int | None = None,\n    text_fields: Sequence[str] = DEFAULT_TEXT_FIELDS,\n) -> list[Document]:\n    """Load existing LanceDB rows into LangChain Documents for RAGAS generation."""\n    import lancedb\n\n    db = lancedb.connect(str(db_path))\n    table = db.open_table(table_name)\n    rows = table.to_arrow().to_pylist()\n    if limit is not None:\n        rows = rows[:limit]\n    return [_row_to_document(row, text_fields=text_fields) for row in rows]\n\n\ndef load_langchain_documents(path: Path) -> list[Document]:\n    """Load an approved JSONL export into LangChain Documents as an offline fallback."""\n    docs: list[Document] = []\n    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):\n        if not line.strip():\n            continue\n        try:\n            row = json.loads(line)\n        except json.JSONDecodeError as exc:\n            raise ValueError(f"Invalid source document JSON at line {line_number}: {exc}") from exc\n        missing = REQUIRED_JSONL_FIELDS - row.keys()\n        if missing:\n            raise ValueError(f"Missing source document fields at line {line_number}: {sorted(missing)}")\n        docs.append(_row_to_document(row, source_line=line_number))\n    return docs\n\n\ndef serialize_knowledge_graph_context(graph_data: dict[str, list[dict[str, Any]]] | None) -> str:\n    """Serialize graph nodes/links into stable text for testset generation."""\n    if not graph_data:\n        return ""\n    nodes = graph_data.get("nodes", [])\n    links = graph_data.get("links", [])\n    lines = ["Knowledge graph context:"]\n    if nodes:\n        lines.append("Entities:")\n        for node in nodes:\n            node_id = node.get("id")\n            group = node.get("group")\n            suffix = f" (group: {group})" if group is not None else ""\n            lines.append(f"- {node_id}{suffix}")\n    if links:\n        lines.append("Relationships:")\n        for link in links:\n            source = link.get("source")\n            target = link.get("target")\n            predicate = link.get("predicate") or "related_to"\n            lines.append(f"- {source} --{predicate}--> {target}")\n    return "\\n".join(lines)\n\n\ndef attach_knowledge_graph_context(\n    documents: Iterable[Document],\n    graph_data: dict[str, list[dict[str, Any]]] | None,\n) -> list[Document]:\n    """Append serialized graph context to LangChain Documents."""\n    graph_context = serialize_knowledge_graph_context(graph_data)\n    if not graph_context:\n        return list(documents)\n    enriched: list[Document] = []\n    for doc in documents:\n        metadata = dict(doc.metadata)\n        metadata["knowledge_graph_context"] = graph_context\n        metadata["has_knowledge_graph_context"] = True\n        enriched.append(Document(page_content=f"{doc.page_content}\\n\\n{graph_context}", metadata=metadata))\n    return enriched\n\n\ndef _ragas_version() -> str:\n    try:\n        return version("ragas")\n    except Exception:\n        return "unknown"\n\n\ndef generate_candidate_testset(\n    documents: Sequence[Document],\n    *,\n    size: int,\n    generator_llm,\n    critic_llm,\n    embeddings,\n) -> list[dict]:\n    """Generate candidate QA/reference rows with RAGAS."""\n    try:\n        from ragas.testset import TestsetGenerator\n    except ImportError:\n        from ragas.testset.generator import TestsetGenerator\n    generator = TestsetGenerator.from_langchain(\n        generator_llm=generator_llm,\n        critic_llm=critic_llm,\n        embeddings=embeddings,\n    )\n    testset = generator.generate_with_langchain_docs(list(documents), test_size=size)\n    return normalize_ragas_testset(testset, documents)\n\n\ndef normalize_ragas_testset(testset, documents: Sequence[Document]) -> list[dict]:\n    """Convert RAGAS output into PrattWise candidate rows."""\n    if hasattr(testset, "to_pandas"):\n        records = testset.to_pandas().to_dict(orient="records")\n    elif hasattr(testset, "to_list"):\n        records = testset.to_list()\n    else:\n        records = list(testset)\n    source_metadata = [doc.metadata for doc in documents]\n    knowledge_graph_context = [\n        doc.metadata["knowledge_graph_context"]\n        for doc in documents\n        if doc.metadata.get("knowledge_graph_context")\n    ]\n    rows: list[dict] = []\n    for index, record in enumerate(records, start=1):\n        rows.append(\n            {\n                "candidate_id": f"candidate-{index:04d}",\n                "question": record.get("question") or record.get("user_input"),\n                "reference_answer": record.get("ground_truth") or record.get("reference"),\n                "supporting_context": record.get("contexts") or record.get("reference_contexts"),\n                "source_metadata": source_metadata,\n                "knowledge_graph_context": knowledge_graph_context or None,\n                "review_status": "candidate",\n                "generator": {"framework": "ragas", "ragas_version": _ragas_version()},\n            }\n        )\n    return rows\n\n\ndef dump_candidate_rows(path: Path, rows: Iterable[dict]) -> None:\n    path.parent.mkdir(parents=True, exist_ok=True)\n    with path.open("w", encoding="utf-8") as handle:\n        for row in rows:\n            handle.write(json.dumps(row, ensure_ascii=False) + "\\n")\n\n\ndef load_eval_config(path: Path):\n    from app_retrieval.evaluation.config.eval_config import load_eval_config as _load_eval_config\n    return _load_eval_config(path)\n\n\ndef build_ragas_langchain_models(config):\n    from app_retrieval.evaluation.ragas_factory import build_ragas_langchain_models as _build_models\n    return _build_models(config)\n\n\ndef build_ragas_azure_completion_llm(config):\n    from app_retrieval.evaluation.ragas_factory import build_ragas_azure_completion_llm as _build_completion_llm\n    return _build_completion_llm(config)\n\n\ndef generate_golden_candidates(\n    *,\n    source_docs_path: Path,\n    eval_config_path: Path,\n    output_path: Path,\n    size: int,\n    graph_data: dict | None = None,\n) -> list[dict]:\n    """Generate candidate golden-set rows from approved source documents."""\n    config = load_eval_config(eval_config_path)\n    if not config.evaluator.enabled:\n        raise ValueError("RAGAS evaluator must be enabled to generate golden candidates")\n    documents = load_langchain_documents(source_docs_path)\n    documents = attach_knowledge_graph_context(documents, graph_data)\n    chat_llm, embeddings = build_ragas_langchain_models(config.evaluator)\n    completion_llm = build_ragas_azure_completion_llm(config.evaluator)\n    candidates = generate_candidate_testset(\n        documents,\n        size=size,\n        generator_llm=chat_llm,\n        critic_llm=completion_llm,\n        embeddings=embeddings,\n    )\n    dump_candidate_rows(output_path, candidates)\n    return candidates\n'
ensure(ROOT / "app_retrieval" / "evaluation" / "golden_test_generator.py", GOLDEN_TEST_GENERATOR_PY)
print("[362-transfer] Created: app_retrieval/evaluation/golden_test_generator.py")

# ---------------------------------------------------------------------------
# tests/app_retrieval/test_gold_dataset_generation.py
# ---------------------------------------------------------------------------
TEST_GOLD_DATASET_GENERATION_PY = 'import json\nimport sys\nfrom pathlib import Path\nfrom types import SimpleNamespace\n\nimport pytest\nfrom langchain_core.documents import Document\n\nfrom app_retrieval.evaluation.config.gold_schema import GoldRow\nfrom app_retrieval.evaluation.gold_dataset import load_gold_file, promote_candidates_to_gold\nfrom app_retrieval.evaluation.golden_test_generator import (\n    attach_knowledge_graph_context,\n    generate_golden_candidates,\n    load_lancedb_documents,\n    load_langchain_documents,\n    normalize_ragas_testset,\n    serialize_knowledge_graph_context,\n)\n\n\nCI_GOLD = Path(__file__).parents[2] / "app_retrieval/evaluation/config/ci_gold.jsonl"\n\n\ndef test_load_ci_gold_returns_valid_rows():\n    rows = load_gold_file(CI_GOLD)\n    assert len(rows) == 2\n    assert all(isinstance(row, GoldRow) for row in rows)\n    assert rows[0].question_id == "ci-001"\n    assert rows[1].difficulty == "medium"\n\n\ndef test_load_gold_file_raises_on_missing_required_field(tmp_path):\n    bad = tmp_path / "bad.jsonl"\n    bad.write_text(json.dumps({"question_id": "x", "question": "q", "gold_doc_id": "d"}) + "\\n")\n    with pytest.raises(ValueError, match="Invalid gold row at line 1"):\n        load_gold_file(bad)\n\n\ndef test_load_gold_file_skips_blank_lines(tmp_path):\n    fixture = tmp_path / "fixture.jsonl"\n    row = {"question_id": "t-001", "question": "Q?", "gold_answer": "A.", "gold_doc_id": "d-001"}\n    fixture.write_text("\\n" + json.dumps(row) + "\\n\\n")\n    assert len(load_gold_file(fixture)) == 1\n\n\ndef test_load_gold_file_with_optional_span_and_chunk_fields(tmp_path):\n    fixture = tmp_path / "full.jsonl"\n    row = {\n        "question_id": "t-002",\n        "question": "Q?",\n        "gold_answer": "A.",\n        "gold_doc_id": "d-002",\n        "gold_span_start": 100,\n        "gold_span_end": 200,\n        "gold_chunk_ids": ["chunk-abc", "chunk-def"],\n        "difficulty": "hard",\n        "tags": ["materials", "repair"],\n    }\n    fixture.write_text(json.dumps(row) + "\\n")\n    loaded = load_gold_file(fixture)[0]\n    assert loaded.gold_span_start == 100\n    assert loaded.gold_chunk_ids == ["chunk-abc", "chunk-def"]\n    assert loaded.tags == ["materials", "repair"]\n\n\ndef test_load_gold_file_raises_on_invalid_json_line(tmp_path):\n    bad = tmp_path / "bad_json.jsonl"\n    bad.write_text("not valid json at all\\n")\n    with pytest.raises(ValueError, match="Invalid gold row at line 1"):\n        load_gold_file(bad)\n\n\ndef test_load_gold_file_raises_on_extra_field(tmp_path):\n    bad = tmp_path / "extra.jsonl"\n    row = {\n        "question_id": "t-003",\n        "question": "Q?",\n        "gold_answer": "A.",\n        "gold_doc_id": "d-003",\n        "unknown_field": "should be rejected",\n    }\n    bad.write_text(json.dumps(row) + "\\n")\n    with pytest.raises(ValueError, match="Invalid gold row at line 1"):\n        load_gold_file(bad)\n\n\ndef test_load_langchain_documents_preserves_metadata(tmp_path):\n    source = tmp_path / "approved_docs.jsonl"\n    source.write_text(json.dumps({"asset_id": "asset-1", "text": "hello", "chunk_id": "chunk-1"}) + "\\n")\n    docs = load_langchain_documents(source)\n    assert len(docs) == 1\n    assert isinstance(docs[0], Document)\n    assert docs[0].page_content == "hello"\n    assert docs[0].metadata["asset_id"] == "asset-1"\n    assert docs[0].metadata["chunk_id"] == "chunk-1"\n    assert docs[0].metadata["text_field"] == "text"\n\n\ndef test_load_lancedb_documents_uses_existing_rows(monkeypatch):\n    rows = [{"asset_id": "asset-1", "content": "from LanceDB", "vector": [0.1, 0.2]}]\n    fake_table = SimpleNamespace(to_arrow=lambda: SimpleNamespace(to_pylist=lambda: rows))\n    fake_db = SimpleNamespace(open_table=lambda table_name: fake_table)\n    fake_lancedb = SimpleNamespace(connect=lambda db_path: fake_db)\n    monkeypatch.setitem(sys.modules, "lancedb", fake_lancedb)\n    docs = load_lancedb_documents("/tmp/lancedb", "chunks", text_fields=("content", "text"))\n    assert docs[0].page_content == "from LanceDB"\n    assert docs[0].metadata["asset_id"] == "asset-1"\n    assert "vector" not in docs[0].metadata\n    assert docs[0].metadata["text_field"] == "content"\n\n\ndef test_serialize_knowledge_graph_context_includes_nodes_and_links():\n    graph = {\n        "nodes": [{"id": "Blade", "group": "part"}],\n        "links": [{"source": "Blade", "target": "Inspection", "predicate": "requires"}],\n    }\n    text = serialize_knowledge_graph_context(graph)\n    assert "Blade" in text\n    assert "requires" in text\n    assert "Inspection" in text\n\n\ndef test_attach_knowledge_graph_context_updates_document_text_and_metadata():\n    docs = [Document(page_content="Source text", metadata={"asset_id": "asset-1"})]\n    enriched = attach_knowledge_graph_context(docs, {"nodes": [{"id": "Entity"}], "links": []})\n    assert "Knowledge graph context" in enriched[0].page_content\n    assert enriched[0].metadata["has_knowledge_graph_context"] is True\n\n\nclass FakeTestset:\n    def to_list(self):\n        return [{"question": "Q?", "ground_truth": "A.", "contexts": ["ctx"]}]\n\n\ndef test_normalize_ragas_testset_preserves_source_and_graph_metadata():\n    docs = [\n        Document(\n            page_content="ctx",\n            metadata={"asset_id": "asset-1", "chunk_id": "chunk-1", "knowledge_graph_context": "KG"},\n        )\n    ]\n    rows = normalize_ragas_testset(FakeTestset(), docs)\n    assert rows[0]["question"] == "Q?"\n    assert rows[0]["reference_answer"] == "A."\n    assert rows[0]["source_metadata"][0]["asset_id"] == "asset-1"\n    assert rows[0]["knowledge_graph_context"] == ["KG"]\n    assert rows[0]["review_status"] == "candidate"\n\n\ndef test_promote_candidates_to_gold_only_promotes_approved_rows(tmp_path):\n    candidates = tmp_path / "candidates.jsonl"\n    gold = tmp_path / "gold.jsonl"\n    candidates.write_text(\n        json.dumps({\n            "candidate_id": "candidate-0001",\n            "question": "Q?",\n            "reference_answer": "A.",\n            "review_status": "approved",\n            "source_metadata": [{"asset_id": "asset-1", "chunk_id": "chunk-1"}],\n        }) + "\\n" +\n        json.dumps({\n            "candidate_id": "candidate-0002",\n            "question": "Reject?",\n            "reference_answer": "No.",\n            "review_status": "rejected",\n            "source_metadata": [{"asset_id": "asset-2"}],\n        }) + "\\n"\n    )\n    rows = promote_candidates_to_gold(candidates, gold)\n    assert len(rows) == 1\n    assert rows[0].question_id == "candidate-0001"\n    assert rows[0].gold_doc_id == "asset-1"\n    assert rows[0].gold_chunk_ids == ["chunk-1"]\n    assert len(gold.read_text().splitlines()) == 1\n\n\ndef test_generate_golden_candidates_wires_loader_factory_generator_and_writer(tmp_path, monkeypatch):\n    calls = []\n    monkeypatch.setattr(\n        "app_retrieval.evaluation.golden_test_generator.load_eval_config",\n        lambda path: SimpleNamespace(evaluator=SimpleNamespace(enabled=True)),\n    )\n    monkeypatch.setattr(\n        "app_retrieval.evaluation.golden_test_generator.load_langchain_documents",\n        lambda path: [Document(page_content="doc", metadata={})],\n    )\n    monkeypatch.setattr(\n        "app_retrieval.evaluation.golden_test_generator.attach_knowledge_graph_context",\n        lambda docs, graph_data: docs,\n    )\n    monkeypatch.setattr(\n        "app_retrieval.evaluation.golden_test_generator.build_ragas_langchain_models",\n        lambda config: ("chat", "embeddings"),\n    )\n    monkeypatch.setattr(\n        "app_retrieval.evaluation.golden_test_generator.build_ragas_azure_completion_llm",\n        lambda config: "completion",\n    )\n    monkeypatch.setattr(\n        "app_retrieval.evaluation.golden_test_generator.generate_candidate_testset",\n        lambda docs, size, generator_llm, critic_llm, embeddings: [{"candidate_id": "candidate-0001"}],\n    )\n    monkeypatch.setattr(\n        "app_retrieval.evaluation.golden_test_generator.dump_candidate_rows",\n        lambda path, rows: calls.append((path, rows)),\n    )\n    output = tmp_path / "candidate_testset.jsonl"\n    rows = generate_golden_candidates(\n        source_docs_path=tmp_path / "approved_docs.jsonl",\n        eval_config_path=tmp_path / "rag_eval.yaml",\n        output_path=output,\n        size=5,\n        graph_data={"nodes": [], "links": []},\n    )\n    assert rows == [{"candidate_id": "candidate-0001"}]\n    assert calls == [(output, rows)]\n'
ensure(ROOT / "tests" / "app_retrieval" / "test_gold_dataset_generation.py", TEST_GOLD_DATASET_GENERATION_PY)
print("[362-transfer] Created: tests/app_retrieval/test_gold_dataset_generation.py")

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
commit_transfer_changes()

print("")
print("[362-transfer] Complete. Verify with:")
print("  pytest tests/app_retrieval/test_gold_dataset_generation.py -v")
print("")
print("  # Confirm CI fixture validates cleanly:")
print('  python -c "')
print("  from app_retrieval.evaluation.gold_dataset import load_gold_file")
print("  rows = load_gold_file('app_retrieval/evaluation/config/ci_gold.jsonl')")
print("  assert len(rows) == 2")
print("  print('OK:', [r.question_id for r in rows])")
print('  "')
