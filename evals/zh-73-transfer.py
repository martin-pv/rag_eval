#!/usr/bin/env python3
"""ZH-73: Document Builder Assistant — management command.

Run from the Django project root (the folder that contains manage.py), i.e.
Path.cwd() should be ENCHS-PW-GenAI-Backend (not its parent).

Writes app_chatbot/management/commands/create_doc_builder_assistant.py (embedded below).
Idempotent: overwrite same content each run.
"""

from pathlib import Path

BACKEND = Path.cwd()

# Embedded command — no dependency on a sibling backend/ tree next to this script.
CREATE_DOC_BUILDER_ASSISTANT_PY = '''\
from django.core.management.base import BaseCommand

from app_chatbot.models import ChatAssistant

ASSISTANT_NAME = "Document Builder"
ASSISTANT_VERSION = "v1.0"

SYS_PROMPT = """\
You are the Document Builder for Pratt & Whitney SAMBA reports.

## Capabilities
- Generate full SAM (Source Approval Method) reports
- Substantiate claims with email evidence
- Output structured JSON for document vs chat surfaces

## Output Format (when structured_output=true)
Always respond with valid JSON:
{"chat": "<brief status or clarification>", "document_patch": {"section": "<section_name>", "content": "<generated_content>"}}

## SAM Report Structure
[Section instructions TBD with DT team — update this prompt once structure is confirmed]

## Email Substantiation
When citing email evidence: include sender, date, subject, and relevant excerpt.
Format: "Per email from <sender> on <date> re: <subject> — '<excerpt>'"
"""


class Command(BaseCommand):
    help = "Create or update the Document Builder ChatAssistant record (idempotent)."

    def handle(self, *args, **options):
        assistant, created = ChatAssistant.objects.update_or_create(
            name=ASSISTANT_NAME,
            defaults={
                "description": f"Document Builder {ASSISTANT_VERSION} — ZH-73. SAM report generation with structured JSON output for ZH-67.",
                "sys_prompt": SYS_PROMPT,
                "default_group": 0,
                "user": None,
                "extensions": [],
            },
        )

        action = "Created" if created else "Updated"
        self.stdout.write(
            self.style.SUCCESS(
                f"{action} ChatAssistant '{ASSISTANT_NAME}' (pk={assistant.pk})"
            )
        )
        self.stdout.write(
            "  Extensions are empty — configure via admin or API after verifying "
            "which extensions should be available to Document Builder users."
        )
'''


def main() -> None:
    mgmt = BACKEND / "app_chatbot" / "management"
    cmds = mgmt / "commands"
    mgmt.mkdir(parents=True, exist_ok=True)
    cmds.mkdir(parents=True, exist_ok=True)
    (mgmt / "__init__.py").touch(exist_ok=True)
    (cmds / "__init__.py").touch(exist_ok=True)

    dest = cmds / "create_doc_builder_assistant.py"
    dest.write_text(CREATE_DOC_BUILDER_ASSISTANT_PY.rstrip() + "\n", encoding="utf-8")
    print(f"[ZH-73] Wrote: {dest}")

    print("[ZH-73] Done. Run on the target machine:")
    print("  python manage.py create_doc_builder_assistant")
    print("")
    print("  Verify:")
    print("  python manage.py shell -c \\")
    print(
        '    "from app_chatbot.models import ChatAssistant; '
        "a = ChatAssistant.objects.get(name='Document Builder'); "
        'print(a.pk, a.description)"'
    )


if __name__ == "__main__":
    main()
