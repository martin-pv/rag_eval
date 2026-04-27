#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(pwd)"
echo "[zh-61] Starting transfer into: $REPO_ROOT"

TARGET="$REPO_ROOT/app_chatbot/views/chatstream.py"

if [ ! -f "$TARGET" ]; then
    echo "[zh-61] ERROR: $TARGET not found. Run from inside ENCHS-PW-GenAI-Backend/."
    exit 1
fi

# ---------------------------------------------------------------------------
# Patch 1 — parse temperature after structured_output line
# ---------------------------------------------------------------------------
python3 - << 'PYEOF'
import sys

path = "app_chatbot/views/chatstream.py"
with open(path) as f:
    content = f.read()

guard = "raw_temp = request.data.get(\"temperature\", None)"
if guard in content:
    print("[zh-61] Already applied: temperature parse block")
    sys.exit(0)

anchor = 'structured_output = bool(request.data.get("structured_output", False))'
if anchor not in content:
    print(f"[zh-61] ERROR: anchor not found in {path}")
    sys.exit(1)

patch = anchor + """
            raw_temp = request.data.get("temperature", None)
            temperature = None
            if raw_temp is not None:
                try:
                    temperature = float(raw_temp)
                except (TypeError, ValueError):
                    temperature = None"""

content = content.replace(anchor, patch, 1)
with open(path, "w") as f:
    f.write(content)
print("[zh-61] Patched: temperature parse block inserted after structured_output")
PYEOF

# ---------------------------------------------------------------------------
# Patch 2 — clamp and apply temperature to data dict
# ---------------------------------------------------------------------------
python3 - << 'PYEOF'
import sys

path = "app_chatbot/views/chatstream.py"
with open(path) as f:
    content = f.read()

guard = 'data["temperature"] = max(0.0, min(2.0, temperature))'
if guard in content:
    print("[zh-61] Already applied: temperature clamp block")
    sys.exit(0)

anchor = "data = get_default_data(stream=True)"
if anchor not in content:
    print(f"[zh-61] ERROR: anchor not found in {path}")
    sys.exit(1)

patch = anchor + """
            if temperature is not None:
                data["temperature"] = max(0.0, min(2.0, temperature))"""

content = content.replace(anchor, patch, 1)
with open(path, "w") as f:
    f.write(content)
print("[zh-61] Patched: temperature clamp applied after get_default_data")
PYEOF

echo ""
echo "[zh-61] Complete. Verify:"
echo "  python manage.py check"
echo "  # POST /streaming_response/ with temperature=0.9 → OpenAI receives temperature=0.9"
echo "  # POST /streaming_response/ with temperature=5.0 → clamped to 2.0"
echo "  # POST /streaming_response/ without temperature → existing behavior unchanged"
