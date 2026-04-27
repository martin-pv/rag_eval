#!/usr/bin/env python3
"""
ZH-64 Transfer Script — Files Stuck in Processing: Watchdog Task

IMPORTANT: Confirm with Dave that the watchdog is needed before running.
Dave Ferguson is actively resolving this issue. If his "lighter reprocess" path
resolves the stuck assets, this watchdog may not be needed.

Deploys:
  - NEW  ENCHS-PW-GenAI-Backend/app_background/tasks/stuck_processing_watchdog.py
  - NEW  ENCHS-PW-GenAI-Backend/tests/app_retrieval/test_stuck_processing.py

Run from the root of the runtime repo checkout:
    python3 zh-64-transfer.py

Branch: zh-64-processing-stuck
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
BRANCH  = "zh-64-processing-stuck"


# ---------------------------------------------------------------------------
# File contents
# ---------------------------------------------------------------------------

WATCHDOG_PY = '''\
# app_background/tasks/stuck_processing_watchdog.py
#
# Celery task: detect assets stuck in "in_progress" for longer than
# stale_minutes and reset them to "error" so they can be reprocessed.
#
# Root causes addressed (ZH-64):
#   - Tasks dropped by Celery worker (never picked up)
#   - Mid-process failures that did not update status to "error"
#   - DB lock deadlocks leaving status stuck
#
# Schedule recommendation: run every 30 minutes via Celery Beat.
# Example celery beat schedule entry (add to app/celery.py or settings.py):
#
#   "reset-stuck-assets": {
#       "task": "app_background.tasks.stuck_processing_watchdog.reset_stuck_assets",
#       "schedule": crontab(minute="*/30"),
#   },

from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from app_retrieval.models import Asset
import logging

logger = logging.getLogger(__name__)


@shared_task
def reset_stuck_assets(stale_minutes: int = 60) -> int:
    """Mark assets stuck in_progress for > stale_minutes as error.

    Args:
        stale_minutes: Assets untouched for this many minutes are considered
                       stuck and will be reset to "error" status.

    Returns:
        Number of assets reset.
    """
    cutoff = timezone.now() - timedelta(minutes=stale_minutes)
    stuck = Asset.objects.filter(status="in_progress", modified_date__lt=cutoff)
    count = stuck.count()
    if count:
        stuck.update(status="error")
        logger.warning(
            "[watchdog] Reset %d stuck asset(s) to error status "
            "(stale_minutes=%d, cutoff=%s)",
            count,
            stale_minutes,
            cutoff.isoformat(),
        )
    else:
        logger.info("[watchdog] No stuck assets found (stale_minutes=%d)", stale_minutes)
    return count
'''


TEST_STUCK_PROCESSING_PY = '''\
# tests/app_retrieval/test_stuck_processing.py
#
# Tests for the stuck-processing watchdog (ZH-64).
# Verifies the ORM query used in reset_stuck_assets correctly identifies
# assets that have been in_progress beyond the stale threshold.

import pytest
from django.utils import timezone
from datetime import timedelta


@pytest.mark.django_db
def test_stale_in_progress_assets_query(asset_factory):
    """Query to find assets stuck in processing > N minutes should work."""
    from app_retrieval.models import Asset

    # Asset stuck for >30 min
    stuck = asset_factory(status="in_progress")
    stuck.modified_date = timezone.now() - timedelta(minutes=35)
    stuck.save(update_fields=["modified_date"])

    # Asset that just started -- should NOT be in stuck queryset
    fresh = asset_factory(status="in_progress")

    stale_cutoff = timezone.now() - timedelta(minutes=30)
    stuck_qs = Asset.objects.filter(
        status="in_progress",
        modified_date__lt=stale_cutoff,
    )

    assert stuck in stuck_qs, "Asset stuck 35 min should appear in stale queryset"
    assert fresh not in stuck_qs, "Freshly-started asset should not appear in stale queryset"


@pytest.mark.django_db
def test_reset_stuck_assets_updates_status(asset_factory):
    """reset_stuck_assets task should flip stuck assets from in_progress to error."""
    from app_retrieval.models import Asset
    from app_background.tasks.stuck_processing_watchdog import reset_stuck_assets

    stuck = asset_factory(status="in_progress")
    stuck.modified_date = timezone.now() - timedelta(minutes=90)
    stuck.save(update_fields=["modified_date"])

    count = reset_stuck_assets(stale_minutes=60)

    stuck.refresh_from_db()
    assert stuck.status == "error", "Stuck asset should be reset to error status"
    assert count >= 1, "Task should report at least one asset reset"


@pytest.mark.django_db
def test_reset_stuck_assets_ignores_fresh(asset_factory):
    """reset_stuck_assets should not touch assets that are still within threshold."""
    from app_retrieval.models import Asset
    from app_background.tasks.stuck_processing_watchdog import reset_stuck_assets

    fresh = asset_factory(status="in_progress")
    # modified_date defaults to now() -- should be within threshold

    count = reset_stuck_assets(stale_minutes=60)

    fresh.refresh_from_db()
    assert fresh.status == "in_progress", "Fresh asset should remain in_progress"
'''


# ---------------------------------------------------------------------------
# Steps
# ---------------------------------------------------------------------------

def step_branch():
    """Checkout or create the feature branch."""
    if not git_or("checkout", BRANCH):
        git("checkout", "-b", BRANCH)
    print(f"[OK] on branch {BRANCH}")


def step_create_watchdog():
    """Write app_background/tasks/stuck_processing_watchdog.py."""
    dest = BACKEND / "app_background" / "tasks" / "stuck_processing_watchdog.py"
    ensure(dest, WATCHDOG_PY)
    print(f"[OK] created {dest.relative_to(BACKEND)}")


def step_create_test():
    """Write tests/app_retrieval/test_stuck_processing.py."""
    dest = BACKEND / "tests" / "app_retrieval" / "test_stuck_processing.py"
    ensure(dest, TEST_STUCK_PROCESSING_PY)
    print(f"[OK] created {dest.relative_to(BACKEND)}")


def step_commit():
    """Stage and commit the changes."""
    git("add",
        str(BACKEND / "app_background" / "tasks" / "stuck_processing_watchdog.py"),
        str(BACKEND / "tests" / "app_retrieval" / "test_stuck_processing.py"),
    )
    git("commit", "-m",
        "ZH-64: add stuck-processing watchdog Celery task + ORM query tests")
    print("[OK] committed")


def main():
    # Reminder guard — do not run blind.
    print("=" * 60)
    print("  ZH-64 STUCK PROCESSING WATCHDOG TRANSFER")
    print("  CONFIRM WITH DAVE BEFORE RUNNING:")
    print("    1. Is Dave's lighter reprocess path merged?")
    print("    2. Is folder 1702 still stuck?")
    print("    3. Is a recurring watchdog actually needed?")
    print("  If Dave's fix resolves it, close this branch instead.")
    print("=" * 60)
    answer = input("Confirmed with Dave that watchdog is needed? Type 'yes' to continue: ").strip().lower()
    if answer != "yes":
        print("[ABORT] Run aborted. Confirm with Dave first.")
        sys.exit(0)

    if not BACKEND.exists():
        print(f"[ERROR] BACKEND not found: {BACKEND}")
        print("  Run this script from the root directory that contains ENCHS-PW-GenAI-Backend/")
        sys.exit(1)

    step_branch()
    step_create_watchdog()
    step_create_test()
    step_commit()
    print("\n[DONE] ZH-64 transfer complete.")
    print("  Next steps:")
    print("    1. Run pytest tests/app_retrieval/test_stuck_processing.py")
    print("    2. Add reset_stuck_assets to Celery Beat schedule (see watchdog module header)")
    print("    3. Open PR to main")


if __name__ == "__main__":
    main()
