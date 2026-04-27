#!/usr/bin/env bash
set -euo pipefail

echo "[ZH-62] Starting transfer..."

# ---------------------------------------------------------------------------
# Patch 1 — Add _normalize_scores + hybrid_search_folder to views/search.py
# ---------------------------------------------------------------------------
python3 - <<'PYEOF'
import sys

path = "app_retrieval/views/search.py"
try:
    with open(path) as f:
        content = f.read()
except FileNotFoundError:
    print(f"[ZH-62] ERROR: {path} not found. Run from ENCHS-PW-GenAI-Backend/ root.")
    sys.exit(1)

if "hybrid_search_folder" in content:
    print("[ZH-62] Already patched (hybrid_search_folder): " + path)
    sys.exit(0)

insertion = """

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
    \\"\\"\\"Merge semantic + keyword results, normalize scores, dedupe by (asset_id, start_lab).\\"\\"\\"
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
"""

if "async def chunk_reranking" in content:
    content = content.replace("async def chunk_reranking", insertion + "\nasync def chunk_reranking", 1)
else:
    content = content.rstrip() + "\n" + insertion + "\n"

with open(path, "w") as f:
    f.write(content)
print("[ZH-62] Patched (hybrid_search_folder): " + path)
PYEOF

# ---------------------------------------------------------------------------
# Patch 2 — Ensure views_search.py imports hybrid_search_folder
# ---------------------------------------------------------------------------
python3 - <<'PYEOF'
import sys, re

path = "app_retrieval/views_search.py"
try:
    with open(path) as f:
        content = f.read()
except FileNotFoundError:
    print(f"[ZH-62] ERROR: {path} not found.")
    sys.exit(1)

if "hybrid_search_folder" in content:
    print("[ZH-62] hybrid_search_folder already present in: " + path)
    sys.exit(0)

existing = re.search(r"(from app_retrieval\.views\.search import[^\n]+)", content)
if existing:
    content = content.replace(existing.group(1), existing.group(1) + ", hybrid_search_folder", 1)
else:
    content = "from app_retrieval.views.search import hybrid_search_folder\n" + content

with open(path, "w") as f:
    f.write(content)
print("[ZH-62] Patched (import): " + path)
PYEOF

# ---------------------------------------------------------------------------
# Write tests
# ---------------------------------------------------------------------------
mkdir -p tests/app_retrieval
touch tests/__init__.py tests/app_retrieval/__init__.py 2>/dev/null || true

TEST="tests/app_retrieval/test_hybrid_search.py"
if [ -f "$TEST" ]; then
    echo "[ZH-62] Test file already exists: $TEST"
else
    python3 - <<'PYEOF'
content = '''"""Tests for ZH-62 hybrid RAG routing.

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
with open("tests/app_retrieval/test_hybrid_search.py", "w") as f:
    f.write(content)
print("[ZH-62] Wrote: tests/app_retrieval/test_hybrid_search.py")
PYEOF
fi

echo ""
echo "[ZH-62] Done."
echo "Unit tests (no DB): pytest tests/app_retrieval/test_hybrid_search.py -v -m 'not integration'"
echo "All tests:          pytest tests/app_retrieval/test_hybrid_search.py -v"
echo "Manual:             GET /ws/search/folders/<pk>/?search_query=engine&keyword_search=hybrid"
