---
name: studio-shutdown
description: End-of-session studio shutdown routine. Commits any mirror edits, runs a retro to capture learnings, flags anything unfinished, and leaves the studio in a clean state. Run at the end of any work session.
allowed-tools: [Read, Write, Edit, Bash]
---

# Studio Shutdown

Run this at the end of every work session. It closes loops, captures learnings, and makes sure nothing is left dangling.

## Steps

### 1. Check for unsaved mirror edits

For each active project, check if `.claude/asana-mirror.md` has uncommitted changes:

```bash
cd /path/to/project && git diff .claude/asana-mirror.md
```

If there are changes, push them to Asana:
```bash
cd /media/data/dev/bain-studio && python3 studio/sync.py --project {PREFIX}
```

Confirm each project's mirror is synced before proceeding.

### 2. Check for open feature branches

```bash
git -C /media/data/dev/bain-studio branch | grep -v master | grep -v main
```

For each open branch, note: what task it relates to, and whether it has a PR. If a branch has completed work but no PR, flag it.

### 3. Run the session retro

```
/studio-retro
```

Capture learnings from the session: what worked, what didn't, any patterns worth recording. Route to CLAUDE.md, skills, ADRs, or memory as appropriate.

### 4. Flag anything unfinished

List any tasks started but not completed this session:
- Branches with partial work
- Tasks marked in-progress but not done
- Any blockers raised today that need Mark's attention

### 5. Shutdown report

Output a brief shutdown summary:

```
## Studio Shutdown — {YYYY-MM-DD} {HH:MM}

### Synced
{list of projects synced, or "None needed"}

### Open branches
{list with PR status, or "None"}

### Unfinished
{list with blockers, or "Clean"}

### Captured
{what the retro produced — skills updated, memories written, ADRs logged}
```

Notify via Hermes if anything critical is unfinished:
```bash
python3 /media/data/dev/bain-studio/studio/notifier.py \
  "Session ended. Unfinished: {summary}" --priority normal --sender hermes
```
