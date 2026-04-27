#!/usr/bin/env bash
set -euo pipefail

BRANCH="zh-44-message-sources"
TARGET="ENCHS-PW-GenAI-Backend/app_chatbot/views/chatstream.py"
TESTS_DIR="ENCHS-PW-GenAI-Backend/tests/app_chatbot"

echo "[ZH-44] Switching to branch $BRANCH..."
git checkout main
git pull
git checkout -b "$BRANCH" 2>/dev/null || git checkout "$BRANCH"

if [ ! -f "$TARGET" ]; then
    echo "ERROR: $TARGET not found. Run from repo root."
    exit 1
fi

# ---------------------------------------------------------------------------
# Patch chatstream.py — two targeted hunks via Python
# ---------------------------------------------------------------------------
echo "[ZH-44] Patching $TARGET..."

python3 - "$TARGET" <<'PYEOF'
import sys

path = sys.argv[1]
src = open(path).read()
original = src

# ---------------------------------------------------------------------------
# Hunk 1: Add _build_attachment_sources() helper after openai.api_key line
# ---------------------------------------------------------------------------
ANCHOR_1 = "openai.api_key = settings.OPENAI_API_LLM_KEY\n"
HELPER = (
    "\n\n"
    "def _build_attachment_sources(asset_ids: list) -> list[dict]:\n"
    '    """Build the sources list for a user ChatResponse from uploaded asset IDs.\n'
    "\n"
    "    Only positive integers are valid PKs. Booleans are excluded (bool is a\n"
    "    subclass of int in Python, so True/False would otherwise pass isinstance).\n"
    "    String numerics are accepted (DRF may deliver IDs as strings).\n"
    '    """\n'
    "    return [\n"
    '        {"source_type": "attachment", "asset_id": int(aid)}\n'
    "        for aid in asset_ids\n"
    "        if (isinstance(aid, int) and not isinstance(aid, bool) and aid > 0)\n"
    "        or (isinstance(aid, str) and aid.isdigit() and int(aid) > 0)\n"
    "    ]\n"
)

if "_build_attachment_sources" not in src:
    if ANCHOR_1 in src:
        src = src.replace(ANCHOR_1, ANCHOR_1 + HELPER, 1)
        print("[ZH-44] Hunk 1 applied: _build_attachment_sources() added")
    else:
        print("[ZH-44] Hunk 1 WARNING: anchor 'openai.api_key = ...' not found")
else:
    print("[ZH-44] Hunk 1 skipped: helper already present")

# ---------------------------------------------------------------------------
# Hunk 2: Replace bare acreate call with sources= kwarg
# ---------------------------------------------------------------------------
OLD_ACREATE = (
    "            user_input_chat_response: ChatResponse = await ChatResponse.objects.acreate(\n"
    "                user=user,\n"
    "                role=\"user\",\n"
    "                content=user_input,\n"
    "            )\n"
)
NEW_ACREATE = (
    "            attachment_sources = _build_attachment_sources(asset_ids)\n"
    "            user_input_chat_response: ChatResponse = await ChatResponse.objects.acreate(\n"
    "                user=user,\n"
    "                role=\"user\",\n"
    "                content=user_input,\n"
    "                sources=attachment_sources,\n"
    "            )\n"
)

if "sources=attachment_sources" not in src:
    if OLD_ACREATE in src:
        src = src.replace(OLD_ACREATE, NEW_ACREATE, 1)
        print("[ZH-44] Hunk 2 applied: sources= added to acreate call")
    else:
        print("[ZH-44] Hunk 2 WARNING: acreate block not found — check chatstream.py manually")
else:
    print("[ZH-44] Hunk 2 skipped: sources= already present")

if src != original:
    open(path, "w").write(src)
    print(f"[ZH-44] Written: {path}")
else:
    print("[ZH-44] No changes written (all hunks already applied)")
PYEOF

# ---------------------------------------------------------------------------
# New test file
# ---------------------------------------------------------------------------
echo "[ZH-44] Creating test file..."
mkdir -p "$TESTS_DIR"
touch "$TESTS_DIR/__init__.py"

cat > "$TESTS_DIR/test_chatstream_sources.py" <<'PYEOF'
"""Tests for ZH-44: user ChatResponse sources persistence.

Run on transfer machine:
    pytest tests/app_chatbot/test_chatstream_sources.py -v -k "sources"
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app_chatbot.views.chatstream import _build_attachment_sources


# ---------------------------------------------------------------------------
# _build_attachment_sources — unit tests (imports real production function)
# ---------------------------------------------------------------------------

class TestBuildAttachmentSources:
    def test_integer_ids_produce_attachment_entries(self):
        result = _build_attachment_sources([1, 2])
        assert result == [
            {"source_type": "attachment", "asset_id": 1},
            {"source_type": "attachment", "asset_id": 2},
        ]

    def test_string_numeric_ids_accepted(self):
        result = _build_attachment_sources(["3", "7"])
        assert result == [
            {"source_type": "attachment", "asset_id": 3},
            {"source_type": "attachment", "asset_id": 7},
        ]

    def test_empty_asset_ids_produces_empty_list(self):
        assert _build_attachment_sources([]) == []

    def test_non_numeric_string_skipped(self):
        result = _build_attachment_sources(["abc", 1])
        assert len(result) == 1
        assert result[0]["asset_id"] == 1

    def test_float_string_skipped(self):
        result = _build_attachment_sources(["2.5", 3])
        assert len(result) == 1
        assert result[0]["asset_id"] == 3

    def test_boolean_true_skipped(self):
        result = _build_attachment_sources([True, 1])
        assert len(result) == 1
        assert result[0]["asset_id"] == 1

    def test_boolean_false_skipped(self):
        result = _build_attachment_sources([False, 2])
        assert len(result) == 1
        assert result[0]["asset_id"] == 2

    def test_negative_int_skipped(self):
        result = _build_attachment_sources([-1, 5])
        assert len(result) == 1
        assert result[0]["asset_id"] == 5

    def test_zero_skipped(self):
        result = _build_attachment_sources([0, 4])
        assert len(result) == 1
        assert result[0]["asset_id"] == 4

    def test_all_entries_have_source_type_attachment(self):
        result = _build_attachment_sources([10, 20, 30])
        assert all(r["source_type"] == "attachment" for r in result)

    def test_mixed_valid_and_invalid(self):
        result = _build_attachment_sources([1, "2", "bad", True, -1, "3"])
        assert [r["asset_id"] for r in result] == [1, 2, 3]


# ---------------------------------------------------------------------------
# Integration: verify acreate receives sources= kwarg
# ---------------------------------------------------------------------------

def _common_patches(acreate_mock):
    return [
        patch("app_chatbot.views.chatstream.get_usage",
              new=AsyncMock(return_value={"tokens_in": 0, "tokens_out": 0})),
        patch("app_chatbot.views.chatstream.Profile.objects.aget",
              new=AsyncMock(return_value=MagicMock(genai_monthly_token_limit=10 ** 9))),
        patch("app_chatbot.views.chatstream.ChatConversation.objects.acreate",
              new=AsyncMock(return_value=MagicMock(
                  pk=99, assistant=None,
                  chat_responses=MagicMock(aadd=AsyncMock()),
                  asave=AsyncMock(),
              ))),
        patch("app_chatbot.views.chatstream.ChatResponse.objects.acreate", acreate_mock),
        patch("app_chatbot.views.chatstream.prepare_conversation_messages",
              new=AsyncMock(return_value=[])),
        patch("app_chatbot.views.chatstream.get_default_tools",
              new=AsyncMock(return_value=[])),
        patch("app_chatbot.views.chatstream.OpenAIStreamGenerator.acreate",
              new=AsyncMock(return_value=AsyncMock(__aiter__=lambda s: iter([])))),
    ]


def _make_request(asset_ids=None):
    request = MagicMock()
    request.user = MagicMock(pk=1, first_name="Test")
    request.data = {
        "user_input": "hello",
        "conversation_id": -1,
        "assistant_id": -1,
        "asset_ids": asset_ids or [],
        "cached_asset_ids": [],
        "folder_ids": [],
        "images": [],
        "structured_output": False,
    }
    return request


async def _run_view(view, request):
    gen = view.post(request)
    if hasattr(gen, "__aiter__"):
        async for _ in gen:
            break
    else:
        await gen


class TestUserChatResponseSourcesPersisted:
    @pytest.mark.asyncio
    async def test_acreate_called_with_attachment_sources(self):
        acreate_mock = AsyncMock(return_value=MagicMock(pk=10, role="user", sources=[]))

        from contextlib import AsyncExitStack
        from app_chatbot.views.chatstream import StreamingResponseView

        async with AsyncExitStack() as stack:
            for ctx in _common_patches(acreate_mock):
                stack.enter_context(ctx)
            await _run_view(StreamingResponseView(), _make_request(asset_ids=[1, 2]))

        user_call = acreate_mock.call_args_list[0]
        sources = user_call.kwargs.get("sources", [])
        assert len(sources) == 2
        assert sources[0] == {"source_type": "attachment", "asset_id": 1}
        assert sources[1] == {"source_type": "attachment", "asset_id": 2}

    @pytest.mark.asyncio
    async def test_acreate_called_with_empty_sources_when_no_asset_ids(self):
        acreate_mock = AsyncMock(return_value=MagicMock(pk=11, role="user", sources=[]))

        from contextlib import AsyncExitStack
        from app_chatbot.views.chatstream import StreamingResponseView

        async with AsyncExitStack() as stack:
            for ctx in _common_patches(acreate_mock):
                stack.enter_context(ctx)
            await _run_view(StreamingResponseView(), _make_request(asset_ids=[]))

        user_call = acreate_mock.call_args_list[0]
        sources = user_call.kwargs.get("sources", [])
        assert sources == []
PYEOF

echo ""
echo "[ZH-44] Done. Verify with:"
echo "  cd ENCHS-PW-GenAI-Backend"
echo "  pytest tests/app_chatbot/test_chatstream_sources.py -v"
echo "  # Expect 13 tests passing"
echo ""
echo "  Integration test: POST with asset_ids, GET conversation history,"
echo "  confirm user message JSON includes sources list."
