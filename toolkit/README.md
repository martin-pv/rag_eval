# Toolkit — skills, workflow, Poolside

Bundled **useful defaults** for humans and agents working across **`rag_eval`** and **Pratt-Backend**. These instructions assume a **Windows PC** is common; macOS/Linux variants are included where they differ.

| Item | Purpose |
|------|---------|
| [POOLSIDE.md](./POOLSIDE.md) | Install **skills** for Poolside (paths on Windows vs Unix) |
| [WORKFLOW.md](./WORKFLOW.md) | Backend cwd, branches, testing, `py -3` / `uv` |
| [poolside-skills/](./poolside-skills/) | Ready-to-copy **`SKILL.md`** folders |

## Windows — copy skills (Poolside global)

Replace `C:\work\rag_eval` with your clone path. Skills end up under **`%USERPROFILE%\.config\poolside\skills\`**.

**PowerShell:**

```powershell
$dest = Join-Path $env:USERPROFILE ".config\poolside\skills"
New-Item -ItemType Directory -Force -Path $dest | Out-Null
Copy-Item -Path "C:\work\rag_eval\toolkit\poolside-skills\*" -Destination $dest -Recurse -Force
```

**Command Prompt:**

```bat
mkdir "%USERPROFILE%\.config\poolside\skills" 2>nul
xcopy /E /I /Y "C:\work\rag_eval\toolkit\poolside-skills\*" "%USERPROFILE%\.config\poolside\skills\"
```

## Windows — project-local skills (sandboxes)

From the folder Poolside opens as the workspace (backend or `rag_eval`):

```powershell
New-Item -ItemType Directory -Force -Path ".poolside\skills" | Out-Null
Copy-Item -Path "C:\work\rag_eval\toolkit\poolside-skills\*" -Destination ".poolside\skills" -Recurse -Force
```

Then in Poolside Assistant or `pool code`, use **`/skills`** to attach or verify.

## macOS / Linux — quick copy (global)

```bash
mkdir -p ~/.config/poolside/skills
cp -R /path/to/rag_eval/toolkit/poolside-skills/* ~/.config/poolside/skills/
```

## Related

- Root **[AGENTS.md](../AGENTS.md)** — repo-wide agent rules (Windows-first notes)  
- **[eval_v2/docs/README.md](../eval_v2/docs/README.md)** — v2 ticket docs and merge order; **[eval_v2/README.md](../eval_v2/README.md)** — LF line endings, `py -3`, subprocess usage on Windows  
