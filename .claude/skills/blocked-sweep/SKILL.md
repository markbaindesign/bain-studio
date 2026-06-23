---
name: blocked-sweep
description: Scan all project mirrors for blocked or stalled tasks. For each blocker, reads the latest comments to check if already resolved, then optionally posts a clarification request to Asana via bainbot. Designed to run at the start of a session or on Hermes schedule.
allowed-tools: [Read, Bash]
---

# Blocked Sweep

Scan all active project mirrors for blocked or stalled tasks. Read comments to see if the blocker was already answered. Post clarification requests via bainbot where needed.

## Steps

### 1. Discover all project mirrors

Read `/media/data/dev/bain-studio/studio/projects.json` to get the list of active project paths.

For each path, check if `{path}/.claude/asana-mirror.md` exists.

### 2. Parse each mirror for blocked tasks

A task is blocked if ANY of the following:
- `Section: STALLED`
- `Blockers:` field is non-empty and not `None identified`
- Task has been `In Progress` or `DOING` with no `Progress:` update in 7+ days (stale)

For each blocked task extract:
- Local ID (e.g. `NORE-014`)
- Asana GID
- Task name
- Section
- Blockers field content
- Latest comment (if any) — the last entry under `Comments:`
- Progress note

### 3. Check if already unblocked via comments

For each blocked task, read the comment thread in the mirror. If the most recent comment (from Mark or anyone) addresses the blocker and suggests it's resolved, mark as `likely resolved` — do not post a new comment.

If the most recent comment is already a bainbot clarification request (starts with `[Blocked Sweep]`), check whether it has been replied to. If not replied to yet, skip — don't double-post.

### 4. Output the sweep report

```
## Blocked Sweep — {YYYY-MM-DD HH:MM}

### {PROJECT_NAME}

**{LOCAL_ID} — {task name}**
Section: {section}
Blocker: {blocker text}
Last comment: {last comment or "none"}
Status: [NEEDS CLARIFICATION | LIKELY RESOLVED | AWAITING REPLY]

...

### Summary
- {N} blocked tasks across {M} projects
- {N} need clarification → will post comments
- {N} awaiting reply (bainbot already asked)
- {N} likely resolved (check and unblock manually)
```

### 5. Ask before posting (interactive mode)

After showing the report, ask:

> Post clarification comments to Asana for the {N} tasks that need it? (yes / no / select)

If yes, proceed to step 6 for all `NEEDS CLARIFICATION` tasks.
If select, list them numbered and ask which to post.
If no, stop here.

### 6. Post clarification comments

For each task approved for comment, post via bainbot:

```bash
python3 /media/data/dev/bain-studio/studio/sync.py \
  --comment \
  --task-gid {TASK_GID} \
  --comment-text "[Blocked Sweep] {context-aware question}"
```

The comment text should be specific to the blocker. Do NOT use a generic template. Examples:

- Blocker: "waiting for client copy" → "Hi — just checking in on the copy for this section. Any update on timing? Happy to draft a placeholder if that helps move things forward."
- Blocker: "needs design decision" → "Quick question on this: {specific decision needed}. What's your preference?"
- Section: STALLED, no blocker text → "This has been stalled for a while — is there anything blocking progress, or can this move back to NEXT UP?"

Sign the comment naturally. Do not expose internal tooling language.

### 7. Report what was posted

List each comment posted with the task ID, a short excerpt of the comment, and a link to the task.

---

## Usage

```
/blocked-sweep
```

Run from any directory — it reads all registered projects from the studio registry.

## Notes

- All comments are posted as bainbot, not Mark. The tone should still be natural and client-appropriate where tasks are client-facing, or direct/internal where tasks are internal studio work.
- The skill reads comments from the local mirror. The mirror must be up to date — run a sync first if you want fresh comment data.
- To post a one-off comment manually: `python3 /media/data/dev/bain-studio/studio/sync.py --comment --task-gid {GID} --comment-text "..."`
