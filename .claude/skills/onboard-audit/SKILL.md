---
name: onboard-audit
description: Audits every active project against the onboarding checklist — surfaces what's missing across all projects.
allowed-tools: [Read, Bash]
---

# Onboard Audit

Checks every registered project against the studio onboarding checklist and reports gaps.

## Steps

### 1. Load the project registry

Read `studio/projects.md`. Extract every row from the table: prefix, name, path, Asana GID, status.

### 2. Run the checklist per project

For each project, check the following. Mark each ✓ (present), ✗ (missing), or ~ (stale):

**Infrastructure**
- [ ] Path exists on disk
- [ ] `CLAUDE.md` present at project root
- [ ] `ASANA_PROJECT_GID` set in `CLAUDE.md`
- [ ] `ASANA_TASK_PREFIX` set in `CLAUDE.md`
- [ ] `.claude/asana-mirror.md` exists
- [ ] Mirror synced within last 7 days (check `Last synced:` line at top of mirror)
- [ ] `.claude/settings.json` exists

**Project hygiene**
- [ ] `.claude/open-questions.md` exists
- [ ] `.claude/inbox/` directory exists
- [ ] At least one ADR in `.claude/adr/` or `docs/adr/`

**Mnemosyne**
- [ ] Row exists in `context/portfolio/project-database.csv` — match on project name or prefix

### 3. Output the report

Produce a compact table per project, then a summary of the worst offenders.

```
## Onboard Audit — YYYY-MM-DD

### MCF — Mhairi McFarlane
✓ path  ✓ CLAUDE.md  ✓ Asana GID  ✓ prefix  ✓ mirror  ~ mirror stale (8d)  ✓ settings
✓ open-questions  ✓ inbox  ✗ ADR
✗ Mnemosyne entry

### PIPE — Upwork Pipeline
...

---
### Gaps summary
| Project | Missing |
|---------|---------|
| MCF     | ADR, Mnemosyne entry |
| ...     | ...     |
```

Flag any project where more than 3 items are missing as **needs attention**.

## Notes

- Mirror staleness threshold is 7 days — projects synced by Hermes on a schedule should never hit this.
- ADR absence is a soft flag — new projects may not have any yet. Flag only if the project is older than 30 days (check mirror's first sync date or project-database.csv start date).
- Mnemosyne check: scan `context/portfolio/project-database.csv` for a row whose Project Name or Prefix column matches. If the CSV doesn't exist yet, note it and skip.
