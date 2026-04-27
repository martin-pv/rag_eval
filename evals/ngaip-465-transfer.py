"""
ngaip-465-transfer.py
Transfers NGAIP-465 skills-integration changes to the runtime machine.
Idempotent: safe to run multiple times.
Run from: ENCHS-PW-GenAI-Backend/ project root on the target machine.
Cross-platform: Windows cmd.exe, macOS, Linux.

What this does:
  Patches backend/app_chatbot/llm_middleware.py with 4 targeted changes:
    1. Import: adds get_user_extensions import after "import time"
    2. Skills context block: inserted after uploaded_asset_blurbs comprehension
    3. Return dict key: adds "available_skills_context" after "files_and_folders_context"
    4. System message injection: inserts skills context check after
       system_message_addendum_text = ""
"""
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def patch_file(path: Path, old: str, new: str, label: str) -> None:
    """Replace first occurrence of old with new in path. Prints [OK] or [SKIP]."""
    src = path.read_text(encoding="utf-8")
    if old not in src:
        print(f"[SKIP] {label} — anchor not found or already applied")
        return
    path.write_text(src.replace(old, new, 1), encoding="utf-8")
    print(f"[OK] {label}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    REPO_ROOT = Path.cwd()
    print(f"[465-transfer] Starting transfer into: {REPO_ROOT}")

    target = REPO_ROOT / "backend" / "app_chatbot" / "llm_middleware.py"
    if not target.exists():
        print(f"[465-transfer] ERROR: {target} not found. Run from ENCHS-PW-GenAI-Backend/ root.")
        sys.exit(1)

    # -----------------------------------------------------------------------
    # Patch 1 — Import: add get_user_extensions after "import time"
    # -----------------------------------------------------------------------
    src = target.read_text(encoding="utf-8")
    if "from app_extensions.utils import get_user_extensions" in src:
        print("[465-transfer] Already patched (import): skipping patch 1")
    else:
        anchor = "import time"
        if anchor not in src:
            print(f"[465-transfer] ERROR: import anchor not found in {target}")
            sys.exit(1)
        if src.count(anchor) > 1:
            print(f"[465-transfer] ERROR: import anchor is not unique in {target}")
            sys.exit(1)
        new_code = anchor + "\nfrom app_extensions.utils import get_user_extensions"
        target.write_text(src.replace(anchor, new_code, 1), encoding="utf-8")
        print(f"[465-transfer] Patched (import): {target}")

    # -----------------------------------------------------------------------
    # Patch 2 — Skills context block: insert after uploaded_asset_blurbs list comp
    # -----------------------------------------------------------------------
    src = target.read_text(encoding="utf-8")
    if "available_skills_blurbs = []" in src:
        print("[465-transfer] Already patched (skills context block): skipping patch 2")
    else:
        anchor = (
            '        f"asset_id: {asset.pk}, folder_id: {asset.folder.pk}, asset_name: {asset.name}"\n'
            '        async for asset in uploaded_assets\n'
            '    ]'
        )
        if anchor not in src:
            print(f"[465-transfer] ERROR: skills-block anchor not found in {target}")
            sys.exit(1)
        if src.count(anchor) > 1:
            print(f"[465-transfer] ERROR: skills-block anchor is not unique in {target}")
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
        target.write_text(src.replace(anchor, anchor + insertion, 1), encoding="utf-8")
        print(f"[465-transfer] Patched (skills context block): {target}")

    # -----------------------------------------------------------------------
    # Patch 3 — Return dict key: add "available_skills_context" after
    #            "files_and_folders_context": dedent(...) closing block
    # -----------------------------------------------------------------------
    src = target.read_text(encoding="utf-8")
    if '"available_skills_context": available_skills_context,' in src:
        print("[465-transfer] Already patched (return dict key): skipping patch 3")
    else:
        anchor = '        "files_and_folders_context": dedent(f"""'
        if anchor not in src:
            print(f"[465-transfer] ERROR: return-dict anchor not found in {target}")
            sys.exit(1)
        if src.count(anchor) > 1:
            print(f"[465-transfer] ERROR: return-dict anchor is not unique in {target}")
            sys.exit(1)
        closing_marker = '        """).strip(),'
        anchor_pos = src.index(anchor)
        closing_pos = src.index(closing_marker, anchor_pos)
        insert_pos = closing_pos + len(closing_marker)
        new_key = '\n        "available_skills_context": available_skills_context,'
        target.write_text(src[:insert_pos] + new_key + src[insert_pos:], encoding="utf-8")
        print(f"[465-transfer] Patched (return dict key): {target}")

    # -----------------------------------------------------------------------
    # Patch 4 — System message injection: insert skills context check after
    #            system_message_addendum_text = ""
    # -----------------------------------------------------------------------
    src = target.read_text(encoding="utf-8")
    if 'if system_message_dict.get("available_skills_context"):' in src:
        print("[465-transfer] Already patched (system message injection): skipping patch 4")
    else:
        anchor = '    system_message_addendum_text = ""'
        if anchor not in src:
            print(f"[465-transfer] ERROR: system-message anchor not found in {target}")
            sys.exit(1)
        if src.count(anchor) > 1:
            print(f"[465-transfer] ERROR: system-message anchor is not unique in {target}")
            sys.exit(1)
        new_code = (
            anchor
            + '\n'
            '    if system_message_dict.get("available_skills_context"):\n'
            '        system_message_addendum_text += "\\n" + system_message_dict["available_skills_context"] + "\\n"'
        )
        target.write_text(src.replace(anchor, new_code, 1), encoding="utf-8")
        print(f"[465-transfer] Patched (system message injection): {target}")

    # -----------------------------------------------------------------------
    # Done
    # -----------------------------------------------------------------------
    print()
    print("[465-transfer] Complete. Verify with:")
    print("  python manage.py check")
    print("  python -c \"from app_chatbot.llm_middleware import get_default_system_message_dict; print('OK')\"")
    print()
    print("  Manual test: start a chat as a user with extension access and confirm")
    print("  '### AVAILABLE SKILLS' block appears in the system message.")


if __name__ == "__main__":
    main()
