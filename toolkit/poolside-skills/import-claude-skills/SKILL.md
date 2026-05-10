---
name: import-claude-skills
description: Import or sync Agent Skills from local Claude directories into Poolside (~/.config/poolside/skills or .poolside/skills) or into rag_eval toolkit/claude-skills for git bundling. Use when setting up Poolside on a new machine, copying from ~/.claude/skills on Mac, %USERPROFILE%\.claude\skills on Windows, .agents/skills, or clawd/skills, or refreshing the repo bundle with symlink-free copies.
---

# Import Claude skills → Poolside / rag_eval

## When to use

- You have skills under **Claude / Clawd / OpenClaw** and want them in **Poolside** or in the **`rag_eval`** repo for the Windows PC.
- You need **flat copies** (no symlinks) so `git clone` and Poolside sandboxes see full files.

## Source locations (check what exists)

| Platform | Typical paths |
|----------|----------------|
| Windows | `%USERPROFILE%\.claude\skills\`, `%USERPROFILE%\.agents\skills\`, `%USERPROFILE%\clawd\skills\` (or `~\clawd\skills`) |
| macOS / Linux | `~/.claude/skills/`, `~/.agents/skills/`, `~/clawd/skills/` |

Each skill is a **folder** containing **`SKILL.md`** with YAML frontmatter. **`name:`** in frontmatter should match the **folder name** (Poolside / Agent Skills convention). Fix `Brave-Search` vs `brave-search` style mismatches before copying.

## Destination locations

| Goal | Path |
|------|------|
| Poolside global | `%USERPROFILE%\.config\poolside\skills\` (Windows) or `~/.config/poolside/skills/` |
| Poolside project / sandboxes | `.poolside\skills\` or `.poolside/skills/` at workspace root |
| rag_eval git bundle | `<rag_eval>\toolkit\claude-skills\<skill-name>\` |

## Windows — copy entire skill trees (no Git)

**PowerShell** — copies each subfolder of `.claude\skills` into Poolside global (skip non-directories):

```powershell
$src = Join-Path $env:USERPROFILE ".claude\skills"
$dest = Join-Path $env:USERPROFILE ".config\poolside\skills"
New-Item -ItemType Directory -Force -Path $dest | Out-Null
Get-ChildItem -Path $src -Directory | ForEach-Object {
  Copy-Item -Path $_.FullName -Destination (Join-Path $dest $_.Name) -Recurse -Force
}
```

Repeat with `$src = Join-Path $env:USERPROFILE ".agents\skills"` if present.

**Symlinks:** Windows junctions/symlinks may copy as links depending on PowerShell version. For a **fully materialized** tree (recommended before `git add` in `rag_eval`), prefer **WSL** `rsync -aL` or duplicate folders manually after resolving link targets.

## macOS / Linux — materialize symlinks into rag_eval

From a machine that has your live skills:

```bash
RAG_EVAL=/path/to/rag_eval/toolkit/claude-skills
mkdir -p "$RAG_EVAL"
for d in "$HOME/.claude/skills"/*; do
  [ -d "$d" ] || continue
  name=$(basename "$d")
  rsync -aL "$d/" "$RAG_EVAL/$name/"
done
```

`-L` follows symlinks so Clawd-linked skills become real files.

## After import

1. Open Poolside, run **`/skills`** and confirm each skill appears.
2. If a skill **does not load**, validate **`SKILL.md` frontmatter** and **folder name**.
3. For **rag_eval** contributions, see **`toolkit/claude-skills/README.md`** (refresh script, license/API notes).

## Do not

- Commit API keys or `.env`; strip machine-specific paths if pasting examples into shared repos.
- Assume **macOS-only** CLI skills work unchanged on Windows — note limitations in your prompt or fork the skill.
