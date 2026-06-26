# QA Workflow — Bain Studio

## Folder structure

| Folder | Purpose |
|---|---|
| `qa-inbox/` | New issues waiting to be picked up |
| `qa-wip/` | Issues actively being worked on |
| `qa-review/` | Fixed issues awaiting sign-off |
| `qa-review-passed/` | Sign-off confirmed — permanent record |
| `qa-counter.json` | Sequential reference counter for this project |
| `qa-log.md` | Append-only log of all QA items and their final status |

## Reference numbers

Every QA item has a reference number assigned at intake (when it enters `qa-inbox/`).

**Format:** `{PROJECT-PREFIX}-QA-{NNN}` — e.g. `BSTD-QA-001`, `NORE-QA-042`

The counter is project-specific and sequential. It lives in `qa/qa-counter.json`:

```json
{"prefix": "BSTD", "next": 2}
```

- `prefix` — the project task prefix (matches `ASANA_TASK_PREFIX` in CLAUDE.md)
- `next` — the next number to assign (starts at 1; increment after each assignment)

**Filename convention:** the ref is embedded in the filename at intake:

```
qa-inbox/BSTD-QA-001-dashboard-fails-to-load.md
```

If an item arrives without a ref (e.g. a plain screenshot or file dropped manually), the QA skill assigns one at the point of pickup.

**Never reuse or skip a number.** If an item is abandoned or marked wontfix, the number is retired in the log and the counter still advances.

## QA log

A running event log is maintained at `qa/qa-log.md`. It is append-only — one line per event, written at every lifecycle transition.

**Format:**

```
[2026-06-19 10:45] BSTD-QA-001 registered — dashboard fails to load gnucash data (high / studio-dashboard)
[2026-06-19 11:02] BSTD-QA-001 → wip
[2026-06-19 11:45] BSTD-QA-001 → review — gnucash path resolution fixed, verified clean output
[2026-06-19 11:47] BSTD-QA-001 passed
[2026-06-19 14:10] BSTD-QA-002 registered — sync script drops tasks on retry (medium / sync)
[2026-06-19 14:55] BSTD-QA-002 → wip
[2026-06-19 15:30] BSTD-QA-002 → review (failed) — still dropping on second retry
[2026-06-19 15:31] BSTD-QA-002 → inbox (re-opened)
```

**Event types:**

| Event | When to write |
|---|---|
| `registered` | Item first assigned a ref — include description, severity, feature area |
| `→ wip` | Item moved from inbox to wip |
| `→ review` | Item moved from wip to review — include a brief note on what was fixed |
| `passed` | Item signed off by Mark |
| `→ inbox (re-opened)` | Item failed sign-off and returned to inbox |
| `wontfix` | Item closed without fixing — include reason |

**Log rules:**

- Append only — never edit or delete lines
- Timestamp format: `[YYYY-MM-DD HH:MM]` (local time, 24h, minute precision is enough)
- `registered` line is the only one that includes the description and severity — subsequent events just reference the ref
- Current status of any item is determined by its most recent event line
- To find all events for a ref: `grep BSTD-QA-001 qa/qa-log.md`

## How issues enter the workflow

Mark drops a file into `qa-inbox/`. The filename should describe the issue (e.g. `dashboard fails to load gnucash data.txt` or `sync script drops tasks on retry.md`). Screenshots work too.

If the filename already includes a ref (`BSTD-QA-001-...`), the item is already registered. If not, the QA skill assigns a ref at pickup, renames the file, and appends to the log.

## Lifecycle

```
qa-inbox → qa-wip → qa-review → qa-review-passed
               ↑          ↓ (fail)
               └──────────┘
```

1. **Picked up** — Claude moves the file from `qa-inbox/` to `qa-wip/` when starting work on it. If the file has no ref, assign one now: read `qa-counter.json`, mint the ref, rename the file to include it, increment `next`, write the counter back, append to `qa-log.md`.
2. **Fixed** — Claude moves the file from `qa-wip/` to `qa-review/` once the fix is verified.
3. **Sign-off** — Claude presents each `qa-review/` item to Mark using the pass/fail UI (one item at a time). Mark always signs off — Claude never auto-passes.
4. **Passed** — Claude moves the file to `qa-review-passed/`. Update `qa-log.md`: status `passed`, closed = today.
5. **Failed** — Claude moves the file back to `qa-inbox/` with the filename unchanged, then investigates further. Log stays `open`.

## Before presenting for sign-off

Claude must be confident the fix is live before moving an item to `qa-review/`. For BSTD, "confident" means:

- **Python script bug** — run the script and confirm clean output
- **Dashboard bug** — start `python3 studio/dashboard/server.py` and verify the behaviour in the browser
- **Skill/agent issue** — invoke the skill and confirm it behaves correctly

Do not move to `qa-review/` on the assumption a change worked — confirm it.

## Sign-off UI

Use `AskUserQuestion` with pass/fail options, one item per question. Include the ref number and a one-line summary of what was fixed and how it was verified.

Example: "BSTD-QA-001 — Dashboard gnucash load fixed. Verified: server started, data loaded cleanly with no errors."

## Rules for Claude

- Never auto-pass an item — always present for sign-off.
- Assign a ref number to any inbox item that doesn't already have one, before or at the point of pickup.
- Keep the ref in the filename when moving files between folders.
- Move to `qa-wip/` before starting work, not after.
- A failed item goes back to `qa-inbox/` with the same filename so history is preserved.
- There is no `failed/` folder — rejected items re-enter the flow immediately.
- Always update `qa-log.md` at intake (if assigning a ref) and at final resolution (passed/wontfix).
