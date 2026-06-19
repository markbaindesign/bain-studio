---
name: review-checklist
description: Generate a pre-release QA checklist from CHANGELOG.md. Creates an Asana task (or markdown fallback) with one checkbox per changed item. Pass --walk to run an interactive sign-off session. Failed items go to qa/qa-inbox/.
allowed-tools: [Bash, Read, Write]
---

# Review Checklist — Pre-Release QA Checklist

Generates a release-specific checklist from `CHANGELOG.md`. One checkbox per Added, Fixed, or Changed item. Can be created as an Asana task or a local markdown file. With `--walk`, steps through each item interactively for sign-off.

---

## Invoke

```
/review-checklist
/review-checklist 1.2.0
/review-checklist --walk
/review-checklist 1.2.0 --walk
```

---

## Steps

### 1. Read CHANGELOG.md

Find the target version section (or most recent if none specified). Extract all Added, Fixed, and Changed items. Ignore Removed unless the removal needs to be verified on the live site.

If `CHANGELOG.md` does not exist or version is not found, stop and tell Mark to run `/changelog` first.

### 2. Build the checklist

Create one checkbox per item:

```markdown
## Release review — v{version} — {YYYY-MM-DD}

**Target:** staging | production (ask Mark)

### Added
- [ ] {item} — verify: {how to verify}

### Fixed
- [ ] {item} — verify: {how to verify}

### Changed
- [ ] {item} — verify: {how to verify}
```

For each item, write a brief "verify:" note — the one thing to check to confirm it is working. Examples:
- "New booking form" → "verify: submit a test enquiry via the contact page form"
- "Mobile nav not closing" → "verify: open on mobile, tap a menu link, confirm menu closes"
- "Hero image updated" → "verify: homepage hero shows new photography on both desktop and mobile"

### 3. Create the checklist

**Primary path — Asana task:**

Check if the project has an Asana GID in `CLAUDE.md` (`ASANA_PROJECT_GID`).

If yes:
1. Write the checklist to `.claude/asana-mirror/review-checklist-v{version}.md` (temporary mirror file)
2. Instruct Mark to run `python3 studio/sync.py` to push it to Asana as a new task titled "Release review — v{version}"

If Asana GID is not set or Mark prefers local:

**Fallback path — markdown file:**

Write to `docs/review-checklist-v{version}.md`.

### 4. Interactive walk-through (--walk mode)

If `--walk` was passed, step through each checklist item one at a time using `AskUserQuestion`.

For each item present:
- Show the item description
- Show the verify instruction
- Ask: Pass or Fail?

Options:
- **Pass** — item verified, move on
- **Fail** — item failed, will go to QA inbox
- **Skip** — not applicable for this release

After all items, report:
```
Review complete — v{version}
✔ Passed: N
✖ Failed: N
— Skipped: N
```

### 5. Handle failures

For each failed item, assign a QA reference number and create an inbox file.

**Assigning the ref:**

1. Read `qa/qa-counter.json` — get `prefix` and `next`. If the file doesn't exist, read `CLAUDE.md` for `ASANA_TASK_PREFIX` and create the counter file with `next: 1`.
2. Mint the ref: `{prefix}-QA-{next:03d}` (zero-padded to 3 digits minimum)
3. Increment `next` and write `qa-counter.json` back
4. Append a row to `qa/qa-log.md` (create the file with a header row if it doesn't exist):
   `| {ref} | {YYYY-MM-DD} | {short description from item} | open | |`

**Filename convention:**

```
qa/qa-inbox/{ref}-{slug}-review-fail.md
```

Example: `qa/qa-inbox/BSTD-QA-003-mobile-nav-not-closing-review-fail.md`

**File content:**

```markdown
---
ref: {ref}
source: review-checklist
version: {version}
severity: high
---

## {item description}

Verify: {verify instruction}

Failed during pre-release review of v{version} on {date}.
```

Tell Mark: "{N} item(s) sent to qa/qa-inbox/ — refs {ref-list} — run /qa to work through them before releasing."

### 6. Update the checklist file

If created as a markdown file, update it to reflect pass/fail results.

If created as an Asana task, note the pass/fail summary in `.claude/asana-mirror/` and remind Mark to sync.

---

## Notes

- Never mark items as passed automatically — Mark must confirm each one in --walk mode.
- The --walk mode uses the same pass/fail pattern as the QA sign-off UI (AskUserQuestion).
- Failed items go to qa-inbox unchanged — the normal QA workflow picks them up from there.
- Run `/release-report` before this so the client report is ready regardless of checklist outcome.
- Typical release order: `/changelog` → `/release-report` → `/review-checklist --walk` → deploy → `/iris signal` (broadcast).
