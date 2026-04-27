"""
ngaip-491-transfer.py
Transfers NGAIP-491 catalog agentic tooling to the runtime machine.
Idempotent: safe to run multiple times.
Run from: ENCHS-PW-GenAI-Backend/ project root on the target machine.
Cross-platform: Windows cmd.exe, macOS, Linux.

What this does:
  1. Patches backend/app_extensions/apps.py to register extensions_standard.app_catalog
  2. Creates the app_catalog extension package (api.py + __init__.py)
  3. Creates the test file
"""
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def ensure(path: Path, content: str) -> None:
    """Write content to path, creating parent dirs as needed. Always overwrites."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def touch(path: Path) -> None:
    """Create an empty file (and parent dirs) if it does not exist."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text("", encoding="utf-8")


# ---------------------------------------------------------------------------
# Embedded file content
# ---------------------------------------------------------------------------

APP_CATALOG_API_PY = '''\
import json
from pathlib import Path

from asgiref.sync import sync_to_async
from django.db.models import Q
from django.http import HttpRequest

from app_catalog.models import Project
from app_chatbot.models import ChatResponse
from app_chatbot.utils import LLMStreamGenerator

p = Path(__file__).resolve()
NAME = f"{p.parent.parent.name}|{p.parent.name}|{p.stem}"
EXTENSION_PRETTY_NAME = "App Catalog Search"
CITATION_IDENTIFIER = "app_catalog"

MAX_RESULTS = 10


@sync_to_async
def _search_projects(search_query: str) -> list:
    qs = Project.objects.filter(
        Q(name__icontains=search_query)
        | Q(long_description__icontains=search_query)
        | Q(topic__icontains=search_query)
        | Q(goals_deliverables__icontains=search_query)
    # Order by most recently active project; date is auto_now=True on Project.
    ).order_by("-date")[:MAX_RESULTS]
    return list(qs)


async def get_tool_entry(request: HttpRequest) -> dict:
    return {
        "type": "function",
        "function": {
            "name": NAME,
            "description": (
                "Search the App Catalog for internal applications, projects, and AI use cases. "
                "Use to find similar apps or details about a specific project. "
                f"Returns up to {MAX_RESULTS} matching projects."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "search_query": {
                        "type": "string",
                        "description": "Keywords for project name, description, topic, or goals.",
                    }
                },
                "required": ["search_query"],
            },
        },
    }


# Required — app_extensions/utils.py resolves tools via this alias.
gpt_tool_entry = get_tool_entry


async def get_description(request: HttpRequest, params: dict) -> str:
    q = params.get("search_query", "")
    return f"Searching the App Catalog for \'{q}\'"


async def has_access(request: HttpRequest) -> bool:
    return True


async def call(
    request: HttpRequest,
    params: dict,
    chat_response: ChatResponse,
    generator: LLMStreamGenerator,
) -> str:
    search_query = (params.get("search_query") or "").strip()
    if not search_query:
        return "No search query provided."

    projects = await _search_projects(search_query)
    if not projects:
        return f"No applications found in the catalog matching \'{search_query}\'."

    results = []
    for proj in projects:
        # All text fields are nullable; default to "" so the LLM receives clean strings.
        results.append({
            "name": proj.name,
            "status": proj.get_status_display(),
            "description": proj.long_description or "",
            "goals": proj.goals_deliverables or "",
            "topic": proj.topic or "",
        })

    return json.dumps(results, indent=2)
'''

TEST_APP_CATALOG_PY = '''\
"""Tests for the app_catalog standard extension (NGAIP-491).

All DB access is mocked — no live Django setup needed.
"""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_get_tool_entry_shape():
    from app_extensions.extensions_standard.app_catalog.api import NAME, get_tool_entry

    entry = await get_tool_entry(request=MagicMock())

    assert entry["type"] == "function"
    # Function name must use the pipe-separated NAME convention so EXTENSION_APIS dispatch works.
    assert entry["function"]["name"] == NAME
    assert "search_query" in entry["function"]["parameters"]["properties"]
    assert "search_query" in entry["function"]["parameters"]["required"]


@pytest.mark.asyncio
async def test_gpt_tool_entry_alias_matches_get_tool_entry():
    from app_extensions.extensions_standard.app_catalog.api import (
        get_tool_entry,
        gpt_tool_entry,
    )

    assert gpt_tool_entry is get_tool_entry


@pytest.mark.asyncio
async def test_call_empty_query_returns_message():
    from app_extensions.extensions_standard.app_catalog.api import call

    result = await call(MagicMock(), {"search_query": ""}, MagicMock(), MagicMock())

    assert "No search query" in result


@pytest.mark.asyncio
async def test_call_missing_search_query_key_treated_as_empty():
    from app_extensions.extensions_standard.app_catalog.api import call

    result = await call(MagicMock(), {}, MagicMock(), MagicMock())

    assert "No search query" in result


@pytest.mark.asyncio
async def test_call_whitespace_query_treated_as_empty():
    from app_extensions.extensions_standard.app_catalog.api import call

    result = await call(MagicMock(), {"search_query": "   "}, MagicMock(), MagicMock())

    assert "No search query" in result


@pytest.mark.asyncio
async def test_call_no_results_returns_message():
    from app_extensions.extensions_standard.app_catalog.api import call

    with patch(
        "app_extensions.extensions_standard.app_catalog.api._search_projects",
        new=AsyncMock(return_value=[]),
    ):
        result = await call(
            MagicMock(), {"search_query": "nonexistent"}, MagicMock(), MagicMock()
        )

    assert "No applications found" in result
    assert "nonexistent" in result


@pytest.mark.asyncio
async def test_call_returns_json_with_expected_keys():
    from app_extensions.extensions_standard.app_catalog.api import call

    fake_project = MagicMock()
    fake_project.name = "PrattWise"
    fake_project.get_status_display.return_value = "Build"
    fake_project.long_description = "An AI assistant for P&W engineers."
    fake_project.goals_deliverables = "Improve knowledge retrieval."
    fake_project.topic = "GenAI"

    with patch(
        "app_extensions.extensions_standard.app_catalog.api._search_projects",
        new=AsyncMock(return_value=[fake_project]),
    ):
        result = await call(
            MagicMock(), {"search_query": "PrattWise"}, MagicMock(), MagicMock()
        )

    data = json.loads(result)
    assert len(data) == 1
    assert data[0]["name"] == "PrattWise"
    assert data[0]["status"] == "Build"
    assert "description" in data[0]
    assert "goals" in data[0]
    assert "topic" in data[0]


@pytest.mark.asyncio
async def test_has_access_always_returns_true():
    from app_extensions.extensions_standard.app_catalog.api import has_access

    result = await has_access(MagicMock())

    assert result is True


@pytest.mark.asyncio
async def test_get_description_includes_query():
    from app_extensions.extensions_standard.app_catalog.api import get_description

    result = await get_description(MagicMock(), {"search_query": "turbofan"})

    assert "turbofan" in result
'''


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    REPO_ROOT = Path.cwd()
    print(f"[491-transfer] Starting transfer into: {REPO_ROOT}")

    # -----------------------------------------------------------------------
    # Create directories
    # -----------------------------------------------------------------------
    (REPO_ROOT / "backend" / "app_extensions" / "extensions_standard" / "app_catalog").mkdir(
        parents=True, exist_ok=True
    )
    (REPO_ROOT / "backend" / "tests" / "app_extensions").mkdir(parents=True, exist_ok=True)
    print("[491-transfer] Created directories")

    # -----------------------------------------------------------------------
    # Patch 1 — apps.py: register extensions_standard.app_catalog after deep_research
    # -----------------------------------------------------------------------
    apps_path = REPO_ROOT / "backend" / "app_extensions" / "apps.py"
    src = apps_path.read_text(encoding="utf-8")

    if '"extensions_standard.app_catalog"' in src:
        print("[491-transfer] Already patched (app_catalog registered): skipping patch 1")
    else:
        anchor = '    "extensions_standard.deep_research",'
        if anchor not in src:
            print(f"[491-transfer] ERROR: anchor not found in {apps_path}")
            sys.exit(1)
        if src.count(anchor) > 1:
            print(f"[491-transfer] ERROR: anchor is not unique in {apps_path}")
            sys.exit(1)
        new_code = anchor + '\n    "extensions_standard.app_catalog",'
        apps_path.write_text(src.replace(anchor, new_code, 1), encoding="utf-8")
        print(f"[491-transfer] Patched (app_catalog registered): {apps_path}")

    # -----------------------------------------------------------------------
    # app_extensions/extensions_standard/app_catalog/__init__.py
    # -----------------------------------------------------------------------
    touch(
        REPO_ROOT / "backend" / "app_extensions" / "extensions_standard" / "app_catalog" / "__init__.py"
    )
    print("[491-transfer] Ensured: backend/app_extensions/extensions_standard/app_catalog/__init__.py")

    # -----------------------------------------------------------------------
    # app_extensions/extensions_standard/app_catalog/api.py  (always write)
    # -----------------------------------------------------------------------
    ensure(
        REPO_ROOT / "backend" / "app_extensions" / "extensions_standard" / "app_catalog" / "api.py",
        APP_CATALOG_API_PY,
    )
    print("[491-transfer] Created: backend/app_extensions/extensions_standard/app_catalog/api.py")

    # -----------------------------------------------------------------------
    # tests/app_extensions/__init__.py
    # -----------------------------------------------------------------------
    touch(REPO_ROOT / "backend" / "tests" / "app_extensions" / "__init__.py")
    print("[491-transfer] Ensured: backend/tests/app_extensions/__init__.py")

    # -----------------------------------------------------------------------
    # tests/app_extensions/test_app_catalog_extension.py  (always write)
    # -----------------------------------------------------------------------
    ensure(
        REPO_ROOT / "backend" / "tests" / "app_extensions" / "test_app_catalog_extension.py",
        TEST_APP_CATALOG_PY,
    )
    print("[491-transfer] Created: backend/tests/app_extensions/test_app_catalog_extension.py")

    # -----------------------------------------------------------------------
    # Done
    # -----------------------------------------------------------------------
    print()
    print("[491-transfer] Complete. Verify with:")
    print("  python manage.py check   # no import errors")
    print("  pytest backend/tests/app_extensions/test_app_catalog_extension.py -v")
    print()
    print("  # Confirm extension registered:")
    print("  python -c \"")
    print("from app_extensions.apps import EXTENSIONS")
    print("assert 'extensions_standard.app_catalog' in EXTENSIONS")
    print("print('Registered OK')")
    print("\"")


if __name__ == "__main__":
    main()
