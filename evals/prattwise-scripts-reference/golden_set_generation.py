from __future__ import annotations

from collections.abc import Sequence
from importlib.metadata import version
from langchain_openai import OpenAIEmbeddings, OpenAI
from pydantic.types import SecretStr
from langchain_core.documents import Document
import glob
import os
from pathlib import Path
from util.pdf_reader import pdf_read_text
from dotenv import load_dotenv


load_dotenv()

llm = OpenAI(
    model=os.getenv("OPENAI_API_MODEL", ""),
    temperature=0,
    max_retries=1,
)

embeddings = OpenAIEmbeddings(
    model=os.getenv("OPENAI_API_EMBEDDINGS_DEPLOYMENT", ""),
    base_url=os.getenv("OPENAI_API_EMBEDDINGS_ENDPOINT", ""),
)

FILE_DIR = Path("data", "golden_dataset", "*.pdf")
files = glob.glob(str(FILE_DIR))
docs = [pdf_read_text(f) for f in files]
documents = [Document(page_content=text) for text in docs]


def _ragas_version() -> str:
    try:
        return version("ragas")
    except Exception:
        return "unknown"


def generate_candidate_testset(
    *,
    size: int,
    knowledge_graph=None,
    llm_context: str | None = None,
) -> list[dict]:
    """Generate candidate QA/reference rows with RAGAS."""
    global llm, embeddings, documents

    try:
        from ragas.testset import TestsetGenerator
    except ImportError:
        from ragas.testset.generator import TestsetGenerator

    generator = TestsetGenerator.from_langchain(
        llm=llm,
        embedding_model=embeddings,
        knowledge_graph=knowledge_graph,
        llm_context=llm_context,
    )
    testset = generator.generate_with_langchain_docs(
        documents,
        testset_size=size,
    )
    return normalize_ragas_testset(testset, documents)


def normalize_ragas_testset(testset, documents: Sequence[Document]) -> list[dict]:
    """Convert RAGAS output into candidate rows.

    The exact RAGAS object shape can vary by version, so keep normalization here.
    """
    if hasattr(testset, "to_pandas"):
        records = testset.to_pandas().to_dict(orient="records")
    elif hasattr(testset, "to_list"):
        records = testset.to_list()
    else:
        records = list(testset)

    source_metadata = [doc.metadata for doc in documents]
    rows: list[dict] = []
    for index, record in enumerate(records, start=1):
        rows.append(
            {
                "candidate_id": f"candidate-{index:04d}",
                "question": record.get("question") or record.get("user_input"),
                "reference_answer": record.get("ground_truth") or record.get("reference"),
                "supporting_context": record.get("contexts") or record.get("reference_contexts"),
                "source_metadata": source_metadata,
                "review_status": "candidate",
                "generator": {
                    "framework": "ragas",
                    "ragas_version": _ragas_version(),
                },
            }
        )

    return rows


if __name__ == "__main__":
    generate_candidate_testset(size=10)


# PROMOTABLE_STATUSES = ("approved", "edited")
# def promote_candidates_to_gold(
#     candidate_path: Path,
#     gold_path: Path,
# ) -> list[GoldRow]:
#     """Promote reviewed RAGAS-generated candidates into the official gold set."""
