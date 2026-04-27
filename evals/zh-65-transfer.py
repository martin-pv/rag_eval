#!/usr/bin/env python3
"""
zh-65-transfer.py -- ZH-65: Deduplicate Folders / Fix exists() Bug
Run from root of ENCHS-PW-GenAI-Backend/ (where manage.py lives).
Idempotent: safe to run multiple times.

Cross-platform equivalent of zh-65-transfer.sh (Windows/macOS/Linux).
"""

import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def ensure(path: Path, content: str) -> None:
    """Write content to path, creating parent directories as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def touch(path: Path) -> None:
    """Create path (and parents) if it doesn't exist."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch()


# ---------------------------------------------------------------------------
# Pre-flight
# ---------------------------------------------------------------------------

print("[ZH-65] Applying fixes to assets_search/api_folders.py...")

TARGET = Path("app_extensions/extensions_standard/assets_search/api_folders.py")
if not TARGET.is_file():
    print(f"[ZH-65] ERROR: {TARGET} not found. Run from ENCHS-PW-GenAI-Backend/ root.")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Patch 1 — Fix Bug 1: exists() == 0 inverted condition
# Before: if not folders.exists() == 0:
# After:  if not folders.exists():
# ---------------------------------------------------------------------------

content = TARGET.read_text(encoding="utf-8")

if "if not folders.exists():\n" in content and "== 0" not in content:
    print(f"[ZH-65] Already patched (exists fix): {TARGET}")
else:
    old_1 = (
        '    if not folders.exists() == 0:\n'
        '        raise Exception("No valid folders were passed into folder_ids")\n'
    )
    new_1 = (
        '    if not folders.exists():\n'
        '        raise Exception("No valid folders were passed into folder_ids")\n'
    )

    if old_1 not in content:
        print("[ZH-65] ERROR: exists() anchor not found. File may have diverged.")
        sys.exit(1)

    if content.count(old_1) > 1:
        print("[ZH-65] ERROR: exists() anchor is not unique.")
        sys.exit(1)

    content = content.replace(old_1, new_1, 1)
    TARGET.write_text(content, encoding="utf-8")
    print(f"[ZH-65] Patched (exists fix): {TARGET}")

# ---------------------------------------------------------------------------
# Patch 2 — Fix Bug 2: dedup folder names by pk in get_description
# Before: folder_names = [f.folder_name async for f in folders]
# After:  seen_pks + explicit loop
# ---------------------------------------------------------------------------

content = TARGET.read_text(encoding="utf-8")

if "seen_pks = set()" in content:
    print(f"[ZH-65] Already patched (dedup fix): {TARGET}")
else:
    old_2 = "    folder_names = [f.folder_name async for f in folders]\n"
    new_2 = (
        "    seen_pks = set()\n"
        "    folder_names = []\n"
        "    async for f in folders:\n"
        "        if f.pk not in seen_pks:\n"
        "            seen_pks.add(f.pk)\n"
        "            folder_names.append(f.folder_name)\n"
    )

    if old_2 not in content:
        print("[ZH-65] ERROR: dedup anchor not found. File may have diverged.")
        sys.exit(1)

    if content.count(old_2) > 1:
        print("[ZH-65] ERROR: dedup anchor is not unique.")
        sys.exit(1)

    content = content.replace(old_2, new_2, 1)
    TARGET.write_text(content, encoding="utf-8")
    print(f"[ZH-65] Patched (dedup fix): {TARGET}")

# ---------------------------------------------------------------------------
# Write test file
# ---------------------------------------------------------------------------

print("[ZH-65] Writing test file...")

TEST_FILE = Path("tests/app_extensions/test_folder_dedup.py")
TEST_FILE.parent.mkdir(parents=True, exist_ok=True)

TEST_CONTENT = '''\
"""
ZH-65: Tests for two bugs in assets_search/api_folders.py

Bug 1 -- exists() == 0 is always False:
    `if not folders.exists() == 0:` raises when folders EXIST (inverted logic).
    Fix: `if not folders.exists():`

Bug 2 -- get_description may repeat folder names:
    If the queryset yields the same folder pk more than once, folder_name appears
    multiple times in the description string.
    Fix: dedupe by pk before building name list.

Run:
    pytest tests/app_extensions/test_folder_dedup.py -v
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app_extensions.extensions_standard.assets_search.api_folders import (
    call,
    get_description,
)


def _make_request(user=None):
    req = MagicMock()
    req.user = user or MagicMock()
    return req


def _make_async_iter(objects):
    async def _aiter():
        for obj in objects:
            yield obj

    mock_qs = MagicMock()
    mock_qs.__aiter__ = MagicMock(return_value=_aiter())
    return mock_qs


class TestExistsBug:
    @pytest.mark.asyncio
    async def test_call_does_not_raise_when_folders_exist(self):
        """When valid folders are found, call() must NOT raise."""
        mock_folder = MagicMock()
        mock_folder.pk = 1

        mock_qs = MagicMock()
        mock_qs.exists.return_value = True
        mock_qs.distinct.return_value = _make_async_iter([mock_folder])

        mock_chat_response = MagicMock()
        mock_chat_response.sources = []
        mock_chat_response.asave = AsyncMock()

        with (
            patch(
                "app_extensions.extensions_standard.assets_search.api_folders.Folder"
            ) as MockFolder,
            patch(
                "app_extensions.extensions_standard.assets_search.api_folders.generate_sources",
                new=AsyncMock(return_value=([], ["result text"])),
            ),
        ):
            MockFolder.objects.filter.return_value = mock_qs
            result = await call(
                _make_request(),
                {"folder_id": [1], "search_query": "engine"},
                mock_chat_response,
                MagicMock(),
            )

        assert result is not None

    @pytest.mark.asyncio
    async def test_call_raises_when_no_folders_found(self):
        """When no valid folders are found, call() MUST raise."""
        mock_qs = MagicMock()
        mock_qs.exists.return_value = False
        mock_qs.distinct.return_value = mock_qs

        with patch(
            "app_extensions.extensions_standard.assets_search.api_folders.Folder"
        ) as MockFolder:
            MockFolder.objects.filter.return_value = mock_qs
            with pytest.raises(Exception, match="No valid folders"):
                await call(
                    _make_request(),
                    {"folder_id": [999], "search_query": "test"},
                    MagicMock(),
                    MagicMock(),
                )


class TestGetDescriptionDedup:
    @pytest.mark.asyncio
    async def test_duplicate_folder_pk_appears_once_in_description(self):
        """Same folder pk yielded twice -> name appears exactly once."""
        folder = MagicMock()
        folder.pk = 42
        folder.folder_name = "Engine Performance SAM"

        mock_qs = _make_async_iter([folder, folder])
        mock_qs.distinct = MagicMock(return_value=mock_qs)

        with patch(
            "app_extensions.extensions_standard.assets_search.api_folders.Folder"
        ) as MockFolder:
            MockFolder.objects.filter.return_value = mock_qs
            desc = await get_description(
                _make_request(),
                {"folder_id": [42], "search_query": "performance"},
            )

        assert desc.count("Engine Performance SAM") == 1

    @pytest.mark.asyncio
    async def test_two_distinct_folders_both_appear(self):
        """Two different folder pks -> both names in description."""
        folder_a = MagicMock()
        folder_a.pk = 1
        folder_a.folder_name = "Airfoil Design"

        folder_b = MagicMock()
        folder_b.pk = 2
        folder_b.folder_name = "Engine Performance SAM"

        mock_qs = _make_async_iter([folder_a, folder_b])
        mock_qs.distinct = MagicMock(return_value=mock_qs)

        with patch(
            "app_extensions.extensions_standard.assets_search.api_folders.Folder"
        ) as MockFolder:
            MockFolder.objects.filter.return_value = mock_qs
            desc = await get_description(
                _make_request(),
                {"folder_id": [1, 2], "search_query": "test"},
            )

        assert "Airfoil Design" in desc
        assert "Engine Performance SAM" in desc

    @pytest.mark.asyncio
    async def test_empty_folder_list_returns_valid_description(self):
        """No folders -> description must not crash."""
        mock_qs = _make_async_iter([])
        mock_qs.distinct = MagicMock(return_value=mock_qs)

        with patch(
            "app_extensions.extensions_standard.assets_search.api_folders.Folder"
        ) as MockFolder:
            MockFolder.objects.filter.return_value = mock_qs
            desc = await get_description(
                _make_request(),
                {"folder_id": [], "search_query": "anything"},
            )

        assert isinstance(desc, str)
        assert "anything" in desc
'''

if TEST_FILE.exists():
    print(f"[ZH-65] {TEST_FILE} already exists, skipping.")
else:
    TEST_FILE.write_text(TEST_CONTENT, encoding="utf-8")
    print(f"[ZH-65] Wrote: {TEST_FILE}")

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------

print("[ZH-65] Done.")
print()
print("Verify:")
print("  pytest tests/app_extensions/test_folder_dedup.py -v")
print()
print("Expected: 5 tests pass")
print("  TestExistsBug::test_call_does_not_raise_when_folders_exist")
print("  TestExistsBug::test_call_raises_when_no_folders_found")
print("  TestGetDescriptionDedup::test_duplicate_folder_pk_appears_once_in_description")
print("  TestGetDescriptionDedup::test_two_distinct_folders_both_appear")
print("  TestGetDescriptionDedup::test_empty_folder_list_returns_valid_description")
