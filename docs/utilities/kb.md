---
tags: [skill]
invoke: /kb
description: Add or update studio knowledge base entries — routes to the correct docs/ location by type
---

# kb — Studio Knowledge Base

Invoke when something new has been built or needs documenting. Routes the entry to the right place in `docs/` based on type.

## Invoke

```
/kb add <thing>       — add a new entry
/kb update <thing>    — update an existing entry
/kb find <thing>      — locate an existing entry
```

No args — skill will ask what to document.

## What it handles

| Type | Destination |
|---|---|
| God / agent | `docs/gods/{god}/` |
| Household member | `docs/gods/{god}/{member}.md` |
| Checklist | `docs/gods/{god}/{name}-checklist.md` |
| Skill / utility | `docs/utilities/{name}.md` |
| ADR | `docs/adr/ADR-NNN-{slug}.md` |
| Project | `docs/projects/{prefix}.md` |

## Notes

- Writes correct YAML frontmatter automatically so entries appear in Obsidian bases indexes
- Suggests global symlink if the new skill should be available outside bain-studio
- ADRs are append-only — status can move to `superseded`, never deleted
