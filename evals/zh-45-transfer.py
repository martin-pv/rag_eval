#!/usr/bin/env python3
"""ZH-45: Add xclass_level to Folder model + API (surgical patches).

Run from Django project root (folder containing manage.py).

Does NOT copy whole files from a sibling backend/ tree — only edits targets.
"""

from pathlib import Path

BACKEND = Path.cwd()

MODELS_PATH = BACKEND / "app_retrieval" / "models.py"
MIGRATION_PATH = (
    BACKEND / "app_retrieval" / "migrations" / "0028_folder_xclass_level.py"
)
FOLDERS_VIEW_PATH = BACKEND / "app_retrieval" / "views" / "folders.py"

XCLASS_FIELD_SNIPPET = '''
    xclass_level = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Export control classification level (e.g. EAR99, CUI, ECCN)",
    )
'''

MIGRATION_BODY = '''from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app_retrieval", "0027_asset_knowledge_graph_contentitem_kg_retries_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="folder",
            name="xclass_level",
            field=models.CharField(
                blank=True,
                help_text="Export control classification level (e.g. EAR99, CUI, ECCN)",
                max_length=50,
                null=True,
            ),
        ),
    ]
'''


def patch_models() -> None:
    text = MODELS_PATH.read_text(encoding="utf-8")
    if "xclass_level" in text:
        print("[ZH-45] models.py already has xclass_level")
        return
    anchor = "    processing_flag = models.TextField(default=\"default\", null=False, blank=False)\n"
    if anchor not in text:
        raise SystemExit("[ZH-45] ERROR: could not find processing_flag anchor in models.py")
    insert = anchor + XCLASS_FIELD_SNIPPET + "\n"
    MODELS_PATH.write_text(text.replace(anchor, insert, 1), encoding="utf-8")
    print("[ZH-45] Patched app_retrieval/models.py (xclass_level field)")


def write_migration() -> None:
    MIGRATION_PATH.parent.mkdir(parents=True, exist_ok=True)
    if MIGRATION_PATH.exists():
        print("[ZH-45] Migration already exists:", MIGRATION_PATH.name)
        return
    MIGRATION_PATH.write_text(MIGRATION_BODY.rstrip() + "\n", encoding="utf-8")
    print("[ZH-45] Wrote", MIGRATION_PATH)


def patch_folders_view() -> None:
    text = FOLDERS_VIEW_PATH.read_text(encoding="utf-8")
    if '"xclass_level"' in text or "'xclass_level'" in text:
        print("[ZH-45] folders.py already exposes xclass_level")
        return

    folder_anchor = '"kg_status": folder.knowledge_graph.status,'
    folder_repl = (
        '"kg_status": folder.knowledge_graph.status,\n'
        '                        "xclass_level": getattr(folder, "xclass_level", None),'
    )
    n = text.count(folder_anchor)
    if n != 2:
        raise SystemExit(
            f"[ZH-45] ERROR: expected 2× {folder_anchor!r}, found {n}"
        )
    text = text.replace(folder_anchor, folder_repl)

    post_anchor = '"kg_status": new_folder.knowledge_graph.status,'
    post_repl = (
        '"kg_status": new_folder.knowledge_graph.status,\n'
        '                "xclass_level": getattr(new_folder, "xclass_level", None),'
    )
    if post_anchor not in text:
        raise SystemExit("[ZH-45] ERROR: new_folder kg_status anchor not found")
    text = text.replace(post_anchor, post_repl, 1)

    FOLDERS_VIEW_PATH.write_text(text, encoding="utf-8")
    print("[ZH-45] Patched app_retrieval/views/folders.py")


def main() -> None:
    for p in (MODELS_PATH, FOLDERS_VIEW_PATH):
        if not p.is_file():
            raise SystemExit(f"[ZH-45] ERROR: {p} not found. Run from Django project root.")

    patch_models()
    write_migration()
    patch_folders_view()

    print("[ZH-45] Done. Verify with:")
    print("  python manage.py migrate")
    print("  python manage.py check")


if __name__ == "__main__":
    main()
