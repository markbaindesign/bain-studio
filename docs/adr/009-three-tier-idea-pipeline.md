---
date: 2026-07-03
status: accepted
tags: [adr]
---

# ADR 009 — Three-Tier Idea Pipeline

## Context

Studio tooling ideas, client feature requests, and QA issues were scattering across Obsidian misc.md, BSTD Asana tasks, spec drafts, and someday-maybe.md with no repeatable path from capture to built-and-documented. The existing spec nursery (`drafts/ → candidates/ → commission`) had no front door and no per-project feature workflow.

## Decision

Adopt a three-tier pipeline with a clear capture layer (Obsidian hashtags) routing into three distinct workflows:

```
OBSIDIAN (capture layer)
    ↓ #project / #skill / #script  →  Greenhouse (new studio tools)
    ↓ #feature {PREFIX}            →  Per-project feature backlog
    ↓ #issue                       →  QA inbox (existing)
```

### Tier 1 — Studio Greenhouse

New project and tool ideas that need to grow into commissioned work.

- Seeds live as tasks in the `Greenhouse` section of the BSTD Asana project
- `obsidian_collector.py` feeds them from `#project`, `#skill`, and `#script` tags
- `/nurture` triages them: quick pass or full grill-me interview → spec in `specs/drafts/`
- `someday-maybe.md` is a live input scanned by `/nurture`, not a dead-end file
- Graduation path: `/nurture` → `/review-spec` → `/commission` → new Asana project

### Tier 2 — Per-project Feature Pipeline

Feature requests on active client projects that need scoping, a branch, and delivery.

- Captured from Obsidian `#feature {PREFIX}` tags or via `/feature` skill directly
- Scope threshold: <4h = task only; ≥4h = lightweight spec written to `.claude/features/{slug}.md`
- `/feature` creates the Asana task in the project's TO DO section via the mirror/sync pattern
- Feature counter per project mints refs: `{PREFIX}-FEAT-001`, `{PREFIX}-FEAT-002`, etc.
- Counter stored in `.claude/feature-counter.json` (gitignored per-project)

### Tier 3 — Issues (existing)

QA bugs and regressions handled by the existing `/issue` skill. Unchanged.

## Alternatives considered

- **Single Asana inbox for all ideas**: no separation between client features and studio tooling — conflates concerns and makes triage harder
- **Obsidian-only capture**: ideas stay in notes, never reach Asana, never get built
- **Immediate Asana task creation on capture**: no review step; noisy backlog

## Consequences

- `obsidian_collector.py` extended to route `#feature {PREFIX}` tags to `{CONTENT_DIR}/pipeline/feature-backlog/{PREFIX}.md` staging files
- `/feature` skill built at `.claude/skills/feature/SKILL.md`
- `/nurture` updated to scan Greenhouse section from mirror and `someday-maybe.md`
- Greenhouse section in BSTD Asana created manually by Mark

## See also

- Spec: `context/internal/greenhouse-feature-pipeline.md`
- `/feature` skill: `.claude/skills/feature/SKILL.md`
- `/nurture` skill: `.claude/skills/nurture/SKILL.md`
- ADR 003: multi-agent studio architecture
