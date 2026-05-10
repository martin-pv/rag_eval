# Toolkit — skills, workflow, Poolside

Bundled **useful defaults** for humans and agents working across **`rag_eval`** and **Pratt-Backend**.

| Item | Purpose |
|------|---------|
| [POOLSIDE.md](./POOLSIDE.md) | Install **skills** for Poolside (and compatible Agent Skills tools) |
| [WORKFLOW.md](./WORKFLOW.md) | Backend cwd, branches, testing, `uv` |
| [poolside-skills/](./poolside-skills/) | Ready-to-copy **`SKILL.md`** folders |

## Quick copy (Poolside global skills)

```bash
mkdir -p ~/.config/poolside/skills
cp -R /path/to/rag_eval/toolkit/poolside-skills/* ~/.config/poolside/skills/
```

## Quick copy (project-local, good for sandboxes)

From the **backend** or **rag_eval** repo root (if you keep rag_eval inside the workspace):

```bash
mkdir -p .poolside/skills
cp -R /path/to/rag_eval/toolkit/poolside-skills/* .poolside/skills/
```

Then in Poolside Assistant or `pool code`, use **`/skills`** to attach or verify.

## Related

- Root **[AGENTS.md](../AGENTS.md)** — repo-wide agent rules  
- **[eval_v2/docs/README.md](../eval_v2/docs/README.md)** — v2 ticket docs and merge order  
