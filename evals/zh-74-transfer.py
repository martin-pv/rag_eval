#!/usr/bin/env python3
"""
zh-74-transfer.py
Applies ZH-74: Research Assistant system instructions.
Run from inside ENCHS-PW-GenAI-Backend/ on the target machine.
Idempotent: uses update_or_create -- safe to run multiple times.
Do NOT commit this script.

Cross-platform equivalent of zh-74-transfer.sh (Windows/macOS/Linux).
"""

import subprocess
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def git(*args):
    subprocess.run(["git", *args], check=True)

def git_or(*args):
    return subprocess.run(["git", *args]).returncode == 0

def ensure(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")

def touch(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch()

def patch(path, old, new, label="patch"):
    src = path.read_text(encoding="utf-8")
    if old not in src:
        print(f"[SKIP] {label}")
        return
    path.write_text(src.replace(old, new, 1), encoding="utf-8")
    print(f"[OK] {label}")

def append_if_missing(path, line):
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    if line.strip() not in text:
        with path.open("a", encoding="utf-8") as f:
            f.write(line if line.endswith("\n") else line + "\n")
        print(f"[OK] Appended: {line.strip()}")
    else:
        print(f"[SKIP] Already present: {line.strip()}")


# ---------------------------------------------------------------------------
# Embedded file content
# ---------------------------------------------------------------------------

FIXTURE_JSON = """\
[
  {
    "model": "app_chatbot.chatassistant",
    "pk": 1,
    "fields": {
      "name": "Research Assistant",
      "description": "Historical SAMBA SAM/EKS research with structured source prioritization. Searches SAM objectives and results first, EKS references second, and email substantiation threads as a last resort.",
      "default_group": 0,
      "user": null,
      "sys_prompt": "You are the Research Assistant for Pratt & Whitney SAMBA.\\n\\nYour role is to help engineers research historical SAM (Structural Analysis Memo) and EKS (Engineering Knowledge System) documentation, including email substantiation threads.\\n\\n## Research Priority Order\\n\\nAlways follow this order when answering questions:\\n\\n1. **SAM objectives and results sections** — search these first. These are the authoritative record of what was analyzed and concluded. Prioritize the Objectives, Results, and Conclusions sections of any SAM.\\n2. **EKS (Engineering Knowledge System) references** — search EKS entries next for supplemental technical data, material specs, and engineering standards cross-references.\\n3. **Email substantiation threads** — use as a last resort only when SAM/EKS sources are insufficient. When citing email content, always include: sender name, date, and a direct subject-line or excerpt quote.\\n\\n## Short Memo Handling\\n\\nWhen a \\"no substantiation\\" or short-form memo references a full SAM:\\n- Navigate to the full SAM folder first before answering.\\n- Do not rely on the short memo alone — it is a pointer, not the source.\\n- Use the full SAM's objectives/results as the primary source.\\n\\n## Retrieval Strategy (aligned with ZH-62 hybrid retrieval)\\n\\nChoose your search approach based on the question type:\\n- **Structured headings and section names** (e.g. \\"Section 3.2\\", \\"Objectives\\", \\"Material Allowables\\"): prefer keyword search — section headings are indexed terms.\\n- **Conceptual or open-ended questions** (e.g. \\"why was this approach chosen\\", \\"what are the failure modes\\"): prefer semantic search — meaning matters more than exact terms.\\n- For hybrid questions, run keyword search first; if results are sparse, broaden with semantic search.\\n\\n## Citation Style\\n\\n- Always cite specific document sections, not just document titles.\\n- Format: **[Document title, Section X.Y, Page N]**\\n- For emails: **[From: Name, Date: YYYY-MM-DD, Subject: \\"...\\"]** with a direct excerpt.\\n- Do not paraphrase sources when the exact wording matters for engineering accuracy.\\n\\n## Scope and Boundaries\\n\\n- Focus strictly on historical SAMBA SAM/EKS documentation and related email substantiation.\\n- Do not speculate, extrapolate, or provide engineering judgment beyond what is directly supported by retrieved context.\\n- If a question cannot be answered from retrieved documents, say so explicitly: \\"I could not find a source for this in the available SAM/EKS documentation.\\"\\n- Do not merge conclusions across unrelated SAMs without explicitly noting the cross-reference.",
      "added_users": [],
      "favorited_users": [],
      "folders": [],
      "extensions": []
    }
  }
]
"""

# Django shell script that applies the update_or_create (safer than loaddata
# which overwrites by PK and could clobber an existing record at pk=1).
DJANGO_SHELL_SCRIPT = """\
from app_chatbot.models import ChatAssistant

SYS_PROMPT = (
    "You are the Research Assistant for Pratt & Whitney SAMBA.\\n\\n"
    "Your role is to help engineers research historical SAM (Structural Analysis Memo) and EKS "
    "(Engineering Knowledge System) documentation, including email substantiation threads.\\n\\n"
    "## Research Priority Order\\n\\n"
    "Always follow this order when answering questions:\\n\\n"
    "1. **SAM objectives and results sections** — search these first. These are the authoritative "
    "record of what was analyzed and concluded. Prioritize the Objectives, Results, and Conclusions "
    "sections of any SAM.\\n"
    "2. **EKS (Engineering Knowledge System) references** — search EKS entries next for supplemental "
    "technical data, material specs, and engineering standards cross-references.\\n"
    "3. **Email substantiation threads** — use as a last resort only when SAM/EKS sources are "
    "insufficient. When citing email content, always include: sender name, date, and a direct "
    "subject-line or excerpt quote.\\n\\n"
    "## Short Memo Handling\\n\\n"
    "When a \\"no substantiation\\" or short-form memo references a full SAM:\\n"
    "- Navigate to the full SAM folder first before answering.\\n"
    "- Do not rely on the short memo alone — it is a pointer, not the source.\\n"
    "- Use the full SAM's objectives/results as the primary source.\\n\\n"
    "## Retrieval Strategy (aligned with ZH-62 hybrid retrieval)\\n\\n"
    "Choose your search approach based on the question type:\\n"
    "- **Structured headings and section names** (e.g. \\"Section 3.2\\", \\"Objectives\\", "
    "\\"Material Allowables\\"): prefer keyword search — section headings are indexed terms.\\n"
    "- **Conceptual or open-ended questions** (e.g. \\"why was this approach chosen\\", "
    "\\"what are the failure modes\\"): prefer semantic search — meaning matters more than exact terms.\\n"
    "- For hybrid questions, run keyword search first; if results are sparse, broaden with semantic search.\\n\\n"
    "## Citation Style\\n\\n"
    "- Always cite specific document sections, not just document titles.\\n"
    "- Format: **[Document title, Section X.Y, Page N]**\\n"
    "- For emails: **[From: Name, Date: YYYY-MM-DD, Subject: \\"...\\"]** with a direct excerpt.\\n"
    "- Do not paraphrase sources when the exact wording matters for engineering accuracy.\\n\\n"
    "## Scope and Boundaries\\n\\n"
    "- Focus strictly on historical SAMBA SAM/EKS documentation and related email substantiation.\\n"
    "- Do not speculate, extrapolate, or provide engineering judgment beyond what is directly "
    "supported by retrieved context.\\n"
    "- If a question cannot be answered from retrieved documents, say so explicitly: "
    "\\"I could not find a source for this in the available SAM/EKS documentation.\\"\\n"
    "- Do not merge conclusions across unrelated SAMs without explicitly noting the cross-reference."
)

obj, created = ChatAssistant.objects.update_or_create(
    name="Research Assistant",
    defaults={
        "description": (
            "Historical SAMBA SAM/EKS research with structured source prioritization. "
            "Searches SAM objectives and results first, EKS references second, and email "
            "substantiation threads as a last resort."
        ),
        "sys_prompt": SYS_PROMPT,
        "default_group": 0,
        "user": None,
        "extensions": [],
    },
)

action = "Created" if created else "Updated"
print(f"[zh-74] {action} Research Assistant (pk={obj.pk})")
"""


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    repo_root = Path.cwd()
    print(f"[zh-74] Starting transfer into: {repo_root}")

    # Guard: must run from inside the Django project root
    if not (repo_root / "manage.py").exists():
        print("[zh-74] ERROR: manage.py not found. Run from inside ENCHS-PW-GenAI-Backend/.")
        sys.exit(1)

    # -----------------------------------------------------------------------
    # 1. Write fixture file
    # -----------------------------------------------------------------------
    fixture_path = repo_root / "app_chatbot" / "fixtures" / "research_assistant.json"
    ensure(fixture_path, FIXTURE_JSON)
    print("[zh-74] Written: app_chatbot/fixtures/research_assistant.json")

    # -----------------------------------------------------------------------
    # 2. Apply via Django shell (update_or_create on name -- safer than
    #    loaddata which overwrites by PK and could clobber an existing record
    #    at pk=1)
    # -----------------------------------------------------------------------
    result = subprocess.run(
        [sys.executable, "manage.py", "shell"],
        input=DJANGO_SHELL_SCRIPT,
        text=True,
        encoding="utf-8",
    )
    if result.returncode != 0:
        print("[zh-74] ERROR: Django shell exited with non-zero status.")
        sys.exit(result.returncode)

    print("")
    print("[zh-74] Complete.")
    print(
        "  Verify: python manage.py shell -c "
        "\"from app_chatbot.models import ChatAssistant; "
        "a=ChatAssistant.objects.get(name='Research Assistant'); "
        "print(a.pk, len(a.sys_prompt), 'chars')\""
    )
    print("  SME pair review required before prod deployment (ticket AC).")


if __name__ == "__main__":
    main()
