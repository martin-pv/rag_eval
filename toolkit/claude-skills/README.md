# Claude-compatible skills (bundled)

This directory contains **Agent Skills**–format folders copied from **Martin’s Mac** Claude setup (`~/.claude/skills`, `~/.agents/skills`, `~/clawd/skills`) with symlinks **resolved**, so the repo is self-contained on **Windows** and after `git clone`.

**Purpose:** Use with [Poolside](https://docs.poolside.ai/skills), Cursor, OpenClaw, or any tool that reads `SKILL.md` + YAML frontmatter.

## Included skills (23)

| Folder | Notes |
|--------|--------|
| `agent-browser` | Browser automation CLI patterns |
| `brave-search` | Web search / content (API-oriented) |
| `caveman`, `caveman-commit`, `caveman-help`, `caveman-review` | Ultra-compressed style, commits, PR review |
| `code-review` | Security / performance / quality review |
| `create-skill` | Minimal skill template |
| `decision-toolkit` | Structured decisions |
| `deep-research` | Deep research workflow |
| `fact-checker` | Evidence-style verification |
| `find-skills` | Discovering skills |
| `gh-issues` | GitHub issues / agent workflows |
| `github` | `gh` CLI usage |
| `humanizer` | Naturalize AI-ish prose |
| `karpathy-guidelines` | Coding discipline, less LLM slop |
| `mcp-builder` | Building MCP servers |
| `mcporter` | MCP CLI |
| `ngrok` | Tunnels |
| `openrouter` | OpenRouter routing |
| `process-interviewer` | Interview-before-build planning |
| `prompt-master` | Prompt optimization |
| `skill-creator` | Full skill authoring guide |

## Poolside / path rules

- Each subfolder must contain **`SKILL.md`** with frontmatter **`name`** matching the **folder name** (e.g. `brave-search/`, not `Brave-Search/`).
- Copy into **`%USERPROFILE%\.config\poolside\skills`** (Windows) or **`~/.config/poolside/skills`** (Unix), or project **`.poolside/skills`**.

**PowerShell (global, copy rag_eval + bundled skills):**

```powershell
$dest = Join-Path $env:USERPROFILE ".config\poolside\skills"
New-Item -ItemType Directory -Force -Path $dest | Out-Null
Copy-Item -Path "C:\work\rag_eval\toolkit\poolside-skills\*" -Destination $dest -Recurse -Force
Copy-Item -Path "C:\work\rag_eval\toolkit\claude-skills\*" -Destination $dest -Recurse -Force
```

## Caveats

- Some skills reference **macOS-only** CLIs or paths; on Windows use equivalents or skip those sections.
- **API keys** are not stored here; skills that need keys expect env vars or your own config.
- **License:** Third-party skill content may follow upstream licenses (ClawdHub, community packs). Verify before redistributing outside your org.

## Refreshing from a Mac

To update this bundle from the laptop that has Claude skills installed:

```bash
DEST=/path/to/rag_eval/toolkit/claude-skills
SKILLS=(karpathy-guidelines code-review mcp-builder process-interviewer prompt-master decision-toolkit deep-research fact-checker find-skills gh-issues humanizer agent-browser ngrok caveman caveman-commit caveman-review caveman-help github Brave-Search create-skill skill-creator mcporter openrouter)
for s in "${SKILLS[@]}"; do
  rm -rf "$DEST/$s" "$DEST/brave-search"
  if [[ -e "$HOME/.claude/skills/$s" ]]; then rsync -aL "$HOME/.claude/skills/$s/" "$DEST/$s/"
  elif [[ -e "$HOME/.agents/skills/$s" ]]; then rsync -aL "$HOME/.agents/skills/$s/" "$DEST/$s/"
  elif [[ -e "$HOME/clawd/skills/$s" ]]; then rsync -aL "$HOME/clawd/skills/$s/" "$DEST/$s/"
  fi
done
# Poolside: brave-search folder name must match frontmatter
[[ -d "$DEST/Brave-Search" ]] && mv "$DEST/Brave-Search" "$DEST/brave-search"
```

Then fix **`code-review`** frontmatter `name: code-review` if upstream changed it, and commit.
