---
tags: [skill, asana, workflow, blockers, hermes]
god: hermes
invoke: /blocked-sweep
description: Scan all project mirrors for blocked or stalled tasks. Reads comment threads to check if already resolved. Posts context-aware clarification requests to Asana via bainbot where needed.
---

# Blocked Sweep

Scans all active project mirrors for blocked or stalled tasks, reads comment threads, and posts clarification requests via bainbot.

## When to use

- Start of session: run after `/studio-startup` to action any blockers before diving into work
- On Hermes schedule: weekly sweep to catch stalled tasks before they rot
- Ad-hoc: when you want to unblock a batch of tasks without going into each one manually

## What counts as blocked

- `Section: STALLED`
- `Blockers:` field is non-empty and not "None identified"
- Task in `DOING` or `In Progress` with no Progress update in 7+ days

## What it does

1. Reads all project mirrors from `studio/projects.json`
2. Identifies blocked/stalled tasks
3. Reads comment thread — checks if already answered or if bainbot already asked
4. Presents a report with status per task: `NEEDS CLARIFICATION`, `AWAITING REPLY`, or `LIKELY RESOLVED`
5. Asks before posting — interactive confirmation per task or batch
6. Posts context-aware comments via bainbot (`sync.py --comment`)

## Posting comments manually

```bash
python3 /media/data/dev/bain-studio/studio/sync.py \
  --comment \
  --task-gid 1234567890 \
  --comment-text "Quick question on this — any update on timing?"
```

`--dry-run` previews without posting.

## Loop behaviour

On the next sync after posting, the reply (if any) will appear in the mirror under `Comments:`. The next `/blocked-sweep` run will detect it and either:
- Mark the task as `LIKELY RESOLVED` (if reply addresses the blocker)
- Move on (if still awaiting)

## Notes

- Comments are posted as bainbot. Tone is natural — not robotic or templated.
- Does not double-post: skips tasks where bainbot already asked and no reply has come in.
- Mirror must be up to date for accurate comment data. Run a sync first if needed.
