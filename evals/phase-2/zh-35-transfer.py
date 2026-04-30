#!/usr/bin/env python3
"""
ZH-35 Transfer Script — GenAI Advanced Auth: Registration API

Deploys:
  - NEW  ENCHS-PW-GenAI-Backend/app_users/register_genai.py
  - EDIT ENCHS-PW-GenAI-Backend/app_users/urls.py  (add import + URL path)

  Placement note: many Pratt backends use a single app_users/views.py module.
  Then ``app_users.views`` is NOT a package, so ``from app_users.views.register_genai``
  fails with "is not a package". The view lives at app root as register_genai.py
  and urls import ``from app_users.register_genai import RegisterGenAIView``.

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

BACKEND = Path.cwd()
BRANCH  = "zh-35-genai-auth"


# ---------------------------------------------------------------------------
# File contents
# ---------------------------------------------------------------------------

REGISTER_GENAI_PY = '''\
# app_users/register_genai.py
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


def step_cleanup_stale_nested_module():
    """Remove app_users/views/register_genai.py if a prior run created it.

    When app_users/views.py exists, ``app_users.views`` is a module, not a package;
    nested register_genai under a ``views/`` directory does not match that layout
    and breaks imports. Delete the misleading file so only app_users/register_genai.py remains.
    """
    stale = BACKEND / "app_users" / "views" / "register_genai.py"
    if stale.is_file():
        stale.unlink()
        print(f"[OK] removed stale {stale.relative_to(BACKEND)} (use app_users/register_genai.py instead)")


def step_create_view():
    """Write app_users/register_genai.py (beside views.py — avoids 'views is not a package')."""
    dest = BACKEND / "app_users" / "register_genai.py"
    ensure(dest, REGISTER_GENAI_PY)
    print(f"[OK] created {dest.relative_to(BACKEND)}")


def step_patch_urls():
    """Add import + URL path to app_users/urls.py."""
    urls_path = BACKEND / "app_users" / "urls.py"

    # 0. If a prior run used the broken nested path, rewrite the import.
    _src0 = urls_path.read_text(encoding="utf-8")
    _broken = "from app_users.views.register_genai import RegisterGenAIView"
    _fixed = "from app_users.register_genai import RegisterGenAIView"
    if _broken in _src0 and _fixed not in _src0:
        urls_path.write_text(_src0.replace(_broken, _fixed, 1), encoding="utf-8")
        print("[OK] urls.py — replaced broken app_users.views.register_genai import")

    # 1. Add the import after the last existing import block.
    #    Anchor on the closing of the existing imports / urlpatterns line.
    if _fixed not in urls_path.read_text(encoding="utf-8"):
        patch(
            urls_path,
            old="urlpatterns = [",
            new=(
                "from app_users.register_genai import RegisterGenAIView\n\n"
                "urlpatterns = ["
            ),
            label="urls.py — add RegisterGenAIView import",
        )
    else:
        print("[SKIP] urls.py — RegisterGenAIView import already present")

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


TEST_REGISTER_GENAI_PY = '''\
"""Tests for ZH-35 RegisterGenAIView (no DB, no DRF setup)."""
from unittest.mock import MagicMock

from app_users.register_genai import RegisterGenAIView


def test_register_genai_returns_400_when_user_id_missing():
    request = MagicMock()
    request.data = {}
    response = RegisterGenAIView().post(request)
    assert response.status_code == 400
    assert response.data == {"error": "user_id required"}


def test_register_genai_returns_200_when_user_id_present():
    request = MagicMock()
    request.data = {"user_id": "u1"}
    response = RegisterGenAIView().post(request)
    assert response.status_code == 200
    assert response.data == {"status": "provisioned", "user_id": "u1"}


def test_register_genai_uses_api_key_authentication():
    from app_users.ping_auth import APIKeyAuthentication
    assert APIKeyAuthentication in RegisterGenAIView.authentication_classes


def test_register_genai_returns_drf_response_object():
    from rest_framework.response import Response
    request = MagicMock()
    request.data = {"user_id": "u1"}
    response = RegisterGenAIView().post(request)
    assert isinstance(response, Response)


def test_register_genai_response_status_uses_named_constants():
    request = MagicMock()
    request.data = {}
    bad = RegisterGenAIView().post(request)
    request.data = {"user_id": "x"}
    ok = RegisterGenAIView().post(request)
    assert bad.status_code == 400 and ok.status_code == 200
    assert "error" in bad.data and "user_id" not in bad.data
    assert ok.data["user_id"] == "x" and ok.data["status"] == "provisioned"


def test_register_genai_module_documents_governance_gate():
    import inspect
    from app_users import register_genai
    src = inspect.getsource(register_genai)
    assert "Global Trade" in src and "Step 2" in src, "Governance gate note must remain in module docstring"
'''

TEST_FILE = BACKEND / "tests" / "app_users" / "test_register_genai.py"


def step_create_test():
    """Write tests/app_users/test_register_genai.py."""
    touch(BACKEND / "tests" / "__init__.py")
    touch(BACKEND / "tests" / "app_users" / "__init__.py")
    ensure(TEST_FILE, TEST_REGISTER_GENAI_PY)
    print(f"[OK] created {TEST_FILE.relative_to(BACKEND)}")


def step_run_pytest():
    """Run generated ZH-35 tests before committing."""
    subprocess.run([sys.executable, "-m", "pytest", str(TEST_FILE.relative_to(BACKEND)), "-v"], check=True)


def step_commit():
    """Stage source changes, force-add generated tests, and commit."""
    git("add",
        str(BACKEND / "app_users" / "register_genai.py"),
        str(BACKEND / "app_users" / "urls.py"),
    )
    git("add", "-f", str(TEST_FILE))
    git("commit", "-m", "ZH-35: add RegisterGenAIView registration endpoint (Step 3)")
    print("[OK] committed")


def main():
    if not BACKEND.exists():
        print(f"[ERROR] BACKEND not found: {BACKEND}")
        print("  Run this script from the root directory that contains ENCHS-PW-GenAI-Backend/")
        sys.exit(1)

    step_branch()
    step_cleanup_stale_nested_module()
    step_create_view()
    step_patch_urls()
    step_create_test()
    step_run_pytest()
    step_commit()
    print("\n[DONE] ZH-35 transfer complete.")
    print("  Next: verify on runtime machine, then open PR to main.")


if __name__ == "__main__":
    main()
