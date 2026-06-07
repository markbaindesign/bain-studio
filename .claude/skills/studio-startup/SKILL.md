---
name: studio-startup
description: Morning studio startup routine. Syncs all project mirrors, runs the Abderus timing sweep, surfaces overdue tasks and harvest gaps, and gives a pulse check to start the day. Run at the beginning of any work session.
allowed-tools: [Read, Bash]
---

# Studio Startup

Run this at the start of every work session. It syncs the world, then tells you what matters today.

## Steps

### 1. Sync all project mirrors

Pull the latest Asana state for all registered projects:

```bash
cd /media/data/dev/bain-studio && python3 studio/sync.py
```

Wait for completion. If any project fails to sync, note it but continue.

### 2. Read the studio pulse

Read `/media/data/dev/bain-studio/studio/projects.md` for the registered project list.

For each active project, read its `.claude/asana-mirror.md`. Extract:
- Overdue tasks (due date in the past)
- Tasks with no Progress note
- Open questions from `.claude/open-questions.md` if it exists

### 3. Run Abderus

```
/abderus
```

Abderus surfaces harvest gaps, stale projects, pending follow-ups, and overdue obligations. Let it run and include its output in the startup report.

### 4. Check Obsidian harvest

Read `/media/data/dev/bain-studio/studio/collectors/obsidian_standup.json` if it exists.

Surface:
- How many spec stubs were created since the last sweep, and their names (strip the `project-` / `skill-` prefix for readability)
- How many ideas were filed

If the file doesn't exist or `spec_stubs` is 0 and `ideas` is 0, skip this section.

### 5. Check the studio inbox

Run `/check-inbox` to process any pending messages in `studio/inbox/`.

If any urgent or high-priority messages are found, surface them at the top of the startup report before anything else.

### 6. Check the financial pulse

Read `{CONTENT_DIR}/finance/accounts.json`. Surface:
- Current bank balance (`total_eur`)
- Cash after 30-day obligations (`balance_after_30d`)
- Any overdue invoices from `{CONTENT_DIR}/finance/invoices.md`

If `balance_after_30d` is below €1,000, flag as **low cash warning**.

### 7. Startup report

Output a concise startup report:

```
## Studio Startup — {YYYY-MM-DD}

### Sync
{N} projects synced. Errors: {none / list}

### Overdue tasks
{list by project, or "None"}

### Open questions
{list by project, or "None"}

### Harvest gaps (from Abderus)
{summary}

### Obsidian harvest _(if anything new)_
{N} spec stubs: {name}, {name} | {N} ideas filed

### Financial pulse
Balance: €{total_eur} | After 30d obligations: €{balance_after_30d}
{Low cash warning if applicable}
{Overdue invoices if any}

### Today's priorities
{Top 3 most pressing items across all projects — your judgment}
```

Keep it scannable. No padding.
