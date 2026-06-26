---
tags: [skill, utility, qa]
command: /issue
description: QA issue intake — assigns a reference number, creates a structured file in qa/qa-inbox/, and logs it. Lightweight alternative to /qa for registering a single issue quickly.
---

# issue — QA Issue Reporter

Intake skill for the QA workflow. Registers a single issue without running the full `/qa` cycle.

## Invoke

```
/issue
/issue broken contact form on mobile
```

Inline description is optional — if omitted, the skill asks.

## What it does

1. Asks for severity, feature area, and reproduction details
2. Assigns the next `{PREFIX}-QA-{NNN}` reference for the project
3. Writes a structured `.md` file to `qa/qa-inbox/`
4. Appends a row to `qa/qa-log.md`
5. Confirms the ref and filename

## Output

`qa/qa-inbox/{ref}-{slug}.md` — structured issue file with frontmatter (ref, severity, feature, type) and reproduction fields.

## Prerequisites

`qa/` must exist in the project root. Run `/qa` first if it hasn't been set up.

## See also

- [qa workflow](../../qa/README.md) — full workflow; run `/qa` to work through registered issues
- [review-checklist](review-checklist.md) — pre-release checklist; failures are registered via the same ref scheme
- [qa-hybrid-input-spec](qa-hybrid-input-spec.md) — spec for image, HTML, audio, and bundle input types
