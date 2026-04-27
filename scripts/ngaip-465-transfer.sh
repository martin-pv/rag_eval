#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(pwd)"
echo "[465-transfer] Starting transfer into: $REPO_ROOT"

TARGET="$REPO_ROOT/backend/app_chatbot/llm_middleware.py"

if [ ! -f "$TARGET" ]; then
    echo "[465-transfer] ERROR: $TARGET not found. Run from ENCHS-PW-GenAI-Backend/ root."
    exit 1
fi

# ---------------------------------------------------------------------------
# Patch 1 — Import: add get_user_extensions after "import time"
# ---------------------------------------------------------------------------
python3 - << 'PYEOF'
import sys

path = "backend/app_chatbot/llm_middleware.py"
with open(path) as f:
    content = f.read()

# Idempotent guard: only present after patching
if "from app_extensions.utils import get_user_extensions" in content:
    print("[465-transfer] Already patched (import): " + path)
    sys.exit(0)

anchor = "import time"
if anchor not in content:
    print("[465-transfer] ERROR: import anchor not found in " + path)
    sys.exit(1)

if content.count(anchor) > 1:
    print("[465-transfer] ERROR: import anchor is not unique in " + path)
    sys.exit(1)

new_code = anchor + "\nfrom app_extensions.utils import get_user_extensions"
content = content.replace(anchor, new_code, 1)

with open(path, "w") as f:
    f.write(content)
print("[465-transfer] Patched (import): " + path)
PYEOF

# ---------------------------------------------------------------------------
# Patch 2 — Skills context block: insert after uploaded_asset_blurbs list comp
# ---------------------------------------------------------------------------
python3 - << 'PYEOF'
import sys

path = "backend/app_chatbot/llm_middleware.py"
with open(path) as f:
    content = f.read()

# Idempotent guard
if "available_skills_blurbs = []" in content:
    print("[465-transfer] Already patched (skills context block): " + path)
    sys.exit(0)

anchor = (
    '        f"asset_id: {asset.pk}, folder_id: {asset.folder.pk}, asset_name: {asset.name}"\n'
    '        async for asset in uploaded_assets\n'
    '    ]'
)
if anchor not in content:
    print("[465-transfer] ERROR: skills-block anchor not found in " + path)
    sys.exit(1)

if content.count(anchor) > 1:
    print("[465-transfer] ERROR: skills-block anchor is not unique in " + path)
    sys.exit(1)

tq = '"""'
insertion = (
    "\n"
    "\n"
    "    user_extensions = await get_user_extensions(request)\n"
    "    available_skills_blurbs = []\n"
    "    for ext_key, ext_info in user_extensions.items():\n"
    "        if ext_info.get(\"has_access\"):\n"
    "            tools_desc = \"\\n\".join([\n"
    "                f\"    - {tool['name']}: {tool['description']}\"\n"
    "                for tool in ext_info.get(\"tools\", [])\n"
    "            ])\n"
    "            pretty = ext_info.get(\"pretty_name\") or ext_key\n"
    "            desc = ext_info.get(\"description\") or \"\"\n"
    "            available_skills_blurbs.append(\n"
    "                f\"- **{pretty}** ({ext_key}): {desc}\\n{tools_desc}\"\n"
    "            )\n"
    "\n"
    "    available_skills_context = \"\"\n"
    "    if available_skills_blurbs:\n"
    + f"        available_skills_context = dedent(f{tq}\n"
    "        ### AVAILABLE SKILLS (EXTENSIONS)\n"
    "        You have access to the following skills (tools) which you can invoke to help the user:\n"
    "{indent(chr(10).join(available_skills_blurbs), '        ')}\n"
    + f"        {tq}).strip()"
)

content = content.replace(anchor, anchor + insertion, 1)

with open(path, "w") as f:
    f.write(content)
print("[465-transfer] Patched (skills context block): " + path)
PYEOF

# ---------------------------------------------------------------------------
# Patch 3 — Return dict key: add "available_skills_context" after
#            "files_and_folders_context": dedent(...) closing block
# ---------------------------------------------------------------------------
python3 - << 'PYEOF'
import sys

path = "backend/app_chatbot/llm_middleware.py"
with open(path) as f:
    content = f.read()

# Idempotent guard
if '"available_skills_context": available_skills_context,' in content:
    print("[465-transfer] Already patched (return dict key): " + path)
    sys.exit(0)

anchor = '        "files_and_folders_context": dedent(f"""'
if anchor not in content:
    print("[465-transfer] ERROR: return-dict anchor not found in " + path)
    sys.exit(1)

if content.count(anchor) > 1:
    print("[465-transfer] ERROR: return-dict anchor is not unique in " + path)
    sys.exit(1)

# Find closing of the files_and_folders_context value — it ends with }).strip(),
# then we need to insert our new key after that entry.
# Locate the full entry and append the new key after the closing line.
closing_marker = '        """).strip(),'
# There are multiple .strip(), entries; we want the one for files_and_folders_context.
# We'll splice in after the last occurrence inside the return dict, which immediately
# follows the anchor. Walk forward from the anchor position.
anchor_pos = content.index(anchor)
closing_pos = content.index(closing_marker, anchor_pos)
insert_pos = closing_pos + len(closing_marker)

new_key = '\n        "available_skills_context": available_skills_context,'
content = content[:insert_pos] + new_key + content[insert_pos:]

with open(path, "w") as f:
    f.write(content)
print("[465-transfer] Patched (return dict key): " + path)
PYEOF

# ---------------------------------------------------------------------------
# Patch 4 — System message injection: insert skills context check after
#            system_message_addendum_text = ""
# ---------------------------------------------------------------------------
python3 - << 'PYEOF'
import sys

path = "backend/app_chatbot/llm_middleware.py"
with open(path) as f:
    content = f.read()

# Idempotent guard
if 'if system_message_dict.get("available_skills_context"):' in content:
    print("[465-transfer] Already patched (system message injection): " + path)
    sys.exit(0)

anchor = '    system_message_addendum_text = ""'
if anchor not in content:
    print("[465-transfer] ERROR: system-message anchor not found in " + path)
    sys.exit(1)

if content.count(anchor) > 1:
    print("[465-transfer] ERROR: system-message anchor is not unique in " + path)
    sys.exit(1)

new_code = anchor + """
    if system_message_dict.get("available_skills_context"):
        system_message_addendum_text += "\\n" + system_message_dict["available_skills_context"] + "\\n\""""
content = content.replace(anchor, new_code, 1)

with open(path, "w") as f:
    f.write(content)
print("[465-transfer] Patched (system message injection): " + path)
PYEOF

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
echo ""
echo "[465-transfer] Complete. Verify with:"
echo "  python manage.py check"
echo "  python -c \"from app_chatbot.llm_middleware import get_default_system_message_dict; print('OK')\""
echo ""
echo "  Manual test: start a chat as a user with extension access and confirm"
echo "  '### AVAILABLE SKILLS' block appears in the system message."
