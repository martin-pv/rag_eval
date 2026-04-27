#!/usr/bin/env bash
set -euo pipefail

echo "[folder-search] Starting transfer..."

# ---------------------------------------------------------------------------
# Write app_retrieval/views/folders.py
# If the file already has FolderView with ?q= filter, skip.
# ---------------------------------------------------------------------------
TARGET="app_retrieval/views/folders.py"

if grep -q "folder_name__icontains" "$TARGET" 2>/dev/null; then
    echo "[folder-search] Already patched: $TARGET"
else
    echo "[folder-search] Writing: $TARGET"
    cat > "$TARGET" <<'PYEOF'
import logging

from django.contrib.auth.models import User
from django.db.models import Q
from rest_framework.response import Response
from rest_framework.views import APIView

from app_retrieval.models import Folder

logger = logging.getLogger(__name__)


class FolderView(APIView):
    async def get(self, request, *args, **kwargs):
        user: User = request.user

        folders_qs = Folder.objects.filter(
            Q(data_owner=user) | Q(members=user)
        ).distinct()

        q = request.query_params.get("q", "").strip()
        if q:
            folders_qs = folders_qs.filter(folder_name__icontains=q)

        folders = [
            {
                "id": f.pk,
                "folder_name": f.folder_name,
                "folder_type": f.folder_type,
            }
            async for f in folders_qs
        ]

        return Response({"folders": folders})
PYEOF
fi

# ---------------------------------------------------------------------------
# Write tests
# ---------------------------------------------------------------------------
mkdir -p tests/app_retrieval
touch tests/__init__.py tests/app_retrieval/__init__.py 2>/dev/null || true

TEST_TARGET="tests/app_retrieval/test_folder_search.py"
if [ -f "$TEST_TARGET" ]; then
    echo "[folder-search] Test file already exists: $TEST_TARGET"
else
    echo "[folder-search] Writing: $TEST_TARGET"
    cat > "$TEST_TARGET" <<'PYEOF'
"""
Folder keyword search — TDD tests.
Run: pytest tests/app_retrieval/test_folder_search.py -v
"""
import pytest
from unittest.mock import MagicMock, patch

from app_retrieval.views.folders import FolderView
from rest_framework.test import APIRequestFactory


def _make_folder(pk, folder_name, folder_type="personal"):
    f = MagicMock()
    f.pk = pk
    f.folder_name = folder_name
    f.folder_type = folder_type
    return f


def _make_async_qs(folders):
    async def _aiter():
        for f in folders:
            yield f

    def _filter(**kwargs):
        field, value = None, None
        for k, v in kwargs.items():
            if "icontains" in k:
                field = k.split("__")[0]
                value = v.lower()
        matched = (
            [f for f in folders if value in getattr(f, field, "").lower()]
            if field and value
            else folders
        )

        async def _inner_aiter():
            for f in matched:
                yield f

        inner_qs = MagicMock()
        inner_qs.__aiter__ = MagicMock(return_value=_inner_aiter())
        inner_qs.filter = _filter
        return inner_qs

    qs = MagicMock()
    qs.__aiter__ = MagicMock(return_value=_aiter())
    qs.filter = _filter
    qs.distinct = MagicMock(return_value=qs)
    return qs


factory = APIRequestFactory()


class TestFolderSearch:

    @pytest.mark.asyncio
    async def test_no_query_returns_all_folders(self):
        folders = [_make_folder(1, "Engine SAM"), _make_folder(2, "Airfoil Design")]
        request = factory.get("/ws/folders/")
        request.user = MagicMock()
        with patch("app_retrieval.views.folders.Folder") as MockFolder:
            MockFolder.objects.filter.return_value = _make_async_qs(folders)
            response = await FolderView().get(request)
        names = [f["folder_name"] for f in response.data["folders"]]
        assert "Engine SAM" in names
        assert "Airfoil Design" in names

    @pytest.mark.asyncio
    async def test_query_filters_by_name(self):
        folders = [_make_folder(1, "Engine SAM"), _make_folder(2, "Airfoil Design")]
        request = factory.get("/ws/folders/", {"q": "Engine"})
        request.user = MagicMock()
        with patch("app_retrieval.views.folders.Folder") as MockFolder:
            MockFolder.objects.filter.return_value = _make_async_qs(folders)
            response = await FolderView().get(request)
        names = [f["folder_name"] for f in response.data["folders"]]
        assert "Engine SAM" in names
        assert "Airfoil Design" not in names

    @pytest.mark.asyncio
    async def test_query_is_case_insensitive(self):
        folders = [_make_folder(1, "Engine SAM")]
        request = factory.get("/ws/folders/", {"q": "engine"})
        request.user = MagicMock()
        with patch("app_retrieval.views.folders.Folder") as MockFolder:
            MockFolder.objects.filter.return_value = _make_async_qs(folders)
            response = await FolderView().get(request)
        assert len(response.data["folders"]) == 1

    @pytest.mark.asyncio
    async def test_no_match_returns_empty(self):
        folders = [_make_folder(1, "Engine SAM")]
        request = factory.get("/ws/folders/", {"q": "zzznomatch"})
        request.user = MagicMock()
        with patch("app_retrieval.views.folders.Folder") as MockFolder:
            MockFolder.objects.filter.return_value = _make_async_qs(folders)
            response = await FolderView().get(request)
        assert response.data["folders"] == []

    @pytest.mark.asyncio
    async def test_empty_query_returns_all(self):
        folders = [_make_folder(1, "A"), _make_folder(2, "B")]
        request = factory.get("/ws/folders/", {"q": ""})
        request.user = MagicMock()
        with patch("app_retrieval.views.folders.Folder") as MockFolder:
            MockFolder.objects.filter.return_value = _make_async_qs(folders)
            response = await FolderView().get(request)
        assert len(response.data["folders"]) == 2

    @pytest.mark.asyncio
    async def test_response_has_required_fields(self):
        folders = [_make_folder(7, "Test Folder", "shared")]
        request = factory.get("/ws/folders/")
        request.user = MagicMock()
        with patch("app_retrieval.views.folders.Folder") as MockFolder:
            MockFolder.objects.filter.return_value = _make_async_qs(folders)
            response = await FolderView().get(request)
        folder = response.data["folders"][0]
        assert folder["id"] == 7
        assert folder["folder_name"] == "Test Folder"
        assert folder["folder_type"] == "shared"
PYEOF
fi

echo ""
echo "[folder-search] Done."
echo ""
echo "Verify:"
echo "  pytest tests/app_retrieval/test_folder_search.py -v"
echo ""
echo "Expected: 6 tests pass"
echo "Manual: GET /ws/folders/?q=engine → only folders with 'engine' in name"
