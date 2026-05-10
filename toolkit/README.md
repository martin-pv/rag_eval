# Toolkit — skills, workflow, Poolside

Bundled **useful defaults** for humans and agents working across **`rag_eval`** and **Pratt-Backend**. These instructions assume a **Windows PC** is common; macOS/Linux variants are included where they differ.

| Item | Purpose |
|------|---------|
| [POOLSIDE.md](./POOLSIDE.md) | Install **skills** for Poolside (paths on Windows vs Unix) |
| [WORKFLOW.md](./WORKFLOW.md) | Backend cwd, branches, testing, `py -3` / `uv` |
| [poolside-skills/](./poolside-skills/) | **rag_eval–specific** skills: transfers, **import from `.claude`**, **RAG / RAGAS** — see [poolside-skills/README.md](./poolside-skills/README.md) |
| [claude-skills/](./claude-skills/) | **23 bundled** skills from Claude (code review, MCP, GitHub, caveman, …) — see [claude-skills/README.md](./claude-skills/README.md) |

## Windows — copy skills (Poolside global)

Replace `C:\work\rag_eval` with your clone path. Skills end up under **`%USERPROFILE%\.config\poolside\skills\`**.

**PowerShell (poolside-skills + Claude bundle):**

```powershell
$dest = Join-Path $env:USERPROFILE ".config\poolside\skills"
New-Item -ItemType Directory -Force -Path $dest | Out-Null
Copy-Item -Path "C:\work\rag_eval\toolkit\poolside-skills\*" -Destination $dest -Recurse -Force
Copy-Item -Path "C:\work\rag_eval\toolkit\claude-skills\*" -Destination $dest -Recurse -Force
```

**PowerShell (poolside-skills only):**

```powershell
$dest = Join-Path $env:USERPROFILE ".config\poolside\skills"
New-Item -ItemType Directory -Force -Path $dest | Out-Null
Copy-Item -Path "C:\work\rag_eval\toolkit\poolside-skills\*" -Destination $dest -Recurse -Force
```

**Command Prompt:**

```bat
mkdir "%USERPROFILE%\.config\poolside\skills" 2>nul
xcopy /E /I /Y "C:\work\rag_eval\toolkit\poolside-skills\*" "%USERPROFILE%\.config\poolside\skills\"
xcopy /E /I /Y "C:\work\rag_eval\toolkit\claude-skills\*" "%USERPROFILE%\.config\poolside\skills\"
```

**Command Prompt (poolside-skills only):**

```bat
mkdir "%USERPROFILE%\.config\poolside\skills" 2>nul
xcopy /E /I /Y "C:\work\rag_eval\toolkit\poolside-skills\*" "%USERPROFILE%\.config\poolside\skills\"
```

## Windows — project-local skills (sandboxes)

From the folder Poolside opens as the workspace (backend or `rag_eval`):

```powershell
New-Item -ItemType Directory -Force -Path ".poolside\skills" | Out-Null
Copy-Item -Path "C:\work\rag_eval\toolkit\poolside-skills\*" -Destination ".poolside\skills" -Recurse -Force
Copy-Item -Path "C:\work\rag_eval\toolkit\claude-skills\*" -Destination ".poolside\skills" -Recurse -Force
```

Then in Poolside Assistant or `pool code`, use **`/skills`** to attach or verify.

## macOS / Linux — quick copy (global)

```bash
mkdir -p ~/.config/poolside/skills
cp -R /path/to/rag_eval/toolkit/poolside-skills/* ~/.config/poolside/skills/
cp -R /path/to/rag_eval/toolkit/claude-skills/* ~/.config/poolside/skills/
```

## Related

- Root **[AGENTS.md](../AGENTS.md)** — repo-wide agent rules (Windows-first notes)  
- **[poolside-skills/README.md](./poolside-skills/README.md)** — index of rag_eval-specific skills (transfers, RAGAS, import from `.claude`)  
- **[claude-skills/README.md](./claude-skills/README.md)** — bundled Claude skills, refresh script, Poolside `name` = folder rule
