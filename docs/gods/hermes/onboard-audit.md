---
tags: [skill]
god: hermes
invoke: /onboard-audit
description: Audits every active project against the onboarding checklist — surfaces what's missing across all projects
---

# onboard-audit

Runs the onboarding checklist against every project in the studio registry and reports gaps.

## Invoke

```
/onboard-audit
```

## Checklist

**Infrastructure**
- Path exists on disk
- `CLAUDE.md` present with `ASANA_PROJECT_GID` and `ASANA_TASK_PREFIX`
- `.claude/asana-mirror.md` exists and synced within 7 days
- `.claude/settings.json` exists

**Project hygiene**
- `.claude/open-questions.md` exists
- `.claude/inbox/` directory exists
- At least one ADR (`.claude/adr/` or `docs/adr/`)

**Mnemosyne**
- Row in `context/portfolio/project-database.csv`

## Output

Compact per-project status with ✓ / ✗ / ~ (stale), followed by a gaps summary table. Projects with 3+ missing items are flagged as **needs attention**.
