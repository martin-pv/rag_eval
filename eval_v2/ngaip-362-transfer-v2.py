#!/usr/bin/env python3
"""NGAIP-362 v2: gold dataset contract and async RAGAS candidate generation."""
import subprocess
import sys
from pathlib import Path

BASE_BRANCH = "main"
BACKEND = Path.cwd()

def git(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=BACKEND, check=check, text=True)

def prepare_branch(branch: str) -> None:
    current = subprocess.run(["git", "branch", "--show-current"], cwd=BACKEND, text=True, capture_output=True, check=True).stdout.strip()
    if current == branch:
        return
    if git("switch", branch, check=False).returncode == 0:
        return
    git("switch", BASE_BRANCH)
    git("switch", "-c", branch)

def write(path: str, content: str) -> Path:
    target = BACKEND / path
    target.parent.mkdir(parents=True, exist_ok=True)
    # Use write_bytes to force LF line endings on Windows (text mode would
    # translate "\n" -> "\r\n", contaminating generated .py and .jsonl files).
    target.write_bytes(content.encode("utf-8"))
    print(f"[write] {target.relative_to(BACKEND)}")
    return target

def touch(path: str) -> Path:
    target = BACKEND / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.touch(exist_ok=True)
    return target

def run_pytest(test_paths: list[str]) -> None:
    if test_paths:
        subprocess.run([sys.executable, "-m", "pytest", *test_paths, "-v"], cwd=BACKEND, check=True)

def commit(paths: list[str], forced_tests: list[str], message: str) -> None:
    if paths:
        git("add", *paths)
    for test_path in forced_tests:
        git("add", "-f", test_path)
    status = subprocess.run(["git", "status", "--short"], cwd=BACKEND, text=True, capture_output=True, check=True).stdout.strip()
    if not status:
        print("[commit] no changes")
        return
    git("commit", "-m", message)

BRANCH = 'ngaip-362-corpus-gold-dataset-v2'
COMMIT_MESSAGE = 'NGAIP-362: Apply v2 RAGAS gold dataset changes'

SAMPLE_GOLD_JSONL = Path(__file__).with_name("sample_gold_v2.jsonl").read_text(encoding="utf-8")
GOLD_SCHEMA = 'from __future__ import annotations\n\nfrom typing import Any, Literal\nfrom pydantic import BaseModel, ConfigDict, Field, model_validator\n\n\nclass GoldRow(BaseModel):\n    model_config = ConfigDict(extra="forbid")\n\n    question_id: str\n    question: str\n    gold_answer: str = Field(description="Reference answer; maps to RAGAS reference.")\n    gold_doc_id: str\n    gold_chunk_ids: list[str] | None = None\n    reference_contexts: list[str] | None = None\n    difficulty: Literal["easy", "medium", "hard"] | None = None\n    tags: list[str] | None = None\n    synthesizer_name: str | None = None\n    ragas_metadata: dict[str, Any] | None = None\n\n    @model_validator(mode="after")\n    def _has_context(self) -> "GoldRow":\n        if self.reference_contexts is not None and len(self.reference_contexts) == 0:\n            raise ValueError("reference_contexts cannot be empty when provided")\n        return self\n\n    def to_ragas_record(self, response: str | None = None, contexts: list[str] | None = None) -> dict[str, Any]:\n        retrieved_contexts = contexts or self.reference_contexts or []\n        answer = response or self.gold_answer\n        return {\n            "user_input": self.question,\n            "response": answer,\n            "retrieved_contexts": retrieved_contexts,\n            "reference": self.gold_answer,\n        }\n'
GOLD_DATASET = "from __future__ import annotations\n\nimport json\nfrom pathlib import Path\nfrom typing import Iterable\n\nfrom datasets import Dataset\n\nfrom app_retrieval.evaluation.config.gold_schema import GoldRow\n\n\ndef load_gold_file(path: str | Path) -> list[GoldRow]:\n    rows: list[GoldRow] = []\n    for line_number, line in enumerate(Path(path).read_text(encoding=\"utf-8\").splitlines(), start=1):\n        if not line.strip():\n            continue\n        try:\n            rows.append(GoldRow.model_validate_json(line))\n        except Exception as exc:\n            raise ValueError(f\"Invalid gold row at line {line_number}: {exc}\") from exc\n    return rows\n\n\ndef to_ragas_records(rows: Iterable[GoldRow], responses: dict[str, str] | None = None, contexts: dict[str, list[str]] | None = None) -> list[dict]:\n    responses = responses or {}\n    contexts = contexts or {}\n    return [row.to_ragas_record(response=responses.get(row.question_id), contexts=contexts.get(row.question_id)) for row in rows]\n\n\ndef to_ragas_dataset(rows: Iterable[GoldRow], responses: dict[str, str] | None = None, contexts: dict[str, list[str]] | None = None) -> Dataset:\n    return Dataset.from_list(to_ragas_records(rows, responses=responses, contexts=contexts))\n\n\ndef append_approved_candidates(candidates_path: str | Path, gold_path: str | Path, approved_ids: set[str]) -> int:\n    promoted = []\n    for line in Path(candidates_path).read_text(encoding=\"utf-8\").splitlines():\n        if not line.strip():\n            continue\n        data = json.loads(line)\n        if data.get(\"question_id\") in approved_ids:\n            promoted.append(GoldRow.model_validate(data))\n    with Path(gold_path).open(\"a\", encoding=\"utf-8\", newline=\"\\n\") as handle:\n        for row in promoted:\n            handle.write(row.model_dump_json(exclude_none=True) + \"\\n\")\n    return len(promoted)\n"
CANDIDATE_GENERATOR = 'from __future__ import annotations\n\nimport asyncio\nimport json\nfrom importlib.metadata import PackageNotFoundError, version\nfrom pathlib import Path\nfrom typing import Any, Iterable, Sequence\n\nfrom langchain_core.documents import Document\n\n\ndef ragas_version() -> str:\n    try:\n        return version("ragas")\n    except PackageNotFoundError:\n        return "unknown"\n\n\ndef load_jsonl_documents(path: str | Path) -> list[Document]:\n    docs: list[Document] = []\n    for line in Path(path).read_text(encoding="utf-8").splitlines():\n        if not line.strip():\n            continue\n        data = json.loads(line)\n        docs.append(Document(page_content=data.get("page_content") or data.get("text") or "", metadata=data.get("metadata", {})))\n    return docs\n\n\ndef serialize_knowledge_graph_context(rows: Iterable[dict[str, Any]]) -> str:\n    facts = []\n    for row in rows:\n        subject = row.get("subject") or row.get("source")\n        relation = row.get("relation") or row.get("predicate")\n        obj = row.get("object") or row.get("target")\n        if subject and relation and obj:\n            facts.append(f"{subject} --{relation}--> {obj}")\n    return "\\n".join(facts)\n\n\ndef attach_knowledge_graph_context(documents: Sequence[Document], kg_context: str) -> list[Document]:\n    if not kg_context:\n        return list(documents)\n    return [Document(page_content=f"{doc.page_content}\\n\\nKnowledge graph context:\\n{kg_context}", metadata={**doc.metadata, "knowledge_graph_context_attached": True}) for doc in documents]\n\n\ndef _generate_sync(documents: Sequence[Document], test_size: int, llm=None, embedding_model=None, knowledge_graph=None, llm_context: str | None = None):\n    try:\n        from ragas.testset import TestsetGenerator\n    except ImportError:\n        from ragas.testset.generator import TestsetGenerator\n    if hasattr(TestsetGenerator, "from_langchain") and llm is not None and embedding_model is not None:\n        try:\n            generator = TestsetGenerator.from_langchain(llm=llm, embedding_model=embedding_model, knowledge_graph=knowledge_graph, llm_context=llm_context)\n        except TypeError:\n            generator = TestsetGenerator.from_langchain(generator_llm=llm, critic_llm=llm, embeddings=embedding_model)\n    else:\n        generator = TestsetGenerator\n    if hasattr(generator, "generate_with_langchain_docs"):\n        return generator.generate_with_langchain_docs(list(documents), testset_size=test_size)\n    return generator.generate(list(documents), test_size=test_size)\n\n\nasync def agenerate_candidate_testset(documents: Sequence[Document], test_size: int, llm=None, embedding_model=None, kg_rows: Iterable[dict[str, Any]] | None = None, knowledge_graph=None):\n    kg_context = serialize_knowledge_graph_context(kg_rows or [])\n    docs = attach_knowledge_graph_context(documents, kg_context)\n    return await asyncio.to_thread(_generate_sync, docs, test_size, llm, embedding_model, knowledge_graph, kg_context or None)\n'
LANCEDB_LOADER = 'from __future__ import annotations\n\nfrom pathlib import Path\nfrom typing import Iterable\n\nfrom langchain_core.documents import Document\n\n\ndef load_lancedb_documents(\n    db_path: str | Path,\n    table_name: str,\n    *,\n    where: str | None = None,\n    text_field: str = "text",\n    metadata_fields: Iterable[str] = ("source", "doc_id", "chunk_id", "page", "asset_id"),\n    limit: int | None = None,\n) -> list[Document]:\n    """Load Documents from a LanceDB table for RAGAS testset generation.\n\n    Wires the existing PrattWise LanceDB store into RAGAS golden-set generation.\n    Lazily imports lancedb so callers without it can still import the module.\n    """\n    import lancedb\n    db = lancedb.connect(str(db_path))\n    table = db.open_table(table_name)\n    query = table.search() if where is None else table.search().where(where)\n    if limit:\n        query = query.limit(limit)\n    if hasattr(query, "to_list"):\n        rows = query.to_list()\n    else:\n        rows = list(query.to_arrow().to_pylist())\n    documents: list[Document] = []\n    for row in rows:\n        text = row.get(text_field) or row.get("page_content") or ""\n        metadata = {field: row[field] for field in metadata_fields if field in row}\n        documents.append(Document(page_content=text, metadata=metadata))\n    return documents\n'
TESTS = "from pathlib import Path\nfrom unittest.mock import MagicMock, patch\n\nfrom langchain_core.documents import Document\n\nfrom app_retrieval.evaluation.gold_dataset import load_gold_file, to_ragas_records\nfrom app_retrieval.evaluation.golden_test_generator import attach_knowledge_graph_context, serialize_knowledge_graph_context\nfrom app_retrieval.evaluation.lancedb_loader import load_lancedb_documents\n\n\ndef test_sample_gold_has_50_rows():\n    rows = load_gold_file(Path(\"app_retrieval/evaluation/config/sample_gold.jsonl\"))\n    assert len(rows) >= 50\n    assert all(row.reference_contexts for row in rows)\n\n\ndef test_gold_rows_convert_to_ragas_records():\n    row = load_gold_file(Path(\"app_retrieval/evaluation/config/sample_gold.jsonl\"))[0]\n    record = to_ragas_records([row])[0]\n    assert set(record) == {\"user_input\", \"response\", \"retrieved_contexts\", \"reference\"}\n\n\ndef test_kg_context_attaches_to_documents():\n    kg = serialize_knowledge_graph_context([{\"subject\": \"A\", \"relation\": \"uses\", \"object\": \"B\"}])\n    docs = attach_knowledge_graph_context([Document(page_content=\"base\", metadata={})], kg)\n    assert \"A --uses--> B\" in docs[0].page_content\n\n\ndef test_lancedb_loader_returns_langchain_documents():\n    fake_table = MagicMock()\n    fake_table.search.return_value.to_list.return_value = [\n        {\"text\": \"hello\", \"doc_id\": \"d1\", \"chunk_id\": \"c1\"},\n    ]\n    fake_db = MagicMock()\n    fake_db.open_table.return_value = fake_table\n    with patch.dict(\"sys.modules\", {\"lancedb\": MagicMock(connect=MagicMock(return_value=fake_db))}):\n        docs = load_lancedb_documents(\"/db\", \"chunks\")\n    assert len(docs) == 1\n    assert isinstance(docs[0], Document)\n    assert docs[0].page_content == \"hello\"\n    assert docs[0].metadata[\"doc_id\"] == \"d1\"\n"

def main() -> None:
    prepare_branch(BRANCH)
    touch("app_retrieval/__init__.py")
    touch("app_retrieval/evaluation/__init__.py")
    touch("app_retrieval/evaluation/config/__init__.py")
    touch("tests/__init__.py")
    touch("tests/app_retrieval/__init__.py")
    paths = ["app_retrieval/evaluation/config/gold_schema.py", "app_retrieval/evaluation/gold_dataset.py", "app_retrieval/evaluation/golden_test_generator.py", "app_retrieval/evaluation/lancedb_loader.py", "app_retrieval/evaluation/config/sample_gold.jsonl"]
    write(paths[0], GOLD_SCHEMA)
    write(paths[1], GOLD_DATASET)
    write(paths[2], CANDIDATE_GENERATOR)
    write(paths[3], LANCEDB_LOADER)
    write(paths[4], SAMPLE_GOLD_JSONL)
    test = "tests/app_retrieval/test_gold_dataset_v2.py"
    write(test, TESTS)
    run_pytest([test])
    commit(paths + ["app_retrieval/__init__.py", "app_retrieval/evaluation/__init__.py", "app_retrieval/evaluation/config/__init__.py", "tests/__init__.py", "tests/app_retrieval/__init__.py"], [test], COMMIT_MESSAGE)

if __name__ == "__main__":
    main()

