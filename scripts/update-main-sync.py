#!/usr/bin/env python3
"""
update-main-sync.py — UPDATE MAIN: snapshot diff, JSON report, apply preview.

Implements the workflow from:
  Pratt&Whitney/.devtool/features/update-main-sync-2026-04-27.md

Run inside a git checkout of ENCHS-PW-GenAI-Backend (or Pratt-Backend), repo root.

Commands:
  diff              Print name-status, commits, and stat diff vs snapshot baseline.
  report [SNAPSHOT] Write sync_report.json in the current directory.
  show              Print human-readable summary from ./sync_report.json.
  full [SNAPSHOT]   Run diff, then report, then show (typical “review sync” pass).
  publish-rag-eval  Copy this script + companion wrappers to ~/rag_eval/scripts (see --rag-eval-root).

Canonical checkout path (avoid repo-root `scripts/` — it matches `.gitignore` `Scripts/` on macOS):
  Pratt-Backend/devscripts/update-main-sync/

Environment:
  RAG_EVAL_ROOT     Override default ~/rag_eval for publish-rag-eval.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

DEFAULT_SNAPSHOT = "8115d83"


def run_git(args: list[str], cwd: Path | None = None) -> str:
    out = subprocess.check_output(["git", *args], text=True, cwd=cwd).strip()
    return out


def git_root(start: Path | None = None) -> Path:
    root = run_git(["rev-parse", "--show-toplevel"], cwd=start or Path.cwd())
    return Path(root)


def cmd_diff(snapshot: str, repo: Path) -> int:
    head = run_git(["rev-parse", "HEAD"], cwd=repo)
    print(f"=== Diff: {snapshot} → {head} ===\n")
    print("=== Changed files ===")
    print(run_git(["diff", "--name-status", snapshot, "HEAD"], cwd=repo))
    print()
    print("=== Commits since snapshot ===")
    print(run_git(["log", "--oneline", f"{snapshot}..HEAD"], cwd=repo) or "(none)")
    print()
    print("=== Stats ===")
    print(run_git(["diff", "--stat", snapshot, "HEAD"], cwd=repo))
    return 0


def parse_name_status(changed_raw: str) -> list[dict]:
    """Parse `git diff --name-status` lines (handles renames/copies)."""
    changes: list[dict] = []
    for line in changed_raw.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        status_token = parts[0]
        status = status_token[0].upper()
        entry: dict = {"status": status}
        if status in ("R", "C") and len(parts) >= 3:
            entry["old_path"] = parts[1]
            entry["path"] = parts[2]
        elif len(parts) >= 2:
            entry["path"] = parts[1]
        else:
            entry["path"] = ""
        changes.append(entry)
    return changes


def cmd_report(snapshot: str, repo: Path, out_path: Path) -> int:
    current = run_git(["rev-parse", "HEAD"], cwd=repo)
    changed_raw = run_git(["diff", "--name-status", snapshot, "HEAD"], cwd=repo)
    changes = parse_name_status(changed_raw)

    commits_raw = run_git(["log", "--oneline", f"{snapshot}..HEAD"], cwd=repo)
    commits = []
    for line in commits_raw.splitlines():
        line = line.strip()
        if not line:
            continue
        bits = line.split(maxsplit=1)
        commits.append({"sha": bits[0], "msg": bits[1] if len(bits) > 1 else ""})

    report = {
        "snapshot_commit": snapshot,
        "current_head": current,
        "total_changes": len(changes),
        "commits_since_snapshot": len(commits),
        "commits": commits,
        "changed_files": changes,
    }

    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(
        f"Report written to {out_path} — {len(changes)} file changes, "
        f"{len(commits)} commits"
    )
    return 0


def cmd_show(report_path: Path) -> int:
    if not report_path.is_file():
        print(f"ERROR: {report_path} not found. Run: update-main-sync.py report", file=sys.stderr)
        return 1
    report = json.loads(report_path.read_text(encoding="utf-8"))
    print(f"Snapshot: {report['snapshot_commit']}")
    print(f"Current:  {report['current_head']}")
    print(f"Changes:  {report['total_changes']}")
    print()
    status_map = {"A": "ADDED", "M": "MODIFIED", "D": "DELETED", "R": "RENAMED", "C": "COPIED"}
    for c in report["changed_files"]:
        st = status_map.get(c["status"], c["status"])
        p = c.get("path", "")
        if c["status"] in ("R", "C") and "old_path" in c:
            print(f"  {st}: {c['old_path']} → {p}")
        else:
            print(f"  {st}: {p}")
    return 0


def cmd_full(snapshot: str, repo: Path, report_path: Path) -> int:
    cmd_diff(snapshot, repo)
    print()
    cmd_report(snapshot, repo, report_path)
    print()
    cmd_show(report_path)
    return 0


def companion_wrappers(this_script: Path) -> dict[str, str]:
    """Relative filename -> file contents for thin wrappers."""
    py = this_script.name
    return {
        "diff-from-snapshot.sh": f"""#!/usr/bin/env bash
# Thin wrapper — see update-main-sync.py
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
exec python3 "$ROOT/{py}" diff "${{1:-8115d83}}"
""",
        "generate-sync-report.py": f"""#!/usr/bin/env python3
# Thin wrapper — see update-main-sync.py
import subprocess
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent
script = ROOT / "{py}"
args = [sys.executable, str(script), "report", *sys.argv[1:]]
raise SystemExit(subprocess.call(args))
""",
        "apply-sync.sh": f"""#!/usr/bin/env bash
# Thin wrapper — see update-main-sync.py
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
exec python3 "$ROOT/{py}" show
""",
    }


def cmd_publish_rag_eval(this_script: Path, rag_eval_root: Path, dry_run: bool) -> int:
    dest_dir = rag_eval_root / "scripts"
    print(f"[publish-rag-eval] Target: {dest_dir}")
    if dry_run:
        print("  (dry-run — no files written)")
    elif not dry_run:
        dest_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(this_script, dest_dir / this_script.name)
        os.chmod(dest_dir / this_script.name, 0o755)
        for name, content in companion_wrappers(this_script).items():
            p = dest_dir / name
            p.write_text(content, encoding="utf-8")
            os.chmod(p, 0o755)

    print(f"  + {this_script.name}")
    for name in companion_wrappers(this_script):
        print(f"  + {name}")

    if dry_run:
        return 0

    print()
    print(
        "Synced to rag_eval. Commit from ~/rag_eval:",
        f'  cd "{rag_eval_root}" && git add scripts && git status',
    )
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="UPDATE MAIN — sync local repo with production (snapshot diff + report)."
    )
    parser.add_argument(
        "command",
        nargs="?",
        default="full",
        choices=("diff", "report", "show", "full", "publish-rag-eval"),
        help="diff | report | show | full | publish-rag-eval (default: full)",
    )
    parser.add_argument(
        "snapshot",
        nargs="?",
        default=DEFAULT_SNAPSHOT,
        help=f"Baseline git SHA (default {DEFAULT_SNAPSHOT})",
    )
    parser.add_argument(
        "--repo",
        type=Path,
        default=None,
        help="Git repo root (default: detected from cwd)",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("sync_report.json"),
        help="Path for sync_report.json (report/full/show)",
    )
    parser.add_argument(
        "--rag-eval-root",
        type=Path,
        default=Path(os.environ.get("RAG_EVAL_ROOT", str(Path.home() / "rag_eval"))),
        help="rag_eval clone root for publish-rag-eval (or env RAG_EVAL_ROOT)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="For publish-rag-eval: print actions only",
    )

    args = parser.parse_args(argv)

    try:
        repo = args.repo or git_root()
    except subprocess.CalledProcessError:
        print("ERROR: not inside a git repository.", file=sys.stderr)
        return 1

    this_script = Path(__file__).resolve()

    if args.command == "publish-rag-eval":
        return cmd_publish_rag_eval(this_script, args.rag_eval_root.expanduser(), args.dry_run)

    snapshot = args.snapshot

    if args.command == "diff":
        return cmd_diff(snapshot, repo)
    if args.command == "report":
        return cmd_report(snapshot, repo, args.report.resolve())
    if args.command == "show":
        return cmd_show(args.report.resolve())
    if args.command == "full":
        return cmd_full(snapshot, repo, args.report.resolve())

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
