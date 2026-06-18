# QA Workflow — Bain Studio

## Folder structure

| Folder | Purpose |
|---|---|
| `qa-inbox/` | New issues waiting to be picked up |
| `qa-wip/` | Issues actively being worked on |
| `qa-review/` | Fixed issues awaiting sign-off |
| `qa-review-passed/` | Sign-off confirmed — permanent record |

## How issues enter the workflow

Mark drops a file into `qa-inbox/`. The filename must describe the issue (e.g. `dashboard fails to load gnucash data.txt` or `sync script drops tasks on retry.md`). No other naming convention is enforced. Screenshots work too.

## Lifecycle

```
qa-inbox → qa-wip → qa-review → qa-review-passed
               ↑          ↓ (fail)
               └──────────┘
```

1. **Picked up** — Claude moves the file from `qa-inbox/` to `qa-wip/` when starting work on it.
2. **Fixed** — Claude moves the file from `qa-wip/` to `qa-review/` once the fix is verified.
3. **Sign-off** — Claude presents each `qa-review/` item to Mark using the pass/fail UI (one item at a time). Mark always signs off — Claude never auto-passes.
4. **Passed** — Claude moves the file to `qa-review-passed/`.
5. **Failed** — Claude moves the file back to `qa-inbox/` with the original filename unchanged, then investigates further.

## Before presenting for sign-off

Claude must be confident the fix is live before moving an item to `qa-review/`. For BSTD, "confident" means:

- **Python script bug** — run the script and confirm clean output
- **Dashboard bug** — start `python3 studio/dashboard/server.py` and verify the behaviour in the browser
- **Skill/agent issue** — invoke the skill and confirm it behaves correctly

Do not move to `qa-review/` on the assumption a change worked — confirm it.

## Sign-off UI

Use `AskUserQuestion` with pass/fail options, one item per question. Include a one-line summary of what was fixed and how it was verified.

## Rules for Claude

- Never auto-pass an item — always present for sign-off.
- Keep the original filename when moving files between folders.
- Move to `qa-wip/` before starting work, not after.
- A failed item goes back to `qa-inbox/` with the same filename so history is preserved.
- There is no `failed/` folder — rejected items re-enter the flow immediately.
