---
name: end-session
description: Wrap up the current project session. Commits pending changes, syncs the mirror for this project only, and writes a one-paragraph handoff note so the next session can pick up cleanly. Lighter and faster than studio-shutdown (which is end-of-day, all projects).
allowed-tools: [Read, Write, Edit, Bash]
---

# End Session

Wrap up the current project session cleanly. Scoped to the project in the current working directory.

## Steps

### 1. Identify the project

Read `CLAUDE.md` in the current directory. Extract:
- `ASANA_TASK_PREFIX` (e.g. `NORE`)
- `ASANA_PROJECT_NAME`

If no `CLAUDE.md`, abort: "Not in a recognised project directory. cd into the project first."

### 2. Summarise what happened this session

Before touching anything, write a brief internal summary of what was done this session. Draw from:
- The conversation so far (tasks discussed, code changed, decisions made)
- Any tasks mentioned as complete or in-progress

This becomes the handoff note. Keep it to 3-5 bullet points.

### 3. Check git status

```bash
git status --short
git diff --stat
```

If there are uncommitted changes:
- Stage and commit them with a message that summarises the session work
- Use the standard commit format: `type: short description`
- Examples: `feat: add cloudways ADR`, `docs: update BSTD-039 progress notes`, `fix: correct staging workflow`
- Do NOT use `--no-verify`

If working tree is clean, note it.

### 4. Update mirror progress notes

For each task that was actively worked on this session, update its `Progress:` line in `.claude/asana-mirror.md`:

```
- **Progress:** {What was done today} {YYYY-MM-DD}.
```

Be specific - "Research complete, ADR written" not "Worked on task".

Only update tasks that were actually touched. Do not modify tasks that weren't part of this session.

### 5. Sync the mirror

Push the updated mirror to Asana for this project only:

```bash
cd /media/data/dev/bain-studio && python3 studio/sync.py --project {PREFIX}
```

If sync fails, note it but do not block - the mirror edit is the source of truth.

### 6. Write the handoff note

Append to `.claude/pm-log.md` in the **bain-studio root** (not the current project). Create the file if it doesn't exist.

Format:

```markdown
## {YYYY-MM-DD HH:MM} — {PROJECT_NAME} session

**Done:**
- {bullet 1}
- {bullet 2}
- {bullet 3}

**Next action:** {single most important next step}

**Blockers:** {any blockers, or "None"}
```

### 7. Output the end-session report

```
## End Session — {PROJECT_NAME} — {YYYY-MM-DD HH:MM}

### Committed
{commit hash + message, or "Working tree was clean"}

### Mirror
{which tasks were updated, or "No changes"}

### Sync
{synced OK / failed / skipped}

### Handoff
{paste the handoff note content}
```

Keep it under 20 lines. The handoff note is the most important part — make it useful for a cold re-entry.
