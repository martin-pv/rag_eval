#!/usr/bin/env bash
set -euo pipefail

BRANCH="zh-67-structured-json-streaming"

# Guard: require a clean working tree before touching git state.
if ! git diff-index --quiet HEAD --; then
    echo "[ZH-67] ERROR: working tree is dirty. Commit or stash changes first." >&2
    exit 1
fi

echo "[ZH-67] Checking out branch $BRANCH..."
git checkout main && git pull origin main
git checkout -b "$BRANCH" 2>/dev/null || git checkout "$BRANCH"

# ---------------------------------------------------------------------------
# Step 2: One-line fix in app_chatbot/views/chatstream.py
# ---------------------------------------------------------------------------
echo "[ZH-67] Patching chatstream.py..."

TARGET="app_chatbot/views/chatstream.py"

if ! grep -q "get_default_data(stream=True)" "$TARGET"; then
    echo "[ZH-67] WARNING: expected pattern not found in $TARGET -- already patched or file changed." >&2
else
    sed -i.bak \
        's/data = get_default_data(stream=True)$/data = get_default_data(stream=True, structured_output=structured_output)/' \
        "$TARGET"
    rm -f "${TARGET}.bak"
    echo "[ZH-67] Patched: get_default_data now receives structured_output=structured_output"
fi

# Verify patch landed
grep -n "get_default_data" "$TARGET" | grep "structured_output" \
    && echo "[ZH-67] Patch verified." \
    || { echo "[ZH-67] ERROR: patch did not apply." >&2; exit 1; }

# ---------------------------------------------------------------------------
# Step 3: Regression tests
# ---------------------------------------------------------------------------
echo "[ZH-67] Writing tests..."
mkdir -p tests/app_chatbot
touch tests/app_chatbot/__init__.py

if [ -f tests/app_chatbot/test_utils.py ]; then
    echo "[ZH-67] tests/app_chatbot/test_utils.py already exists, skipping."
else
cat > tests/app_chatbot/test_utils.py << 'PYEOF'
"""
Unit tests for app_chatbot.utils.get_default_data.

Regression coverage for ZH-67: structured_output must propagate to
response_format in the OpenAI payload when requested.
"""
import pytest

from app_chatbot.utils import get_default_data


class TestGetDefaultDataStructuredOutput:
    def test_structured_output_true_sets_json_object_format(self):
        data = get_default_data(stream=True, structured_output=True)
        assert data["response_format"] == {"type": "json_object"}

    def test_structured_output_false_omits_response_format(self):
        data = get_default_data(stream=True, structured_output=False)
        assert "response_format" not in data

    def test_structured_output_default_omits_response_format(self):
        data = get_default_data(stream=True)
        assert "response_format" not in data

    def test_stream_flag_preserved_when_structured_output_true(self):
        data = get_default_data(stream=True, structured_output=True)
        assert data["stream"] is True

    def test_stream_false_preserved_when_structured_output_true(self):
        data = get_default_data(stream=False, structured_output=True)
        assert data["stream"] is False
        assert data["response_format"] == {"type": "json_object"}

    def test_required_openai_keys_present(self):
        data = get_default_data(stream=True)
        for key in ("messages", "max_tokens", "temperature", "stream"):
            assert key in data
PYEOF
fi

echo "[ZH-67] Done. Verify with:"
echo "  pytest tests/app_chatbot/test_utils.py -v"
echo ""
echo "  # Manual smoke test (structured_output=true → response_format in payload):"
echo "  # POST to /api/chatbot/stream/ with structured_output=true and check OpenAI payload"
