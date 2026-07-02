---
name: kb
description: Add or update an entry in the studio knowledge base (docs/). Routes the entry to the correct location based on type — god doc, utility, checklist, ADR, or project doc.
allowed-tools: [Read, Write, Edit, Bash]
---

# KB — Studio Knowledge Base

Add or update documentation in `docs/`. Invoked when something new has been built, changed, or needs recording.

## Usage

```
/kb add <thing>         — add a new entry
/kb update <thing>      — update an existing entry
/kb find <thing>        — locate an existing entry
```

No args — ask what to add or update.

---

## Step 1 — Parse intent

Extract from the invocation:
- **Mode**: add / update / find (default: add)
- **Subject**: what is being documented (a skill, tool, agent, checklist, decision, project)

If unclear, ask one question: "What are you documenting — a skill, tool, checklist, ADR, or project doc?"

---

## Step 2 — Route to the right location

Determine the entry type and target path:

| Type | Where it goes | Example |
|---|---|---|
| God (agent) | `docs/gods/{god-name}/{god-name}.md` | `/themis`, `/athena` |
| Household member (sub-agent) | `docs/gods/{god-name}/{member-name}.md` | Eirene under Themis |
| Checklist | `docs/gods/{god-name}/{name}-checklist.md` | performance-checklist |
| Skill (utility) | `docs/utilities/{skill-name}.md` | brand-doc, notifier |
| ADR | `docs/adr/ADR-NNN-{slug}.md` | new architectural decision |
| Project | `docs/projects/{prefix}.md` | bff.md, kf.md |
| Other / unclear | Ask before writing | — |

To find the next ADR number:
```bash
ls /media/data/dev/bain-studio/docs/adr/ | grep "^ADR-" | sort | tail -1
```

---

## Step 3 — Gather content

### For a new entry (add mode)

Ask the minimum needed to write a useful doc. Questions depend on type:

**Skill / tool:**
- What does it do? (one sentence)
- How is it invoked? (command or slash command)
- Which god owns it?
- Any notable behaviour, flags, or gotchas?

**God / agent:**
- What is its domain?
- How is it invoked?
- What does it check or produce?
- Which household members serve under it?

**Checklist:**
- Which god does it belong to?
- What triggers it?
- List the items (can be rough — you will structure them)

**ADR:**
- What decision was made?
- What were the alternatives?
- Why was this chosen?
- Any consequences or follow-up?

**Project:**
- Prefix, name, client, sector, stack, path, status

If the user provides enough in their message, skip the questions and go straight to writing.

### For an update (update mode)

Read the existing file first. Ask what changed. Make surgical edits — do not rewrite unless asked.

---

## Step 4 — Write or edit the entry

### Frontmatter format

All docs use YAML frontmatter. Match the format of the target directory:

**God / skill / utility:**
```yaml
---
tags: [skill, agent]        # or [tool], [checklist], etc.
god: {god-name}
invoke: /{skill-name}       # if applicable
command: {cli command}      # if applicable
description: One-line summary — used in Obsidian bases indexes
---
```

**ADR:**
```yaml
---
date: {YYYY-MM-DD}
status: accepted
tags: [adr]
---
```

**Project:**
```yaml
---
tags: [studio-project]
prefix: {PREFIX}
name: {Full name}
status: active
client: {client name}
sector: {sector}
stack: {stack}
path: {absolute path}
asana: "yes"
---
```

### Body

- `# Title` as the first heading
- Short description paragraph
- `## Invoke` section if it's a skill or tool
- `## What it does` or domain-specific sections
- `## Notes` for gotchas, model preferences, or context
- `## See also` with links to related docs

Keep it tight. Docs are read by agents, not users — clarity over completeness.

---

## Step 5 — Confirm and symlink if needed

After writing, confirm the file path to the user.

If the entry is a new studio skill that should be globally accessible, check if it needs symlinking:
```bash
ls ~/.claude/skills/{skill-name} 2>/dev/null || echo "not linked"
```

If not linked and it's a studio skill meant for all project contexts, suggest:
```bash
ln -s /media/data/dev/bain-studio/.claude/skills/{name} ~/.claude/skills/{name}
```

---

## Rules

- Never duplicate existing content — run find mode first if unsure
- Never write comments or meta-notes in the doc body ("added for task X", "see issue #Y")
- Frontmatter must be valid YAML — quote strings with colons
- ADRs are append-only once written — status can change to `superseded`, never delete
- Project docs are the single source of truth for path and status — update them when projects change
