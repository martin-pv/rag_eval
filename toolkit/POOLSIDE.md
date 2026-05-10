# Poolside setup (rag_eval toolkit)

Poolside discovers skills in:

- `~/.config/poolside/skills/<skill-name>/SKILL.md` (global)
- `.poolside/skills/<skill-name>/SKILL.md` (project)
- `.agents/skills/` (alternate)

It also scans some **Agent Skills**–compatible locations used by other tools; see [Poolside Skills](https://docs.poolside.ai/skills).

## Use this repo’s skills

1. Copy folders under **`toolkit/poolside-skills/`** into one of the directories above. Each folder must contain **`SKILL.md`** with valid YAML frontmatter (`name`, `description`); the **`name` must match the directory name**.

2. In a session, type **`/skills`** and confirm **Global** or **Project** skills appear.

3. For **local sandboxes**, prefer **`.poolside/skills/`** inside the project — user-level `~/.config/poolside/skills/` may not be mounted in the container ([Skills and sandboxes](https://docs.poolside.ai/skills#skills-and-sandboxes)).

## AGENTS.md

The **[`AGENTS.md`](../AGENTS.md)** at this repo’s root is picked up when Poolside’s workspace includes **`rag_eval`**. When the agent’s root is **only Pratt-Backend**, copy or symlink that file, or add a backend **`AGENTS.md`** that points here:

```markdown
## rag_eval

Evaluation transfer scripts and skills live in `../rag_eval` (or your path). See that repo’s `AGENTS.md` and `toolkit/`.
```

## Personal preferences

Cross-project Markdown prefs: **`~/.config/poolside/.poolside`** ([Agent instructions](https://docs.poolside.ai/agent-instructions)).
