---
name: release-report
description: Generate a client-facing release report from CHANGELOG.md. Plain English, no technical jargon. Outputs a dated markdown file and optionally creates a Gmail draft. Run after /changelog at release time.
allowed-tools: [Bash, Read, Write]
---

# Release Report — Client Release Communication

Reads a version entry from `CHANGELOG.md` and produces a plain-English release report for the client. Not a technical document — written as a friendly update in studio voice.

---

## Invoke

```
/release-report
/release-report 1.2.0
```

If no version is provided, reads the most recent entry from `CHANGELOG.md`.

---

## Steps

### 1. Read CHANGELOG.md

```bash
cat CHANGELOG.md
```

Find the requested version section (or the first/most recent `## [X.Y.Z]` block if none specified). Extract entries by category: Added, Fixed, Changed, Removed.

If `CHANGELOG.md` does not exist or the version is not found, stop and tell Mark to run `/changelog` first.

### 2. Read brand voice

Read `$STUDIO_CONTENT_DIR/internal/brand.md` for voice guidance.

Apply the **"Client messages (existing relationships)"** register:
- Direct, no filler openers
- Plain English, no technical terms
- Short sentences
- Sign off with "Cheers"

### 3. Read project context

Read `CLAUDE.md` for:
- Client name
- Project name
- Any notes on communication preferences

### 4. Write the report

Map changelog categories to client-friendly headings:

| Changelog | Report heading |
|---|---|
| Added | What's new |
| Fixed | Issues resolved |
| Changed | Updates |
| Removed | Removed |

Omit any empty categories. Omit the "Removed" section unless there is something the client needs to know about.

Write each item in plain English describing what the client will notice — not what code changed. Examples:

- "Added" / "New booking form on the contact page" → "You can now receive booking enquiries directly through the contact page."
- "Fixed" / "Mobile nav menu not closing after selection" → "The mobile navigation menu now closes correctly after selecting a page."
- "Changed" / "Updated hero image on homepage" → "The homepage hero image has been updated to the new photography."

**Format:**

```markdown
# Release update — {Project name} — v{version}

Hi {Client first name},

Here's a summary of what changed in this update.

## What's new
- {item}

## Issues resolved
- {item}

## Updates
- {item}

Cheers,
Mark
```

If there is only one category, skip the headings and use a single bulleted list after the intro line.

### 5. Save the report

```
docs/release-report-{version}-{YYYY-MM-DD}.md
```

Create `docs/` if it does not exist.

### 6. Offer to send as email

Ask: "Want me to create a Gmail draft to send this to the client?"

If yes, use the Gmail MCP tool (`mcp__claude_ai_Gmail__create_draft`) with:
- `to`: client email address (ask if not in CLAUDE.md)
- `subject`: "Update: {Project name} — v{version}"
- `body`: the report content as plain text

---

## Notes

- Never invent client contact details — ask if not in CLAUDE.md.
- Do not include version numbers in the email subject unless the client is technical. Use "latest update" if unsure.
- This is the external-facing document. Do not include git hashes, file paths, or internal task IDs.
- If the changelog entry has no client-visible changes (only internal tooling, deps, etc.), say so and offer to skip sending.
