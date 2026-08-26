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

If missing, create it with this header, worded exactly as the spec words it:

```markdown
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
```

Do not paraphrase those two sentences. The spec's own wording is the standard
across every studio repo.

An `[Unreleased]` section sits above the most recent release and collects changes
before they are cut into one.

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
| `Changed` | Updates to existing features, design tweaks, content changes |
| `Deprecated` | Features still present but marked for removal |
| `Removed` | Deleted features, pages, or functionality |
| `Fixed` | Bug fixes, broken functionality repaired |
| `Security` | Vulnerability fixes |

These six are the full Keep a Changelog set. Use only the ones that apply, but do
not invent categories outside this list.

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

### Changed
- {item}

### Fixed
- {item}

### Removed
- {item}
```

The date is ISO 8601 (`YYYY-MM-DD`). The latest version comes first, directly
below `## [Unreleased]`.

Omit any empty categories. Items should be one line each, written in plain English from the client's perspective.

### 8. Update the link definitions

Every `## [X.Y.Z]` heading uses bracket notation, so each needs a matching link
definition at the end of the file. The spec requires versions and sections to be
linkable.

Check the remote host first, the URL shapes differ:

```bash
git remote get-url origin
```

GitHub:
```markdown
[Unreleased]: https://github.com/{owner}/{repo}/compare/X.Y.Z...develop
[X.Y.Z]: https://github.com/{owner}/{repo}/compare/{previous}...X.Y.Z
[1.0.0]: https://github.com/{owner}/{repo}/releases/tag/1.0.0
```

Bitbucket:
```markdown
[Unreleased]: https://bitbucket.org/{owner}/{repo}/branches/compare/develop%0DX.Y.Z
[X.Y.Z]: https://bitbucket.org/{owner}/{repo}/branches/compare/X.Y.Z%0D{previous}
[1.0.0]: https://bitbucket.org/{owner}/{repo}/src/1.0.0/
```

The earliest release has no predecessor to compare against, so link it to the tag
itself rather than a comparison.

### 9. Update VERSION and offer to tag

If the project has a `VERSION` file at its root, update it to the new version
(bare version string, no `v` prefix, trailing newline). This is the version-bump
commit the studio git flow expects.

Ask: "Tag this release as X.Y.Z in git?"

If yes:
```bash
printf '%s\n' "X.Y.Z" > VERSION   # only if the file exists
git add CHANGELOG.md VERSION
git commit -m "chore: release X.Y.Z"
git tag -a X.Y.Z -m "X.Y.Z"
```

Tags carry no `v` prefix. See the versioning section of `/media/data/dev/CLAUDE.md`.

---

## Notes

- Never auto-write the changelog without Mark confirming the version number.
- Tags are `X.Y.Z`, never `vX.Y.Z`. The studio convention has no `v` prefix.
- Header wording is spec-exact, not paraphrased. See step 1.
- Full git flow cuts a `release/x.y.z` branch holding the version-bump commit,
  merges it to `main` and back to `develop`, then tags on `main`. This skill
  handles the changelog and version bump; the branch and merge are done around it.
- Write from the client's perspective — "Fixed broken contact form" not "Fixed POST handler null reference on /wp-json/contact/v1/submit".
- If a QA review-passed item contradicts the git log, trust the QA item.
- Run `/release-report` after this to generate the client-facing version.
