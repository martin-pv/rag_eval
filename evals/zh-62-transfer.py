#!/usr/bin/env python3
"""ZH-62 Transfer Script — cross-platform (Windows/macOS/Linux)

Ticket: Hybrid keyword / semantic RAG routing

What this does:
  1. Patches app_retrieval/views/search.py
     - adds _normalize_scores() + hybrid_search_folder() before chunk_reranking
       (or appends to end if chunk_reranking not found)
  2. Patches app_retrieval/views_search.py
     - ensures hybrid_search_folder is imported
  3. Creates tests/app_retrieval/test_hybrid_search.py (new file)

Usage: python zh-62-transfer.py  (run from ENCHS-PW-GenAI-Backend/ root)
Idempotent: safe to run multiple times.
"""
import re
import subprocess
import sys
from pathlib import Path

BRANCH = "zh-62-hybrid-rag"
BACKEND = Path.cwd()

SEARCH_PY = BACKEND / "app_retrieval" / "views" / "search.py"
VIEWS_SEARCH_PY = BACKEND / "app_retrieval" / "views_search.py"
TESTS_DIR = BACKEND / "tests" / "app_retrieval"
TEST_FILE = TESTS_DIR / "test_hybrid_search.py"


def git(*args):
    subprocess.run(["git", *args], check=True)


def git_or(*args):
    """Run git command, return True if succeeded."""
    return subprocess.run(["git", *args]).returncode == 0


def patch_search_py():
    """Add _normalize_scores + hybrid_search_folder to views/search.py."""
    if not SEARCH_PY.exists():
        print(f"[ZH-62] ERROR: {SEARCH_PY} not found. Run from ENCHS-PW-GenAI-Backend/ root.")
        sys.exit(1)

    content = SEARCH_PY.read_text(encoding="utf-8")

    if "hybrid_search_folder" in content:
        print(f"[ZH-62] Already patched (hybrid_search_folder): {SEARCH_PY}")
        return

    insertion = '''

def _normalize_scores(results: list[dict]) -> list[dict]:
    if not results:
        return []
    scores = [r.get("score", 0) for r in results]
    max_s, min_s = max(scores), min(scores)
    if max_s == min_s:
        return [{**r, "_norm_score": 1.0} for r in results]
    rng = max_s - min_s
    return [{**r, "_norm_score": (r.get("score", 0) - min_s) / rng} for r in results]


async def hybrid_search_folder(request, search_query: str, folder, top_k: int = 5) -> list[dict]:
    """Merge semantic + keyword results, normalize scores, dedupe by (asset_id, start_lab)."""
    import asyncio
    semantic, keyword = await asyncio.gather(
        search_folder(request, search_query, folder, target_total_k_results=top_k),
        keyword_search_folder(request, search_query, folder, k=top_k),
    )
    merged: dict = {}
    for result in _normalize_scores(keyword):
        key = (result.get("asset_id"), result.get("start_lab"))
        merged[key] = result
    for result in _normalize_scores(semantic):
        key = (result.get("asset_id"), result.get("start_lab"))
        if key in merged:
            merged[key]["_norm_score"] = max(merged[key]["_norm_score"], result["_norm_score"])
        else:
            merged[key] = result
    return sorted(merged.values(), key=lambda x: x["_norm_score"], reverse=True)[:top_k]
'''

    if "async def chunk_reranking" in content:
        content = content.replace(
            "async def chunk_reranking",
            insertion + "\nasync def chunk_reranking",
            1,
        )
    else:
        content = content.rstrip() + "\n" + insertion + "\n"

    SEARCH_PY.write_text(content, encoding="utf-8")
    print(f"[ZH-62] Patched (hybrid_search_folder): {SEARCH_PY}")


def patch_views_search_py():
    """Ensure views_search.py imports hybrid_search_folder."""
    if not VIEWS_SEARCH_PY.exists():
        print(f"[ZH-62] ERROR: {VIEWS_SEARCH_PY} not found.")
        sys.exit(1)

    content = VIEWS_SEARCH_PY.read_text(encoding="utf-8")

    if "hybrid_search_folder" in content:
        print(f"[ZH-62] hybrid_search_folder already present in: {VIEWS_SEARCH_PY}")
        return

    existing = re.search(r"(from app_retrieval\.views\.search import[^\n]+)", content)
    if existing:
        content = content.replace(
            existing.group(1),
            existing.group(1) + ", hybrid_search_folder",
            1,
        )
    else:
        content = "from app_retrieval.views.search import hybrid_search_folder\n" + content

    VIEWS_SEARCH_PY.write_text(content, encoding="utf-8")
    print(f"[ZH-62] Patched (import): {VIEWS_SEARCH_PY}")


def write_test_file():
    """Create tests/app_retrieval/test_hybrid_search.py."""
    TESTS_DIR.mkdir(parents=True, exist_ok=True)

    tests_init = BACKEND / "tests" / "__init__.py"
    retrieval_init = TESTS_DIR / "__init__.py"
    for init in (tests_init, retrieval_init):
        if not init.exists():
            init.touch()

    if TEST_FILE.exists():
        print(f"[ZH-62] Test file already exists: {TEST_FILE}")
        return

    content = r'''"""Tests for ZH-62 hybrid RAG routing.

Run unit tests (no DB):
    pytest tests/app_retrieval/test_hybrid_search.py -v -m "not integration"
"""
from __future__ import annotations
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from app_retrieval.views.search import _normalize_scores


class TestNormalizeScores:
    def test_empty(self): assert _normalize_scores([]) == []
    def test_single_gets_one(self):
        assert _normalize_scores([{"score": 0.4}])[0]["_norm_score"] == 1.0
    def test_range(self):
        out = _normalize_scores([{"score": 0.0}, {"score": 1.0}])
        scores = [r["_norm_score"] for r in out]
        assert min(scores) == pytest.approx(0.0) and max(scores) == pytest.approx(1.0)
    def test_equal_scores_get_one(self):
        out = _normalize_scores([{"score": 0.5}, {"score": 0.5}])
        assert all(r["_norm_score"] == 1.0 for r in out)
    def test_original_score_preserved(self):
        out = _normalize_scores([{"score": 0.8}])
        assert out[0]["score"] == 0.8


class TestHybridSearchFolder:
    def _r(self, aid, slab, score):
        return {"asset_id": aid, "start_lab": slab, "score": score, "content": "x", "file_name": "f.pdf"}

    @pytest.mark.asyncio
    async def test_combines_both_paths(self):
        sem = [self._r(1, 0, 0.9), self._r(2, 0, 0.7)]
        kw = [self._r(3, 0, 0.8)]
        with (
            patch("app_retrieval.views.search.search_folder", new=AsyncMock(return_value=sem)),
            patch("app_retrieval.views.search.keyword_search_folder", new=AsyncMock(return_value=kw)),
        ):
            from app_retrieval.views.search import hybrid_search_folder
            results = await hybrid_search_folder(MagicMock(), "q", MagicMock(), top_k=5)
        assert {r["asset_id"] for r in results} == {1, 2, 3}

    @pytest.mark.asyncio
    async def test_dedupes_same_chunk(self):
        with (
            patch("app_retrieval.views.search.search_folder", new=AsyncMock(return_value=[self._r(1, 100, 0.9)])),
            patch("app_retrieval.views.search.keyword_search_folder", new=AsyncMock(return_value=[self._r(1, 100, 0.6)])),
        ):
            from app_retrieval.views.search import hybrid_search_folder
            results = await hybrid_search_folder(MagicMock(), "q", MagicMock(), top_k=10)
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_sorted_descending(self):
        sem = [self._r(1, 0, 0.3), self._r(2, 0, 0.9)]
        kw = [self._r(3, 0, 0.6)]
        with (
            patch("app_retrieval.views.search.search_folder", new=AsyncMock(return_value=sem)),
            patch("app_retrieval.views.search.keyword_search_folder", new=AsyncMock(return_value=kw)),
        ):
            from app_retrieval.views.search import hybrid_search_folder
            results = await hybrid_search_folder(MagicMock(), "q", MagicMock(), top_k=10)
        ns = [r["_norm_score"] for r in results]
        assert ns == sorted(ns, reverse=True)

    @pytest.mark.asyncio
    async def test_top_k_respected(self):
        sem = [self._r(i, 0, i/10) for i in range(1, 8)]
        kw = [self._r(i, 100, i/10) for i in range(8, 15)]
        with (
            patch("app_retrieval.views.search.search_folder", new=AsyncMock(return_value=sem)),
            patch("app_retrieval.views.search.keyword_search_folder", new=AsyncMock(return_value=kw)),
        ):
            from app_retrieval.views.search import hybrid_search_folder
            results = await hybrid_search_folder(MagicMock(), "q", MagicMock(), top_k=5)
        assert len(results) == 5

    @pytest.mark.asyncio
    async def test_empty_both_paths(self):
        with (
            patch("app_retrieval.views.search.search_folder", new=AsyncMock(return_value=[])),
            patch("app_retrieval.views.search.keyword_search_folder", new=AsyncMock(return_value=[])),
        ):
            from app_retrieval.views.search import hybrid_search_folder
            results = await hybrid_search_folder(MagicMock(), "q", MagicMock(), top_k=5)
        assert results == []

    @pytest.mark.asyncio
    async def test_no_duplicate_keys(self):
        sem = [self._r(1, 0, 0.8), self._r(1, 100, 0.6)]
        kw = [self._r(1, 0, 0.5), self._r(2, 0, 0.9)]
        with (
            patch("app_retrieval.views.search.search_folder", new=AsyncMock(return_value=sem)),
            patch("app_retrieval.views.search.keyword_search_folder", new=AsyncMock(return_value=kw)),
        ):
            from app_retrieval.views.search import hybrid_search_folder
            results = await hybrid_search_folder(MagicMock(), "q", MagicMock(), top_k=10)
        keys = [(r["asset_id"], r.get("start_lab")) for r in results]
        assert len(keys) == len(set(keys))


@pytest.mark.integration
class TestHybridIntegration:
    @pytest.mark.asyncio
    async def test_returns_results(self, folder_with_chunks):
        from app_retrieval.views.search import hybrid_search_folder
        results = await hybrid_search_folder(MagicMock(), "engine", folder_with_chunks, top_k=5)
        assert len(results) > 0 and all("content" in r for r in results)

    @pytest.mark.asyncio
    async def test_no_duplicate_keys(self, folder_with_chunks):
        from app_retrieval.views.search import hybrid_search_folder
        results = await hybrid_search_folder(MagicMock(), "test", folder_with_chunks, top_k=10)
        keys = [(r.get("asset_id"), r.get("start_lab")) for r in results]
        assert len(keys) == len(set(keys))
'''
    TEST_FILE.write_text(content, encoding="utf-8")
    print(f"[ZH-62] Wrote: {TEST_FILE}")


def main():
    print("[ZH-62] Starting transfer...")

    # Note: zh-62 runs from ENCHS-PW-GenAI-Backend/ root (no BACKEND prefix needed for git).
    # Git branch ops still apply.
    if not git_or("checkout", "-b", BRANCH):
        git("checkout", BRANCH)

    patch_search_py()
    patch_views_search_py()
    write_test_file()

    print()
    print("[ZH-62] Done.")
    print("Unit tests (no DB): pytest tests/app_retrieval/test_hybrid_search.py -v -m 'not integration'")
    print("All tests:          pytest tests/app_retrieval/test_hybrid_search.py -v")
    print("Manual:             GET /ws/search/folders/<pk>/?search_query=engine&keyword_search=hybrid")


if __name__ == "__main__":
    main()
