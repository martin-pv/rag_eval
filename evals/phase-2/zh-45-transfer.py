#!/usr/bin/env python3
"""ZH-45: Add xclass_level to Folder model + API (surgical patches).

Run from Django project root (folder containing manage.py).

This script does NOT copy folders.py (or any file) from a sibling tree.
It ONLY: inserts one model field, writes one migration if missing, and patches
kg_status dict entries in app_retrieval/views/folders.py.
"""

import subprocess
import sys
from pathlib import Path

BACKEND = Path.cwd()
TEST_FILE = BACKEND / "tests" / "app_retrieval" / "test_xclass_migration.py"

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


TEST_XCLASS_MIGRATION_PY = '''\
"""ZH-45 migration smoke test (string-only, no Django setup needed)."""
from pathlib import Path


def test_xclass_level_migration_has_correct_field_definition():
    src = Path("app_retrieval/migrations/0028_folder_xclass_level.py").read_text(encoding="utf-8")
    assert 'name="xclass_level"' in src
    assert "max_length=50" in src
    assert "blank=True" in src
    assert "null=True" in src
    assert '"app_retrieval", "0027_asset_knowledge_graph_contentitem_kg_retries_and_more"' in src


def test_models_py_has_xclass_level_field():
    src = Path("app_retrieval/models.py").read_text(encoding="utf-8")
    assert "xclass_level = models.CharField(" in src


def test_xclass_migration_uses_addfield_operation():
    src = Path("app_retrieval/migrations/0028_folder_xclass_level.py").read_text(encoding="utf-8")
    assert "migrations.AddField(" in src
    assert 'model_name="folder"' in src


def test_xclass_migration_field_is_charfield_with_help_text():
    src = Path("app_retrieval/migrations/0028_folder_xclass_level.py").read_text(encoding="utf-8")
    assert "models.CharField(" in src
    assert "Export control classification level" in src
    assert "EAR99" in src


def test_models_xclass_field_has_help_text_and_optional_flags():
    src = Path("app_retrieval/models.py").read_text(encoding="utf-8")
    assert "max_length=50" in src
    assert "blank=True" in src
    assert "null=True" in src
    assert "Export control classification level" in src


def test_views_folders_exposes_xclass_level_in_response_dicts():
    src = Path("app_retrieval/views/folders.py").read_text(encoding="utf-8")
    # Patch adds it in 3 places: 2x existing folder dicts + 1x new_folder dict.
    assert src.count('"xclass_level"') >= 2
    assert 'getattr(folder, "xclass_level", None)' in src or 'getattr(new_folder, "xclass_level", None)' in src
'''


def write_test() -> None:
    TEST_FILE.parent.mkdir(parents=True, exist_ok=True)
    init_pkg = BACKEND / "tests" / "__init__.py"
    init_app = TEST_FILE.parent / "__init__.py"
    init_pkg.touch(exist_ok=True)
    init_app.touch(exist_ok=True)
    TEST_FILE.write_text(TEST_XCLASS_MIGRATION_PY, encoding="utf-8")
    print(f"[ZH-45] Wrote {TEST_FILE}")


def run_pytest() -> None:
    subprocess.run([sys.executable, "-m", "pytest", str(TEST_FILE.relative_to(BACKEND)), "-v"], check=True)


def stage_and_commit() -> None:
    subprocess.run(["git", "add",
                    str(MODELS_PATH.relative_to(BACKEND)),
                    str(MIGRATION_PATH.relative_to(BACKEND)),
                    str(FOLDERS_VIEW_PATH.relative_to(BACKEND))], check=True)
    subprocess.run(["git", "add", "-f", str(TEST_FILE.relative_to(BACKEND))], check=True)
    status = subprocess.run(["git", "status", "--short"], capture_output=True, text=True, check=True).stdout.strip()
    if not status:
        print("[ZH-45] Nothing to commit (no changes)")
        return
    subprocess.run(["git", "commit", "-m",
                    "ZH-45: add Folder.xclass_level field, migration, view exposure"], check=True)
    print("[ZH-45] Committed locally")


def main() -> None:
    print("[ZH-45] Applying surgical patches under", BACKEND.resolve())
    for p in (MODELS_PATH, FOLDERS_VIEW_PATH):
        if not p.is_file():
            raise SystemExit(f"[ZH-45] ERROR: {p} not found. Run from Django project root.")

    patch_models()
    write_migration()
    patch_folders_view()
    write_test()
    run_pytest()
    stage_and_commit()

    print("[ZH-45] Done. Verify with:")
    print("  python manage.py migrate")
    print("  python manage.py check")


if __name__ == "__main__":
    main()
