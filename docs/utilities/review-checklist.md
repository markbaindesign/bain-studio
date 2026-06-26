---
tags: [skill, utility, release, qa]
command: /review-checklist
description: Generate a pre-release QA checklist from CHANGELOG.md. Creates an Asana task or markdown file with one checkbox per changed item. Pass --walk for interactive sign-off.
---

# review-checklist — Pre-Release QA Checklist

Generates a release-specific checklist from `CHANGELOG.md`. One checkbox per Added, Fixed, or Changed item.

## Invoke

```
/review-checklist
/review-checklist 1.2.0
/review-checklist --walk
```

## What it does

1. Reads the target version from `CHANGELOG.md`
2. Builds a checklist with one item per change plus a "verify:" instruction
3. Creates an Asana task (`Release review — v{version}`) if the project has `ASANA_PROJECT_GID`
4. Falls back to `docs/review-checklist-v{version}.md` if no Asana project

## Interactive mode (`--walk`)

Steps through each checklist item one by one with pass/fail prompts. At the end:

- Passed items are marked done
- Failed items are written to `qa/qa-inbox/` for the QA workflow to pick up

## Release order

`/changelog` → `/release-report` → **`/review-checklist --walk`** → deploy

## See also

- [changelog](changelog.md) — must run first
- [qa-hybrid-input-spec](qa-hybrid-input-spec.md) — QA input format spec
