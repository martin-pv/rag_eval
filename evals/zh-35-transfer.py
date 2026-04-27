#!/usr/bin/env python3
"""
ZH-35 Transfer Script — GenAI Advanced Auth: Registration API

Deploys:
  - NEW  ENCHS-PW-GenAI-Backend/app_users/views/register_genai.py
  - EDIT ENCHS-PW-GenAI-Backend/app_users/urls.py  (add import + URL path)

Run from the root of the runtime repo checkout:
    python3 zh-35-transfer.py

Branch: zh-35-genai-auth
"""
import subprocess
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Standard helpers
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


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BACKEND = Path.cwd() / "ENCHS-PW-GenAI-Backend"
BRANCH  = "zh-35-genai-auth"


# ---------------------------------------------------------------------------
# File contents
# ---------------------------------------------------------------------------

REGISTER_GENAI_PY = '''\
# app_users/views/register_genai.py
#
# Registration endpoint for GenAI user provisioning (ZH-35).
# Service-token authenticated via APIKeyAuthentication.
#
# Governance gate: Step 2 (auto-entitlement via X-Class + US-Person claims) is
# blocked pending Global Trade sign-off. Do NOT implement auto-entitlement until
# George / Dave confirm approval.

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from app_users.models import APIKey

# APIKeyAuthentication is the service-token auth class from app_users / ping_auth.
# Adjust import path if the class lives elsewhere on the runtime machine.
from app_users.ping_auth import APIKeyAuthentication


class RegisterGenAIView(APIView):
    """Service-token-authenticated endpoint to provision GenAI user state.

    POST /api/users/register-genai/

    Body:
        user_id (str): The user to provision.

    Returns:
        200 {"status": "provisioned", "user_id": "<user_id>"}
        400 {"error": "user_id required"}

    Step 2 (auto-entitlement via X-Class + US-Person claims) is blocked pending
    Global Trade sign-off (ZH-35 governance gate). Implement entitlement mapping
    once approved -- do NOT add without that approval.

    TODO: provision GenAI role, folder memberships, assistant access for user_id.
    Implementation details pending policy confirmation from Global Trade / George / Dave.
    """

    authentication_classes = [APIKeyAuthentication]

    def post(self, request):
        user_id = request.data.get("user_id")
        if not user_id:
            return Response(
                {"error": "user_id required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        # TODO: idempotently provision:
        #   - GenAI role assignment
        #   - Default folder memberships
        #   - Default assistant access
        # Implementation details pending policy confirmation from Global Trade / George / Dave.
        return Response(
            {"status": "provisioned", "user_id": user_id},
            status=status.HTTP_200_OK,
        )
'''


# ---------------------------------------------------------------------------
# Steps
# ---------------------------------------------------------------------------

def step_branch():
    """Checkout or create the feature branch."""
    if not git_or("checkout", BRANCH):
        git("checkout", "-b", BRANCH)
    print(f"[OK] on branch {BRANCH}")


def step_create_view():
    """Write app_users/views/register_genai.py."""
    dest = BACKEND / "app_users" / "views" / "register_genai.py"
    ensure(dest, REGISTER_GENAI_PY)
    print(f"[OK] created {dest.relative_to(BACKEND)}")


def step_patch_urls():
    """Add import + URL path to app_users/urls.py."""
    urls_path = BACKEND / "app_users" / "urls.py"

    # 1. Add the import after the last existing import block.
    #    Anchor on the closing of the existing imports / urlpatterns line.
    patch(
        urls_path,
        old="urlpatterns = [",
        new=(
            "from app_users.views.register_genai import RegisterGenAIView\n\n"
            "urlpatterns = ["
        ),
        label="urls.py — add RegisterGenAIView import",
    )

    # 2. Add the URL entry before the closing bracket.
    patch(
        urls_path,
        old='    path("api/profile", ProfileView.as_view(), name="user-profile"),\n]',
        new=(
            '    path("api/profile", ProfileView.as_view(), name="user-profile"),\n'
            '    path("api/users/register-genai/", RegisterGenAIView.as_view(), name="register-genai"),\n'
            "]"
        ),
        label="urls.py — add register-genai path",
    )


def step_commit():
    """Stage and commit the changes."""
    git("add",
        str(BACKEND / "app_users" / "views" / "register_genai.py"),
        str(BACKEND / "app_users" / "urls.py"),
    )
    git("commit", "-m", "ZH-35: add RegisterGenAIView registration endpoint (Step 3)")
    print("[OK] committed")


def main():
    if not BACKEND.exists():
        print(f"[ERROR] BACKEND not found: {BACKEND}")
        print("  Run this script from the root directory that contains ENCHS-PW-GenAI-Backend/")
        sys.exit(1)

    step_branch()
    step_create_view()
    step_patch_urls()
    step_commit()
    print("\n[DONE] ZH-35 transfer complete.")
    print("  Next: verify on runtime machine, then open PR to main.")


if __name__ == "__main__":
    main()
