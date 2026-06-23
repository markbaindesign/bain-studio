---
tags: [utility, qa, workflow, skill]
god: hephaestus
invoke: /qa
description: QA workflow for studio projects. Two entry points — interactive session with full pipeline (/qa) and quick screenshot capture without breaking focus (/qa-capture).
---

# QA

Two entry points depending on context.

## `/qa` — interactive session

Full pipeline: inbox → wip → review → sign-off. Use when actively QAing a site or feature.

1. Scaffolds `qa/` if it doesn't exist
2. Assigns ref numbers to any unregistered inbox items
3. Picks up each item, investigates, fixes, verifies
4. Presents each fix for sign-off (pass/fail)
5. Passed items move to `qa-review-passed/` and are logged

Sign-off is always required — Claude never auto-passes.

## `/qa-capture` — quick log without breaking focus

Drop a screenshot into `qa/qa-inbox/`, run `/qa-capture`. Done in under 30 seconds.

1. Finds unregistered images in `qa/qa-inbox/` automatically
2. Reads each screenshot and proposes a title + severity + feature area
3. Greps the project mirror for possible duplicates (2+ keyword matches = warning)
4. One confirmation question — create / edit title / skip
5. Creates an Asana task with severity, description, and screenshot path in notes

Screenshots stay in `qa/qa-inbox/`. The Asana task notes reference the path.

## Folder structure

```
qa/
  qa-inbox/          — drop files here (screenshots, notes, etc.)
  qa-wip/            — items being actively worked
  qa-review/         — fixed, awaiting sign-off
  qa-review-passed/  — signed off, permanent record
  qa-counter.json    — sequential ref counter
  qa-log.md          — append-only event log
  README.md          — full workflow rules
```

## Reference numbers

Format: `{PREFIX}-QA-{NNN}` — e.g. `BSTD-QA-001`, `NORE-QA-042`

Sequential, project-scoped, never reused. Assigned at intake (when `/qa` picks up an unregistered item). Already-registered images (filename starts with the ref) are skipped by `/qa-capture`.

## QA log

Append-only event log at `qa/qa-log.md`. One line per lifecycle event:

```
[2026-06-23 14:10] BSTD-QA-001 registered — dashboard totals show zero (high / dashboard)
[2026-06-23 14:55] BSTD-QA-001 → wip
[2026-06-23 15:30] BSTD-QA-001 → review — gnucash path fixed, verified clean output
[2026-06-23 15:31] BSTD-QA-001 passed
```

## When to use which

| Situation | Use |
|---|---|
| Actively testing a feature end-to-end | `/qa` |
| Spotted an issue mid-session, don't want to lose focus | `/qa-capture` |
| Reviewing a batch of screenshots dropped overnight | `/qa-capture` then `/qa` |
| Signing off a fix someone else made | `/qa` |

## Related

- `qa/README.md` — full workflow rules, lifecycle diagram, sign-off UI spec
- `docs/utilities/qa-hybrid-input-spec.md` — spec for structured input format (draft)
