---
name: qa
description: "Run the QA workflow for the current project: report status, pick up inbox items, work through fixes, present review items for sign-off."
---

# QA Workflow Skill

Run the full QA workflow for the current project. The workflow rules live in `qa/README.md` — read it first.

## Step 0 — Scaffold if needed

Check whether `qa/` exists in the current project root. If it doesn't:

1. Create the folder structure:
   ```
   qa/
     qa-inbox/
     qa-wip/
     qa-review/
     qa-review-passed/
   ```
2. Copy the canonical README from `~/.claude/skills/qa/README.md` into `qa/README.md`
3. Create `qa/qa-counter.json` — read the project prefix from `CLAUDE.md` (`ASANA_TASK_PREFIX`). If not found, ask Mark. Write:
   ```json
   {"prefix": "PREFIX", "next": 1}
   ```
4. Create `qa/qa-log.md` with the standard header:
   ```
   # QA Log — {PREFIX}

   Append-only event log. One line per lifecycle event.
   Format: [YYYY-MM-DD HH:MM] {ref} {event} — {details}

   To check status of an item: grep {ref} qa/qa-log.md
   To list open items: grep "registered" qa/qa-log.md | grep -v "passed\|wontfix"
   ```
5. Tell the user the structure has been created and drop files into `qa-inbox/` to get started
6. Stop — nothing to process yet

## Step 1 — Orient

Read `qa/README.md` in the current project root. This is the source of truth for folder names, lifecycle rules, sign-off behaviour, and the reference number scheme.

Then list the contents of each QA folder and report a status summary to the user:

```
qa-inbox:         N items
qa-wip:           N items
qa-review:        N items
qa-review-passed: N items
```

If all folders are empty, report that and stop.

## Step 2 — Assign refs to inbox items without one

Before picking up any work, scan `qa-inbox/` for files whose names do not already start with a project ref (`{PREFIX}-QA-{NNN}`).

For each such file:
1. Read `qa/qa-counter.json` to get the current `prefix` and `next`
2. Mint the ref: `{prefix}-QA-{next:03d}` (zero-padded to 3 digits minimum)
3. Rename the file: prepend the ref and a hyphen, slugifying if needed
   - `dashboard fails to load.md` → `BSTD-QA-001-dashboard-fails-to-load.md`
4. Increment `next` and write `qa-counter.json` back
5. Append a line to `qa/qa-log.md`:
   `[YYYY-MM-DD HH:MM] {ref} registered — {description} (untyped / unknown)`
   - Description: derive from the original filename (strip extension, de-slug, trim)

Process all unregistered inbox items before moving any to wip.

## Step 3 — Pick up inbox items

For each item in `qa-inbox/`:
- Move it to `qa-wip/` (keeping the full filename including ref)
- Read the filename — it describes the issue
- If the issue is visual (screenshot), read the image
- Investigate the issue (check local, production, or both as appropriate)
- Fix it
- Verify the fix is live before proceeding (see README for what "confident" means per issue type)
- Move the item from `qa-wip/` to `qa-review/`

Work through inbox items one at a time, fully resolving each before moving to the next.

## Step 4 — Present review items

For each item in `qa-review/`, present it to the user using `AskUserQuestion` with Pass / Fail options (one item per question). Include:
- The ref number (e.g. `BSTD-QA-001`)
- A one-line description of what was fixed
- How the fix was verified

**Pass** → move to `qa-review-passed/`. Append to `qa-log.md`: `[YYYY-MM-DD HH:MM] {ref} passed`
**Fail** → move back to `qa-inbox/` with the original filename unchanged. Append to `qa-log.md`: `[YYYY-MM-DD HH:MM] {ref} → inbox (re-opened)`. Return to Step 3.

## Rules

- Never auto-pass — always present for sign-off
- Assign a ref to any inbox item that lacks one before picking it up
- Keep the full filename (including ref) when moving between folders
- Move to `qa-wip/` before starting work, not after
- Do not present for review until the fix is verified
- Update `qa-log.md` at intake (ref assignment) and at final resolution (passed/wontfix)
