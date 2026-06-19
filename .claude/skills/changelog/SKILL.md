---
name: changelog
description: Update the project CHANGELOG.md at release time. Reads git log since last tag and QA review-passed items, proposes a semver version bump, and writes a Keep a Changelog formatted entry. Invoke before /release-report and /review-checklist.
allowed-tools: [Bash, Read, Write]
---

# Changelog — Release Changelog Maintainer

Updates `CHANGELOG.md` at the project root using the [Keep a Changelog](https://keepachangelog.com) format. Run at release time before generating the client report or review checklist.

---

## Steps

### 1. Read existing changelog

Check if `CHANGELOG.md` exists at the project root:

```bash
ls CHANGELOG.md 2>/dev/null || echo "NOT FOUND"
```

If missing, create it with this header:

```markdown
# Changelog

All notable changes to this project are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
Versioning: [Semantic Versioning](https://semver.org/spec/v2.0.0.html)
```

### 2. Find the last release

```bash
git tag --sort=-version:refname | head -5
git log $(git describe --tags --abbrev=0 2>/dev/null || echo "")..HEAD --oneline 2>/dev/null || git log --oneline -20
```

If no tags exist, use all commits.

### 3. Read QA review-passed items

```bash
ls qa/qa-review-passed/ 2>/dev/null
```

Read each file for context on what was fixed or verified.

### 4. Read any release notes

Check for release notes in:
- `.claude/release-notes.md`
- `docs/release-notes.md`

Use if present — these take priority over raw git log.

### 5. Categorise changes

Group commits and QA items into Keep a Changelog categories:

| Category | What goes here |
|---|---|
| `Added` | New features, new pages, new functionality |
| `Fixed` | Bug fixes, broken functionality repaired |
| `Changed` | Updates to existing features, design tweaks, content changes |
| `Removed` | Deleted features, pages, or functionality |

Use judgment — merge commit noise, dependency bumps, and internal tooling changes are not client-relevant. Focus on what changed from the client's perspective.

### 6. Propose version bump

Apply semver logic:

| Condition | Bump |
|---|---|
| Only `Fixed` entries | Patch: `x.y.Z+1` |
| Any `Added` or `Changed` entries | Minor: `x.Y+1.0` |
| Breaking change or major redesign | Major: `X+1.0.0` |

If no previous tag exists, propose `1.0.0` for a first release, or `0.1.0` for a pre-launch release.

Present the proposed version and category list to Mark for confirmation before writing.

### 7. Write the changelog entry

After confirmation, prepend the new entry to `CHANGELOG.md`:

```markdown
## [X.Y.Z] - YYYY-MM-DD

### Added
- {item}

### Fixed
- {item}

### Changed
- {item}

### Removed
- {item}
```

Omit any empty categories. Items should be one line each, written in plain English from the client's perspective.

### 8. Offer to tag

Ask: "Tag this release as vX.Y.Z in git?"

If yes:
```bash
git add CHANGELOG.md
git commit -m "chore: update changelog for vX.Y.Z"
git tag -a vX.Y.Z -m "Release vX.Y.Z"
```

---

## Notes

- Never auto-write the changelog without Mark confirming the version number.
- Write from the client's perspective — "Fixed broken contact form" not "Fixed POST handler null reference on /wp-json/contact/v1/submit".
- If a QA review-passed item contradicts the git log, trust the QA item.
- Run `/release-report` after this to generate the client-facing version.
