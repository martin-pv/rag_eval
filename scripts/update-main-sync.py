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

Windows CMD: in ``scripts\\`` (or ``devscripts\\update-main-sync\\``) use the
``.cmd`` launchers — no Git Bash required::

  diff-from-snapshot.cmd
  apply-sync.cmd
  generate-sync-report.cmd

Example::

  cd C:\\path\\to\\ENCHS-PW-GenAI-Backend
  scripts\\diff-from-snapshot.cmd --fetch

They try ``py -3`` first, then ``python``. Patch/report outputs stay UTF-8 with LF newlines.

``lines`` output format (no unified-diff noise; line numbers match ``git diff``):

  === path/to/file.py ===
  -42: removed text
  +65: inserted text

Pure insertions are only ``+N:`` lines; deletions only ``-N:``. Omits unchanged
context lines. Use for screenshot/extraction spot-checks.

Commands:
  lines             Compact line-numbered +/- listing for extraction review (see below).
  diff              Print name-status, commits (FROM..TO), and --stat diff.
  patch             Write unified diff to sync_full.diff (default -U0: changed lines only).
  report            Write sync_report.json (resolved SHAs + file list + commits).
  show              Print summary from ./sync_report.json.
  full              diff + report + show + patch; add --with-lines for compact +/- listing.
  publish-rag-eval  Copy this toolkit to ~/rag_eval/scripts.

Also documented in:
  Pratt&Whitney/.devtool/features/update-main-sync-2026-04-27.md

Canonical path:
  Pratt-Backend/devscripts/update-main-sync/

Environment:
  RAG_EVAL_ROOT     Override ~/rag_eval for publish-rag-eval.

Ticket scoping:
  Add one or more ``--ticket-script PATH`` arguments to restrict diff/report/patch/lines
  output to files written by those Python transfer scripts. This is useful for screenshots:

    py -3 scripts\\update-main-sync.py lines --ticket-script evals\\ngaip-365-transfer.py --lines-out -
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import re
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


def _path_from_join_expr(node: ast.AST) -> str | None:
    """Extract string path from expressions like BACKEND / "a" / "b.py"."""
    parts: list[str] = []
    cur = node
    while isinstance(cur, ast.BinOp) and isinstance(cur.op, ast.Div):
        right = cur.right
        if isinstance(right, ast.Constant) and isinstance(right.value, str):
            parts.append(right.value)
        else:
            return None
        cur = cur.left
    if isinstance(cur, ast.Name) and cur.id in {"BACKEND", "ROOT"}:
        return "/".join(reversed(parts))
    return None


def extract_ticket_script_paths(script_path: Path) -> list[str]:
    """Return repo-relative files that a transfer script writes/touches.

    The NGAIP transfer scripts are ordinary Python and usually write files via
    helpers such as ensure(BACKEND / "...", ...), touch(...), append_if_missing(...),
    or patch(...). This parser intentionally looks only at the first argument to
    those helper calls, so it is safe and does not execute the transfer script.
    """
    tree = ast.parse(script_path.read_text(encoding="utf-8"), filename=str(script_path))
    targets: set[str] = set()
    assigned_paths: dict[str, str] = {}
    writer_calls = {"ensure", "touch", "append_if_missing", "patch"}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        path = _path_from_join_expr(node.value)
        if not path:
            continue
        for target in node.targets:
            if isinstance(target, ast.Name):
                assigned_paths[target.id] = path.replace("\\", "/")

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not node.args:
            continue
        func = node.func
        if isinstance(func, ast.Name):
            func_name = func.id
        else:
            continue
        if func_name not in writer_calls:
            continue
        first_arg = node.args[0]
        if isinstance(first_arg, ast.Name):
            path = assigned_paths.get(first_arg.id)
        else:
            path = _path_from_join_expr(first_arg)
        if path:
            targets.add(path.replace("\\", "/"))
    return sorted(targets)


def ticket_script_paths(script_paths: list[Path]) -> list[str]:
    """Merge output paths from one or more transfer scripts."""
    paths: set[str] = set()
    for script_path in script_paths:
        if not script_path.is_file():
            raise FileNotFoundError(f"--ticket-script not found: {script_path}")
        extracted = extract_ticket_script_paths(script_path)
        if not extracted:
            print(
                f"WARNING: no writable BACKEND/ROOT paths found in {script_path}",
                file=sys.stderr,
            )
        paths.update(extracted)
    return sorted(paths)


def _pathspec(paths: list[str] | None) -> list[str]:
    return ["--", *paths] if paths else []


def _scope_label(paths: list[str] | None) -> str:
    return f" scoped to {len(paths)} ticket file(s)" if paths else ""


def git_root(start: Path | None = None) -> Path:
    root = run_git(["rev-parse", "--show-toplevel"], cwd=start or Path.cwd())
    return Path(root)


def resolve_ref(repo: Path, ref: str) -> str:
    """Resolve ref to full SHA; fails if missing."""
    return run_git(["rev-parse", "--verify", ref], cwd=repo)


def cmd_diff(from_ref: str, to_ref: str, repo: Path, paths: list[str] | None) -> int:
    fr = resolve_ref(repo, from_ref)
    to = resolve_ref(repo, to_ref)
    print(
        f"=== Diff: {from_ref} ({fr[:12]}…) → {to_ref} ({to[:12]}…)"
        f"{_scope_label(paths)} ===\n"
    )
    print("=== Changed files ===")
    print(run_git(["diff", "--name-status", from_ref, to_ref, *_pathspec(paths)], cwd=repo))
    print()
    print(f"=== Commits on {to_ref} not in {from_ref} ({from_ref}..{to_ref}) ===")
    print(run_git(["log", "--oneline", f"{from_ref}..{to_ref}"], cwd=repo) or "(none)")
    print()
    print("=== Stats ===")
    print(run_git(["diff", "--stat", from_ref, to_ref, *_pathspec(paths)], cwd=repo))
    return 0


def cmd_patch(
    from_ref: str,
    to_ref: str,
    repo: Path,
    out_path: Path,
    unified: int,
    paths: list[str] | None,
) -> int:
    """Write unified diff for changed lines only when unified=0 (no surrounding context)."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fr = resolve_ref(repo, from_ref)
    to = resolve_ref(repo, to_ref)
    with out_path.open("w", encoding="utf-8", newline="\n") as f:
        r = subprocess.run(
            [
                "git",
                "diff",
                f"-U{unified}",
                "--no-ext-diff",
                from_ref,
                to_ref,
                *_pathspec(paths),
            ],
            cwd=repo,
            stdout=f,
        )
    if r.returncode != 0:
        print("ERROR: git diff failed (see messages above).", file=sys.stderr)
        return r.returncode
    print(
        f"Unified diff written to {out_path.resolve()} (-U{unified}; unchanged "
        f"context lines omitted when 0;{_scope_label(paths)})\n"
        f"  ({from_ref} {fr[:12]}… → {to_ref} {to[:12]}…)"
    )
    return 0


HUNK_HEADER_RE = re.compile(r"^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@")


def _display_path_from_diff_git(line: str) -> str:
    """Second path from ``diff --git`` line (prefer ``b/`` side)."""
    m = re.match(r"^diff --git (.+) (.+)$", line)
    if not m:
        return "?"
    a_raw, b_raw = m.group(1), m.group(2)
    if b_raw != "/dev/null":
        return b_raw[2:] if b_raw.startswith("b/") else b_raw
    return a_raw[2:] if a_raw.startswith("a/") else a_raw


def format_git_diff_as_line_numbers(diff_text: str) -> str:
    """Turn unified diff into ``-oldline:`` / ``+newline:`` lines (no context)."""
    out: list[str] = []
    lines = diff_text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("diff --git"):
            out.append("")
            out.append(f"=== {_display_path_from_diff_git(line)} ===")
            i += 1
            continue
        if line.startswith("Binary files ") and line.endswith(" differ"):
            out.append(line)
            i += 1
            continue
        if line.startswith("@@"):
            m = HUNK_HEADER_RE.match(line)
            if not m:
                i += 1
                continue
            old_line = int(m.group(1)) - 1
            new_line = int(m.group(2)) - 1
            i += 1
            while i < len(lines):
                l = lines[i]
                if l.startswith("diff --git") or l.startswith("@@"):
                    break
                if l.startswith("Binary files"):
                    break
                if not l:
                    i += 1
                    continue
                kind = l[0]
                body = l[1:]
                if kind == " ":
                    old_line += 1
                    new_line += 1
                elif kind == "-":
                    old_line += 1
                    out.append(f"-{old_line}: {body}")
                elif kind == "+":
                    new_line += 1
                    out.append(f"+{new_line}: {body}")
                elif kind == "\\":
                    pass
                else:
                    pass
                i += 1
            continue
        i += 1

    text = "\n".join(out).strip()
    return text + ("\n" if text else "")


def cmd_lines(
    from_ref: str,
    to_ref: str,
    repo: Path,
    out_target: Path | str | None,
    unified: int,
    paths: list[str] | None,
) -> int:
    diff_text = subprocess.check_output(
        [
            "git",
            "diff",
            f"-U{unified}",
            "--no-color",
            "--no-ext-diff",
            from_ref,
            to_ref,
            *_pathspec(paths),
        ],
        cwd=repo,
        text=True,
        errors="replace",
    )
    body = format_git_diff_as_line_numbers(diff_text)
    if out_target is None or str(out_target) == "-":
        sys.stdout.write(body)
    else:
        Path(out_target).write_text(body, encoding="utf-8", newline="\n")
        print(f"Line-number listing written to {Path(out_target).resolve()}")
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


def cmd_report(
    from_ref: str,
    to_ref: str,
    repo: Path,
    out_path: Path,
    paths: list[str] | None,
) -> int:
    from_sha = resolve_ref(repo, from_ref)
    to_sha = resolve_ref(repo, to_ref)
    changed_raw = run_git(["diff", "--name-status", from_ref, to_ref, *_pathspec(paths)], cwd=repo)
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
        "path_filter": paths or [],
        # Legacy keys for older consumers
        "snapshot_commit": from_sha,
        "current_head": to_sha,
        "commits_since_snapshot": len(commits),
    }

    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(
        f"Report written to {out_path} — {len(changes)} file changes, "
        f"{len(commits)} commits ({from_ref} → {to_ref}){_scope_label(paths)}"
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
    with_lines: bool,
    lines_out: str,
    unified: int,
    paths: list[str] | None,
) -> int:
    cmd_diff(from_ref, to_ref, repo, paths)
    print()
    cmd_report(from_ref, to_ref, repo, report_path, paths)
    print()
    cmd_show(report_path)
    if not skip_patch:
        print()
        cmd_patch(from_ref, to_ref, repo, patch_path, unified, paths)
    if with_lines:
        print()
        lo = None if lines_out == "-" else Path(lines_out)
        cmd_lines(from_ref, to_ref, repo, lo, unified, paths)
    return 0


def companion_wrappers(this_script: Path) -> dict[str, str]:
    """Thin wrappers: Unix (.sh / helper .py) and Windows CMD (.cmd).

    CMD files use ``py -3`` when available, else ``python``, so they work from
    Command Prompt without Git Bash.
    """
    py = this_script.name
    unix = {
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
    # Windows Command Prompt (cmd.exe) — double-click or: diff-from-snapshot.cmd --fetch
    win = {
        "diff-from-snapshot.cmd": f"""@echo off
cd /d "%~dp0"
where py >nul 2>nul
if not errorlevel 1 goto RUN_PY
python "%~dp0{py}" diff %*
goto EOF
:RUN_PY
py -3 "%~dp0{py}" diff %*
:EOF
""",
        "apply-sync.cmd": f"""@echo off
cd /d "%~dp0"
where py >nul 2>nul
if not errorlevel 1 goto RUN_PY
python "%~dp0{py}" show %*
goto EOF
:RUN_PY
py -3 "%~dp0{py}" show %*
:EOF
""",
        "generate-sync-report.cmd": f"""@echo off
cd /d "%~dp0"
where py >nul 2>nul
if not errorlevel 1 goto RUN_PY
python "%~dp0{py}" report %*
goto EOF
:RUN_PY
py -3 "%~dp0{py}" report %*
:EOF
""",
    }
    unix.update(win)
    return unix


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
            body = content.replace("\n", "\r\n") if name.endswith(".cmd") else content
            p.write_text(body, encoding="utf-8", newline="" if name.endswith(".cmd") else "\n")
            if not name.endswith(".cmd"):
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
        choices=("lines", "diff", "patch", "report", "show", "full", "publish-rag-eval"),
        help="lines | diff | patch | report | show | full | publish-rag-eval (default: full)",
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
    parser.add_argument(
        "--lines-out",
        type=str,
        default="sync_lines.txt",
        metavar="PATH",
        help="For 'lines' / --with-lines: output file, or '-' for stdout (default: sync_lines.txt)",
    )
    parser.add_argument(
        "--unified",
        type=int,
        default=0,
        metavar="N",
        help=(
            "git diff -U N for patch file, lines listing, and full (default: 0 = no "
            "unchanged context lines around edits; use 3 if you need git apply-friendly hunks)"
        ),
    )
    parser.add_argument(
        "--with-lines",
        action="store_true",
        help="With 'full': also write compact -N:/+N: listing (--lines-out, --unified)",
    )
    parser.add_argument(
        "--ticket-script",
        type=Path,
        action="append",
        default=[],
        metavar="PATH",
        help=(
            "Restrict output to files written/touched by a Python transfer script. "
            "Repeat for multiple tickets."
        ),
    )
    parser.add_argument(
        "--print-ticket-paths",
        action="store_true",
        help="Print files extracted from --ticket-script before running the command.",
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
    try:
        scoped_paths = ticket_script_paths(args.ticket_script) if args.ticket_script else []
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    if args.print_ticket_paths and scoped_paths:
        print("=== Ticket-scoped files ===")
        for p in scoped_paths:
            print(p)
        print()

    if args.command == "diff":
        return cmd_diff(from_ref, to_ref, repo, scoped_paths)
    if args.command == "lines":
        lo = None if args.lines_out == "-" else Path(args.lines_out)
        return cmd_lines(from_ref, to_ref, repo, lo, args.unified, scoped_paths)
    if args.command == "patch":
        return cmd_patch(from_ref, to_ref, repo, patch_path, args.unified, scoped_paths)
    if args.command == "report":
        return cmd_report(from_ref, to_ref, repo, report_path, scoped_paths)
    if args.command == "show":
        return cmd_show(report_path)
    if args.command == "full":
        return cmd_full(
            from_ref,
            to_ref,
            repo,
            report_path,
            patch_path,
            args.no_patch,
            args.with_lines,
            args.lines_out,
            args.unified,
            scoped_paths,
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
