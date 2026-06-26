---
tags: [skill, utility, release]
command: /changelog
description: Update the project CHANGELOG.md at release time. Reads git log and QA review-passed items, proposes a semver version bump, writes a Keep a Changelog entry.
---

# changelog — Release Changelog Maintainer

Maintains `CHANGELOG.md` at the project root in [Keep a Changelog](https://keepachangelog.com) format.

## Invoke

```
/changelog
```

Run at release time, before `/release-report` and `/review-checklist`.

## What it does

1. Reads git log since the last tag and `qa/qa-review-passed/` items
2. Categorises changes: Added / Fixed / Changed / Removed
3. Proposes a semver version bump (patch / minor / major)
4. Asks Mark to confirm the version before writing
5. Prepends the new entry to `CHANGELOG.md`
6. Offers to tag the git commit

## Version strategy

| Changes | Bump |
|---|---|
| Bug fixes only | Patch (x.y.Z) |
| New features or changes | Minor (x.Y.0) |
| Breaking change or major redesign | Major (X.0.0) |

## See also

- [release-report](release-report.md) — run after this to generate the client-facing version
- [review-checklist](review-checklist.md) — run after this to generate the QA checklist
