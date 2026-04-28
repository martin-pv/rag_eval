#!/usr/bin/env python3
"""
ensure-worktree-branches.py — Ensure ticket/worktree branches exist locally off main.

For each directory under `<repo>/.worktrees/`, expects a branch with the same name.
If `refs/heads/<name>` does not exist, creates it with:

    git branch <name> <base>

Default base ref is `main`. Safe with `--dry-run`. Ignores `.git` and dot-directories.

Optional:
  --branches-file PATH    Extra branch names (one per line; # comments allowed).
  --skip NAMES            Comma-separated branch names to skip.
  --base REF              Branch to branch off (default: main).

Run from repo root (Pratt-Backend):

    python3 devscripts/ensure-worktree-branches.py
    python3 devscripts/ensure-worktree-branches.py --dry-run

Companion to update-main-sync (ticket hygiene).
See also: devscripts/update-main-sync/update-main-sync.py
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def run_git(args: list[str], cwd: Path, *, check: bool = True) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=check,
        capture_output=True,
        text=True,
    ).stdout.strip()


def git_root() -> Path:
    return Path(run_git(["rev-parse", "--show-toplevel"], Path.cwd()))


def branch_exists(repo: Path, name: str) -> bool:
    r = subprocess.run(
        ["git", "show-ref", "--verify", f"refs/heads/{name}"],
        cwd=repo,
        capture_output=True,
        check=False,
    )
    return r.returncode == 0


def collect_branch_names(worktrees_root: Path, branches_file: Path | None) -> list[str]:
    names: set[str] = set()
    if worktrees_root.is_dir():
        for p in sorted(worktrees_root.iterdir()):
            if not p.is_dir():
                continue
            if p.name.startswith("."):
                continue
            names.add(p.name)

    if branches_file and branches_file.is_file():
        for raw in branches_file.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            names.add(line)

    return sorted(names)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Create missing worktree ticket branches from main.")
    parser.add_argument(
        "--repo",
        type=Path,
        default=None,
        help="Git repository root (default: cwd)",
    )
    parser.add_argument(
        "--worktrees-root",
        type=Path,
        default=None,
        metavar="DIR",
        help="Directory holding one folder per ticket branch (default: REPO/.worktrees)",
    )
    parser.add_argument(
        "--branches-file",
        type=Path,
        default=None,
        metavar="PATH",
        help="Optional file with extra branch names, one per line",
    )
    parser.add_argument(
        "--base",
        default="main",
        metavar="REF",
        help="Branch or SHA to create missing branches from (default: main)",
    )
    parser.add_argument(
        "--skip",
        default="",
        help="Comma-separated branch names to ignore",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print actions only",
    )
    args = parser.parse_args(argv)

    repo = args.repo.resolve() if args.repo else git_root()
    worktrees_root = args.worktrees_root
    if worktrees_root is None:
        worktrees_root = repo / ".worktrees"

    skip_set = {s.strip() for s in args.skip.split(",") if s.strip()}

    try:
        base_sha = run_git(["rev-parse", "--verify", args.base], repo)
    except subprocess.CalledProcessError:
        print(f"ERROR: base ref {args.base!r} does not exist in this repo.", file=sys.stderr)
        return 1

    names = collect_branch_names(worktrees_root, args.branches_file)

    if not names:
        print(
            f"No branch names found under {worktrees_root} "
            f"({'none provided via --branches-file' if not args.branches_file else 'empty'}).",
            file=sys.stderr,
        )
        return 1

    created = 0
    skipped = 0
    existed = 0

    print(f"Repo:   {repo}")
    print(f"Base:   {args.base} ({base_sha[:12]}…)")
    print(f"Source: {worktrees_root}")
    print()

    for name in names:
        if name in skip_set:
            print(f"[skip-list] {name}")
            skipped += 1
            continue
        if name == args.base:
            print(f"[skip same-as-base] {name}")
            skipped += 1
            continue

        if branch_exists(repo, name):
            print(f"[exists]  {name}")
            existed += 1
            continue

        if args.dry_run:
            print(f"[would create] git branch {name} {args.base}")
        else:
            subprocess.run(
                ["git", "branch", name, args.base],
                cwd=repo,
                check=True,
            )
            print(f"[created] git branch {name} {args.base}")
        created += 1

    print()
    print(f"Done — existed: {existed}, created: {created}, skipped: {skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
