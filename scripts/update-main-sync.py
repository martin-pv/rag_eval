#!/usr/bin/env python3
"""
update-main-sync.py — Compare backup branch to current main; JSON report + full patch.

Default comparison:
  FROM  main-backup-for-mac-claude-repo-04-07-2026  (Mac Claude repo snapshot)
  TO    main                                       (current main)

Intended case (e.g. Windows ENCHS-PW-GenAI-Backend laptop):
  The backup branch sits at an older commit; local ``main`` has moved forward.
  That is exactly “backup is behind main”. This script shows everything that
  changed between those tips:

  - ``git log FROM..TO`` — commits reachable from TO but not FROM
  - ``git diff FROM TO`` — full unified diff of all file changes

  If ``main`` itself is behind ``origin/main``, update first (``git pull``) or pass
  ``--fetch`` / compare to ``origin/main`` (see ``--to-ref``).

Windows: run from the repo root in Git Bash, PowerShell, or cmd — use
``py -3 devscripts\\update-main-sync\\update-main-sync.py full`` if ``python``
is not on PATH. Patch/report files are UTF-8 with LF newlines (fine for review
and ``git apply``).

Commands:
  diff              Print name-status, commits (FROM..TO), and --stat diff.
  patch             Write unified diff for ALL files (git diff FROM TO) to a .patch file.
  report            Write sync_report.json (resolved SHAs + file list + commits).
  show              Print summary from ./sync_report.json.
  full              diff + report + show + patch (default artifact: sync_full.diff).
  publish-rag-eval  Copy this toolkit to ~/rag_eval/scripts.

Also documented in:
  Pratt&Whitney/.devtool/features/update-main-sync-2026-04-27.md

Canonical path:
  Pratt-Backend/devscripts/update-main-sync/

Environment:
  RAG_EVAL_ROOT     Override ~/rag_eval for publish-rag-eval.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

DEFAULT_FROM_REF = "main-backup-for-mac-claude-repo-04-07-2026"
DEFAULT_TO_REF = "main"


def cmd_fetch(repo: Path, remote: str) -> int:
    """Optional ``git fetch`` so local main (or remote-tracking refs) are current."""
    print(f"[update-main-sync] git fetch {remote}")
    r = subprocess.run(["git", "fetch", remote], cwd=repo)
    return r.returncode


def run_git(args: list[str], cwd: Path | None = None) -> str:
    out = subprocess.check_output(["git", *args], text=True, cwd=cwd).strip()
    return out


def git_root(start: Path | None = None) -> Path:
    root = run_git(["rev-parse", "--show-toplevel"], cwd=start or Path.cwd())
    return Path(root)


def resolve_ref(repo: Path, ref: str) -> str:
    """Resolve ref to full SHA; fails if missing."""
    return run_git(["rev-parse", "--verify", ref], cwd=repo)


def cmd_diff(from_ref: str, to_ref: str, repo: Path) -> int:
    fr = resolve_ref(repo, from_ref)
    to = resolve_ref(repo, to_ref)
    print(f"=== Diff: {from_ref} ({fr[:12]}…) → {to_ref} ({to[:12]}…) ===\n")
    print("=== Changed files ===")
    print(run_git(["diff", "--name-status", from_ref, to_ref], cwd=repo))
    print()
    print(f"=== Commits on {to_ref} not in {from_ref} ({from_ref}..{to_ref}) ===")
    print(run_git(["log", "--oneline", f"{from_ref}..{to_ref}"], cwd=repo) or "(none)")
    print()
    print("=== Stats ===")
    print(run_git(["diff", "--stat", from_ref, to_ref], cwd=repo))
    return 0


def cmd_patch(from_ref: str, to_ref: str, repo: Path, out_path: Path) -> int:
    """Write full unified diff for every changed file (same as `git diff FROM TO`)."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fr = resolve_ref(repo, from_ref)
    to = resolve_ref(repo, to_ref)
    with out_path.open("w", encoding="utf-8", newline="\n") as f:
        r = subprocess.run(
            ["git", "diff", "--no-ext-diff", from_ref, to_ref],
            cwd=repo,
            stdout=f,
        )
    if r.returncode != 0:
        print("ERROR: git diff failed (see messages above).", file=sys.stderr)
        return r.returncode
    print(
        f"Full unified diff written to {out_path.resolve()}\n"
        f"  ({from_ref} {fr[:12]}… → {to_ref} {to[:12]}…)"
    )
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


def cmd_report(from_ref: str, to_ref: str, repo: Path, out_path: Path) -> int:
    from_sha = resolve_ref(repo, from_ref)
    to_sha = resolve_ref(repo, to_ref)
    changed_raw = run_git(["diff", "--name-status", from_ref, to_ref], cwd=repo)
    changes = parse_name_status(changed_raw)

    commits_raw = run_git(["log", "--oneline", f"{from_ref}..{to_ref}"], cwd=repo)
    commits = []
    for line in commits_raw.splitlines():
        line = line.strip()
        if not line:
            continue
        bits = line.split(maxsplit=1)
        commits.append({"sha": bits[0], "msg": bits[1] if len(bits) > 1 else ""})

    report = {
        "from_ref": from_ref,
        "to_ref": to_ref,
        "from_sha": from_sha,
        "to_sha": to_sha,
        "compare_range": f"{from_ref}..{to_ref}",
        "total_changes": len(changes),
        "commits_from_to": len(commits),
        "commits": commits,
        "changed_files": changes,
        # Legacy keys for older consumers
        "snapshot_commit": from_sha,
        "current_head": to_sha,
        "commits_since_snapshot": len(commits),
    }

    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(
        f"Report written to {out_path} — {len(changes)} file changes, "
        f"{len(commits)} commits ({from_ref} → {to_ref})"
    )
    return 0


def cmd_show(report_path: Path) -> int:
    if not report_path.is_file():
        print(
            f"ERROR: {report_path} not found. Run: update-main-sync.py report",
            file=sys.stderr,
        )
        return 1
    report = json.loads(report_path.read_text(encoding="utf-8"))
    fr = report.get("from_ref") or report.get("snapshot_commit", "?")[:40]
    tr = report.get("to_ref") or report.get("current_head", "?")[:40]
    if "from_sha" in report:
        print(f"From: {report['from_ref']} ({report['from_sha'][:12]}…)")
        print(f"To:   {report['to_ref']} ({report['to_sha'][:12]}…)")
    else:
        print(f"From (legacy): {fr}")
        print(f"To (legacy):   {tr}")
    print(f"Changes: {report.get('total_changes', '?')}")
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


def cmd_full(
    from_ref: str,
    to_ref: str,
    repo: Path,
    report_path: Path,
    patch_path: Path,
    skip_patch: bool,
) -> int:
    cmd_diff(from_ref, to_ref, repo)
    print()
    cmd_report(from_ref, to_ref, repo, report_path)
    print()
    cmd_show(report_path)
    if not skip_patch:
        print()
        cmd_patch(from_ref, to_ref, repo, patch_path)
    return 0


def companion_wrappers(this_script: Path) -> dict[str, str]:
    """Relative filename -> file contents for thin wrappers."""
    py = this_script.name
    return {
        "diff-from-snapshot.sh": f"""#!/usr/bin/env bash
# Thin wrapper — see update-main-sync.py (defaults: backup branch vs main)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
exec python3 "$ROOT/{py}" diff "$@"
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
exec python3 "$ROOT/{py}" show "$@"
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
        description=(
            "Compare backup branch to main: list changes, JSON report, full unified patch."
        )
    )
    parser.add_argument(
        "command",
        nargs="?",
        default="full",
        choices=("diff", "patch", "report", "show", "full", "publish-rag-eval"),
        help="diff | patch | report | show | full | publish-rag-eval (default: full)",
    )
    parser.add_argument(
        "--from-ref",
        default=DEFAULT_FROM_REF,
        metavar="REF",
        help=f"Older / backup ref (default: {DEFAULT_FROM_REF})",
    )
    parser.add_argument(
        "--to-ref",
        default=DEFAULT_TO_REF,
        metavar="REF",
        help=f"Newer ref to compare (default: {DEFAULT_TO_REF})",
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
        help="Path for sync_report.json",
    )
    parser.add_argument(
        "--patch-out",
        type=Path,
        default=Path("sync_full.diff"),
        help="Output path for unified diff (patch/full)",
    )
    parser.add_argument(
        "--no-patch",
        action="store_true",
        help="With full: skip writing the unified diff file",
    )
    parser.add_argument(
        "--rag-eval-root",
        type=Path,
        default=Path(os.environ.get("RAG_EVAL_ROOT", str(Path.home() / "rag_eval"))),
        help="rag_eval clone root for publish-rag-eval",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="For publish-rag-eval: print actions only",
    )
    parser.add_argument(
        "--fetch",
        action="store_true",
        help="Before comparing: run git fetch <remote> (useful on Windows if origin moved)",
    )
    parser.add_argument(
        "--fetch-remote",
        default="origin",
        metavar="NAME",
        help="Remote for --fetch (default: origin)",
    )

    args = parser.parse_args(argv)

    try:
        repo = args.repo or git_root()
    except subprocess.CalledProcessError:
        print("ERROR: not inside a git repository.", file=sys.stderr)
        return 1

    this_script = Path(__file__).resolve()
    from_ref = args.from_ref
    to_ref = args.to_ref

    if args.command == "publish-rag-eval":
        return cmd_publish_rag_eval(this_script, args.rag_eval_root.expanduser(), args.dry_run)

    if args.fetch:
        rc = cmd_fetch(repo, args.fetch_remote)
        if rc != 0:
            return rc
        print()

    # Verify refs early for clearer errors
    try:
        resolve_ref(repo, from_ref)
        resolve_ref(repo, to_ref)
    except subprocess.CalledProcessError as e:
        print(
            f"ERROR: could not resolve --from-ref / --to-ref in this repo.\n"
            f"  Create or fetch: {from_ref!r} and {to_ref!r}",
            file=sys.stderr,
        )
        return 1

    report_path = args.report.resolve()
    patch_path = args.patch_out.resolve()

    if args.command == "diff":
        return cmd_diff(from_ref, to_ref, repo)
    if args.command == "patch":
        return cmd_patch(from_ref, to_ref, repo, patch_path)
    if args.command == "report":
        return cmd_report(from_ref, to_ref, repo, report_path)
    if args.command == "show":
        return cmd_show(report_path)
    if args.command == "full":
        return cmd_full(from_ref, to_ref, repo, report_path, patch_path, args.no_patch)

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
