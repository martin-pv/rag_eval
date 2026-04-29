#!/usr/bin/env python3
"""NGAIP-362 transfer: RAGAS-primary gold dataset and testset generation."""
import subprocess
from pathlib import Path

BRANCH = 'ngaip-362-corpus-gold-dataset'
COMMIT_MESSAGE = 'NGAIP-362: Apply transfer script changes'
BASE_BRANCH = "main-backup-for-mac-claude-repo-04-07-2026"
BACKEND = Path.cwd()


def git(*args):
    subprocess.run(["git", *args], check=True)


def git_or(*args):
    return subprocess.run(["git", *args], check=False).returncode == 0


def current_branch() -> str:
    return subprocess.check_output(["git", "branch", "--show-current"], text=True).strip()


def ensure_ticket_branch() -> None:
    print(f"[362-transfer] Preparing branch: {BRANCH} from local {BASE_BRANCH}")
    if current_branch() == BRANCH:
        print(f"[362-transfer] Already on ticket branch: {BRANCH}")
        return
    if git_or("rev-parse", "--verify", f"refs/heads/{BRANCH}"):
        git("switch", BRANCH)
        return
    git("switch", BASE_BRANCH)
    git("switch", "-c", BRANCH)


def ensure(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"  Created: {path}")


def touch(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.touch()
        print(f"  Touched: {path}")
    else:
        print(f"  Already exists: {path}")


def read_text_compat(path: Path) -> str:
    if not path.exists():
        return ""
    raw = path.read_bytes()
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        return raw.decode("utf-16")
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw.decode("utf-8-sig")
    for encoding in ("utf-8", "utf-16-le", "cp1252", "latin-1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            pass
    return raw.decode("latin-1")


def append_if_missing(path: Path, line: str):
    text = read_text_compat(path)
    addition = line if line.endswith("\n") else line + "\n"
    if line.rstrip() not in text:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(addition if not text else text + ("" if text.endswith("\n") else "\n") + addition, encoding="utf-8")
        print(f"  Appended: {line.strip()}")
    else:
        print(f"  Already present: {line.strip()}")


def remove_obsolete_generated_files() -> None:
    if OBSOLETE_PATHS:
        git("rm", "--ignore-unmatch", "--", *OBSOLETE_PATHS)


def commit_transfer_changes() -> None:
    existing_paths = [p for p in GENERATED_PATHS if (BACKEND / p).exists()]
    commit_paths = sorted(set(existing_paths + OBSOLETE_PATHS))
    normal_paths = [p for p in existing_paths if not p.startswith("tests/")]
    test_paths = [p for p in existing_paths if p.startswith("tests/")]
    if normal_paths:
        git("add", "--", *normal_paths)
    if test_paths:
        print(f"[362-transfer] Force-adding generated test files...")
        git("add", "-f", "--", *test_paths)
    staged = subprocess.run(["git", "diff", "--cached", "--quiet", "--", *commit_paths], check=False)
    if staged.returncode == 0:
        print(f"[362-transfer] No changes to commit.")
        return
    git("commit", "-m", COMMIT_MESSAGE, "--", *commit_paths)
    print(f"[362-transfer] Created local commit: {COMMIT_MESSAGE}")

GENERATED_PATHS = ['requirements.txt', 'app_retrieval/evaluation/__init__.py', 'app_retrieval/evaluation/config/__init__.py', 'app_retrieval/evaluation/config/gold_schema.py', 'app_retrieval/evaluation/config/gold_schema.md', 'app_retrieval/evaluation/config/ci_gold.jsonl', 'app_retrieval/evaluation/gold_dataset.py', 'app_retrieval/evaluation/golden_test_generator.py', 'tests/app_retrieval/__init__.py', 'tests/app_retrieval/test_gold_dataset_generation.py']
OBSOLETE_PATHS = ['app_retrieval/evaluation/gold_loader.py', 'tests/app_retrieval/test_gold_loader.py']


def main():
    ensure_ticket_branch()
    for dep in ["ragas>=0.2.0", "datasets>=2.14.0", "lancedb", "langchain-core==0.3.21", "langchain-openai==0.2.11", "langchain-community==0.3.4", "langchain==0.3.10"]:
        append_if_missing(BACKEND / "requirements.txt", dep)
    for init in [BACKEND / "app_retrieval" / "evaluation" / "__init__.py", BACKEND / "app_retrieval" / "evaluation" / "config" / "__init__.py", BACKEND / "tests" / "app_retrieval" / "__init__.py"]:
        touch(init)
    remove_obsolete_generated_files()
    ensure(BACKEND / "app_retrieval" / "evaluation" / "config" / "gold_schema.py", 'from __future__ import annotations\n\nfrom typing import Any, Literal\n\nfrom pydantic import BaseModel, ConfigDict, Field, model_validator\n\n\nclass GoldRow(BaseModel):\n    """Validated gold row with RAGAS-native fields plus PrattWise source metadata."""\n\n    model_config = ConfigDict(extra="forbid")\n\n    question_id: str\n    question: str\n    gold_answer: str = Field(description="Reference answer; maps to RAGAS `reference`.")\n    gold_doc_id: str\n    gold_span_start: int | None = None\n    gold_span_end: int | None = None\n    gold_chunk_ids: list[str] | None = None\n    reference_contexts: list[str] | None = None\n    difficulty: Literal["easy", "medium", "hard"] | None = None\n    tags: list[str] | None = None\n    synthesizer_name: str | None = None\n    ragas_metadata: dict[str, Any] | None = None\n\n    @model_validator(mode="after")\n    def _validate_span(self) -> "GoldRow":\n        if self.gold_span_start is not None and self.gold_span_end is not None:\n            if self.gold_span_end <= self.gold_span_start:\n                raise ValueError("gold_span_end must be greater than gold_span_start")\n        return self\n\n    def to_ragas_sample(self, answer: str | None = None, contexts: list[str] | None = None) -> dict[str, Any]:\n        retrieved_contexts = contexts or self.reference_contexts or []\n        response = answer or self.gold_answer\n        return {\n            "user_input": self.question,\n            "response": response,\n            "retrieved_contexts": retrieved_contexts,\n            "reference": self.gold_answer,\n            "question": self.question,\n            "answer": response,\n            "contexts": retrieved_contexts,\n            "ground_truth": self.gold_answer,\n        }\n')
    ensure(BACKEND / "app_retrieval" / "evaluation" / "config" / "gold_schema.md", "Gold rows are RAGAS-native: question -> user_input, gold_answer -> reference, reference_contexts -> contexts. PrattWise ids/spans are supplemental metadata.\n")
    ensure(BACKEND / "app_retrieval" / "evaluation" / "config" / "ci_gold.jsonl", '{"question_id":"ci-001","question":"What is the maintenance interval for component X?","gold_answer":"Component X requires maintenance every 500 flight hours.","gold_doc_id":"ci-asset-001","reference_contexts":["Component X requires maintenance every 500 flight hours."],"difficulty":"easy","tags":["maintenance"]}\n')
    ensure(BACKEND / "app_retrieval" / "evaluation" / "gold_dataset.py", 'from __future__ import annotations\n\nimport json\nfrom pathlib import Path\nfrom typing import Iterable\n\nfrom app_retrieval.evaluation.config.gold_schema import GoldRow\n\n\ndef load_gold_file(path: str | Path) -> list[GoldRow]:\n    rows: list[GoldRow] = []\n    with Path(path).open(encoding="utf-8") as handle:\n        for line_number, line in enumerate(handle, start=1):\n            line = line.strip()\n            if not line:\n                continue\n            try:\n                rows.append(GoldRow.model_validate_json(line))\n            except Exception as exc:\n                raise ValueError(f"Invalid gold row at line {line_number}: {exc}") from exc\n    return rows\n\n\ndef to_ragas_rows(rows: Iterable[GoldRow], answers_by_id: dict[str, str] | None = None, contexts_by_id: dict[str, list[str]] | None = None) -> list[dict]:\n    answers_by_id = answers_by_id or {}\n    contexts_by_id = contexts_by_id or {}\n    return [row.to_ragas_sample(answer=answers_by_id.get(row.question_id), contexts=contexts_by_id.get(row.question_id)) for row in rows]\n\n\ndef to_ragas_dataset(rows: Iterable[GoldRow], answers_by_id: dict[str, str] | None = None, contexts_by_id: dict[str, list[str]] | None = None):\n    from datasets import Dataset\n\n    return Dataset.from_list(to_ragas_rows(rows, answers_by_id=answers_by_id, contexts_by_id=contexts_by_id))\n\n\ndef promote_candidates_to_gold(candidates_path: str | Path, gold_path: str | Path, approved_ids: set[str] | None = None) -> int:\n    promoted: list[GoldRow] = []\n    for line_number, line in enumerate(Path(candidates_path).read_text(encoding="utf-8").splitlines(), start=1):\n        if not line.strip():\n            continue\n        data = json.loads(line)\n        if approved_ids is not None and data.get("question_id") not in approved_ids:\n            continue\n        try:\n            promoted.append(GoldRow.model_validate(data))\n        except Exception as exc:\n            raise ValueError(f"Invalid candidate row at line {line_number}: {exc}") from exc\n    out = Path(gold_path)\n    out.parent.mkdir(parents=True, exist_ok=True)\n    with out.open("a", encoding="utf-8") as handle:\n        for row in promoted:\n            handle.write(row.model_dump_json(exclude_none=True) + "\\n")\n    return len(promoted)\n')
    ensure(BACKEND / "app_retrieval" / "evaluation" / "golden_test_generator.py", 'from __future__ import annotations\n\nimport json\nfrom importlib.metadata import PackageNotFoundError, version\nfrom pathlib import Path\nfrom typing import Any, Iterable, Sequence\n\nfrom langchain_core.documents import Document\n\n\ndef ragas_version() -> str:\n    try:\n        return version("ragas")\n    except PackageNotFoundError:\n        return "unknown"\n\n\ndef load_langchain_documents(path: str | Path) -> list[Document]:\n    docs: list[Document] = []\n    for line in Path(path).read_text(encoding="utf-8").splitlines():\n        if not line.strip():\n            continue\n        data = json.loads(line)\n        docs.append(Document(page_content=data.get("page_content") or data.get("text") or "", metadata=data.get("metadata", {})))\n    return docs\n\n\ndef load_lancedb_documents(db_path: str | Path, table_name: str, text_field: str = "text", limit: int | None = None) -> list[Document]:\n    import lancedb\n\n    rows = lancedb.connect(str(db_path)).open_table(table_name).to_arrow().to_pylist()\n    if limit is not None:\n        rows = rows[:limit]\n    return [Document(page_content=str(row.get(text_field, "")), metadata={k: v for k, v in row.items() if k != text_field}) for row in rows]\n\n\ndef serialize_knowledge_graph_context(kg_rows: Iterable[dict[str, Any]]) -> str:\n    facts = []\n    for row in kg_rows:\n        subject = row.get("subject") or row.get("source") or row.get("from")\n        relation = row.get("relation") or row.get("edge") or row.get("predicate")\n        obj = row.get("object") or row.get("target") or row.get("to")\n        if subject and relation and obj:\n            facts.append(f"{subject} --{relation}--> {obj}")\n    return "\\n".join(facts)\n\n\ndef attach_knowledge_graph_context(documents: Sequence[Document], kg_context: str) -> list[Document]:\n    if not kg_context:\n        return list(documents)\n    return [Document(page_content=f"{doc.page_content}\\n\\nKnowledge graph context:\\n{kg_context}", metadata={**doc.metadata, "knowledge_graph_context_attached": True}) for doc in documents]\n\n\ndef _testset_generator(llm=None, embedding_model=None):\n    try:\n        from ragas.testset import TestsetGenerator\n    except ImportError:\n        from ragas.testset.generator import TestsetGenerator\n    if llm is not None and embedding_model is not None and hasattr(TestsetGenerator, "from_langchain"):\n        return TestsetGenerator.from_langchain(generator_llm=llm, critic_llm=llm, embeddings=embedding_model)\n    return TestsetGenerator\n\n\ndef generate_candidate_testset(documents: Sequence[Document], test_size: int, llm=None, embedding_model=None, distributions: dict | None = None):\n    generator = _testset_generator(llm=llm, embedding_model=embedding_model)\n    if hasattr(generator, "generate_with_langchain_docs"):\n        return generator.generate_with_langchain_docs(list(documents), test_size=test_size, distributions=distributions)\n    if hasattr(generator, "generate"):\n        return generator.generate(list(documents), test_size=test_size, distributions=distributions)\n    raise TypeError("Installed RAGAS TestsetGenerator does not expose a supported generate method")\n\n\ndef normalize_ragas_testset(testset, documents: Sequence[Document]) -> list[dict[str, Any]]:\n    if hasattr(testset, "to_pandas"):\n        raw_rows = testset.to_pandas().to_dict(orient="records")\n    elif hasattr(testset, "to_dataset"):\n        raw_rows = list(testset.to_dataset())\n    else:\n        raw_rows = list(testset)\n    normalized = []\n    for index, row in enumerate(raw_rows, start=1):\n        doc = documents[(index - 1) % len(documents)] if documents else Document(page_content="", metadata={})\n        normalized.append({\n            "question_id": row.get("question_id") or f"ragas-candidate-{index:04d}",\n            "question": row.get("question") or row.get("user_input") or row.get("query"),\n            "gold_answer": row.get("ground_truth") or row.get("reference") or row.get("answer"),\n            "gold_doc_id": str(doc.metadata.get("asset_id") or doc.metadata.get("doc_id") or "unknown"),\n            "reference_contexts": row.get("contexts") or row.get("retrieved_contexts") or [doc.page_content],\n            "difficulty": row.get("difficulty"),\n            "tags": row.get("tags") or ["ragas-generated"],\n            "synthesizer_name": row.get("synthesizer_name") or row.get("evolution_type"),\n            "ragas_metadata": {"framework": "ragas", "ragas_version": ragas_version(), "raw": row},\n        })\n    return normalized\n\n\ndef generate_golden_candidates(documents: Sequence[Document], output_path: str | Path, test_size: int, llm=None, embedding_model=None, kg_rows: Iterable[dict[str, Any]] | None = None) -> list[dict[str, Any]]:\n    docs = attach_knowledge_graph_context(documents, serialize_knowledge_graph_context(kg_rows or []))\n    rows = normalize_ragas_testset(generate_candidate_testset(docs, test_size=test_size, llm=llm, embedding_model=embedding_model), docs)\n    path = Path(output_path)\n    path.parent.mkdir(parents=True, exist_ok=True)\n    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\\n" for row in rows), encoding="utf-8")\n    return rows\n')
    ensure(BACKEND / "tests" / "app_retrieval" / "test_gold_dataset_generation.py", 'from __future__ import annotations\n\nimport json\nfrom pathlib import Path\n\nfrom langchain_core.documents import Document\n\nfrom app_retrieval.evaluation.config.gold_schema import GoldRow\nfrom app_retrieval.evaluation.gold_dataset import load_gold_file, to_ragas_rows\nfrom app_retrieval.evaluation.golden_test_generator import attach_knowledge_graph_context, normalize_ragas_testset, serialize_knowledge_graph_context\n\n\ndef test_gold_row_exports_ragas_sample():\n    row = GoldRow(question_id="q1", question="Q?", gold_answer="A", gold_doc_id="doc", reference_contexts=["ctx"])\n    sample = row.to_ragas_sample()\n    assert sample["user_input"] == "Q?"\n    assert sample["reference"] == "A"\n    assert sample["retrieved_contexts"] == ["ctx"]\n\n\ndef test_load_gold_file_validates_rows(tmp_path: Path):\n    path = tmp_path / "gold.jsonl"\n    path.write_text(json.dumps({"question_id": "q1", "question": "Q?", "gold_answer": "A", "gold_doc_id": "doc"}) + "\\n")\n    assert load_gold_file(path)[0].question_id == "q1"\n\n\ndef test_to_ragas_rows_uses_model_answer_and_contexts():\n    rows = [GoldRow(question_id="q1", question="Q?", gold_answer="Gold", gold_doc_id="doc")]\n    ragas_rows = to_ragas_rows(rows, answers_by_id={"q1": "Model"}, contexts_by_id={"q1": ["ctx"]})\n    assert ragas_rows[0]["response"] == "Model"\n    assert ragas_rows[0]["retrieved_contexts"] == ["ctx"]\n\n\ndef test_knowledge_graph_context_attaches_to_documents():\n    kg = serialize_knowledge_graph_context([{"subject": "A", "relation": "uses", "object": "B"}])\n    docs = attach_knowledge_graph_context([Document(page_content="Base", metadata={"asset_id": "doc"})], kg)\n    assert "A --uses--> B" in docs[0].page_content\n    assert docs[0].metadata["knowledge_graph_context_attached"] is True\n\n\ndef test_normalize_ragas_testset_outputs_gold_candidate_shape():\n    rows = normalize_ragas_testset([{"question": "Q?", "ground_truth": "A", "contexts": ["ctx"], "evolution_type": "simple"}], [Document(page_content="ctx", metadata={"asset_id": "doc-1"})])\n    assert rows[0]["question_id"].startswith("ragas-candidate-")\n    assert rows[0]["gold_answer"] == "A"\n    assert rows[0]["gold_doc_id"] == "doc-1"\n    assert rows[0]["ragas_metadata"]["framework"] == "ragas"\n')
    commit_transfer_changes()
    print("[362-transfer] Done. Verify with: pytest tests/app_retrieval/test_gold_dataset_generation.py -v")


if __name__ == "__main__":
    main()
