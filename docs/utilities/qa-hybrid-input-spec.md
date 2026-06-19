---
tags: [spec, qa, utility]
status: draft
version: 0.1
---

# QA Hybrid Input Spec

## Problem

The current QA workflow (`qa/README.md`) accepts arbitrary files dropped into `qa-inbox/`. In practice this means screenshots — a file dropped in, a visual check performed. This works but has several gaps:

- **No context** — a screenshot shows what is broken but not how to reproduce it, what was expected, or how severe it is
- **Hard to automate** — a screenshot cannot be parsed, diffed, or compared to a baseline without computer vision
- **No structure** — filenames are free-form; there is no way to query by severity, feature area, or type
- **Single medium** — voice memos, HTML state, structured reproduction steps are all excluded by convention

This spec proposes a hybrid input model that adds structure without removing the simplicity of the current drop-file workflow.

---

## Proposed input types

### `image` (existing)
Screenshots, before/after comparisons, annotated captures.

- Extensions: `.png`, `.jpg`, `.gif`, `.webp`
- No change to current behaviour — images continue to work as before
- During sign-off, Claude reads the filename and displays context; Mark views the image in their file manager/IDE

### `html`
Full-page HTML dump saved from the browser ("Save as > Webpage, Complete" or via a script).

- Extension: `.html`
- Purpose: enables structural diffing against a known-good baseline
- Baseline storage: `qa/baselines/{slug}.html` — manually set by Mark after a confirmed-good deploy
- On new dump: Claude diffs against the baseline and surfaces changed sections (structural diff, not full text diff)
- Tooling: `qa/tools/html-diff.py` — **future work**, not yet built. Until available, Claude reads and summarises the HTML directly.

### `description`
Structured written reproduction case. The preferred format for non-visual bugs or anything that requires reproduction steps.

- Extension: `.md`
- Required frontmatter:

```markdown
---
type: description
severity: critical | high | medium | low
feature: (what area of the site — e.g. "contact form", "mobile nav", "checkout")
---

## Steps to reproduce

1.
2.
3.

## Expected

## Actual

## Notes
```

- Claude detects the `type: description` frontmatter and routes accordingly
- If frontmatter is absent, treat as a plain-text description (legacy behaviour)

**Severity guidance:**

| Level | Meaning |
|---|---|
| `critical` | Site is down, data loss, or broken for all users |
| `high` | Key feature broken for most users |
| `medium` | Feature broken for some users, workaround exists |
| `low` | Visual issue, minor UX problem, no functional impact |

### `audio`
Voice memo describing the issue — for cases where it is faster to speak than type.

- Extensions: `.mp3`, `.m4a`, `.wav`, `.ogg`
- **Phase 2 — aspirational.** Requires a transcription step before the item can enter the workflow.
- Proposed pipeline: audio file dropped into `qa-inbox/` → `qa/tools/transcribe.py` (wraps Whisper or the Anthropic audio API) → output written as a `description` `.md` file alongside the audio → both files treated as a bundle
- Until transcription tooling is in place: Claude flags audio files with "Transcription not yet available — please add a written description alongside this file."

### `bundle`
A folder (or zip) containing any combination of the above, treated as a single QA item.

- Format: directory named `{YYYY-MM-DD}-{slug}/` containing any mix of image, html, description, audio files
- Claude reads all files in the directory and synthesises a single QA item from them
- The bundle is moved as a unit through the workflow (inbox → wip → review → passed)
- If a description file is present, it is the canonical record; other files are supporting evidence

---

## File naming convention

All files in `qa-inbox/` should follow:

```
{YYYY-MM-DD}-{slug}-{type}.{ext}
```

Examples:
- `2026-06-19-hero-image-not-loading-image.png`
- `2026-06-19-checkout-redirect-broken-description.md`
- `2026-06-19-mobile-nav-stays-open-html.html`
- `2026-06-19-contact-form-no-email-audio.m4a`
- `2026-06-19-cart-empty-on-reload/` (bundle directory)

The `{type}` suffix in the slug is the file's role, not its extension. It helps Claude route the file without parsing content.

**Legacy filenames** (no convention) continue to work — Claude treats them as untyped and falls back to visual/text inspection.

---

## HTML diff workflow

1. Mark confirms a good deploy → runs `cp {downloaded}.html qa/baselines/{slug}.html`
2. On a future deploy, Mark saves a new HTML dump to `qa-inbox/`
3. Claude runs `qa/tools/html-diff.py {new}.html qa/baselines/{slug}.html` and surfaces:
   - Added elements (new DOM nodes)
   - Removed elements
   - Changed text content
   - Changed attributes (class, href, src)
4. Claude presents the diff summary during sign-off rather than the raw HTML

`qa/tools/html-diff.py` — **not yet built.** Proposed implementation: use Python's `difflib` or `html.parser` to produce a structural diff. Mark as a BSTD task.

---

## Audio workflow (phase 2)

1. Voice memo dropped into `qa-inbox/`
2. `qa/tools/transcribe.py` watches the inbox (or is run manually) and transcribes audio files using Whisper (local) or a transcription API
3. Transcription is written to `{same-slug}-description.md` with `type: description` frontmatter and the transcript as the "Actual" field
4. The audio file and description file are treated as a bundle
5. Claude prompts Mark to review and edit the transcription before the item enters the workflow

Whisper (local, free) is the preferred tool. The Anthropic API does not currently support audio transcription directly.

---

## Sign-off changes for hybrid input

During the review step (moving from `qa-wip/` to `qa-review/`), Claude should:

| Input type | Sign-off presentation |
|---|---|
| `image` | Filename + description of what to look for |
| `html` | Diff summary (or "HTML diff tooling not yet available") |
| `description` | Severity, feature area, steps to reproduce, expected vs actual |
| `audio` | Transcription (if available) + link to audio file |
| `bundle` | Description file as canonical record, other files listed as evidence |

---

## Changes needed to `qa/README.md`

1. Add file naming convention section
2. Add input types table with accepted formats
3. Update "How issues enter the workflow" to describe detection by type
4. Add note on baselines directory
5. Add note on audio (phase 2, aspirational)

## Changes needed to the QA skill (when built)

1. On picking up an item from inbox, detect type from filename suffix or frontmatter
2. For `description` type: parse frontmatter, display severity and feature area prominently
3. For `html` type: attempt diff against baseline; fall back to summary if no baseline or no tooling
4. For `audio` type: check for paired description file; warn if absent
5. For `bundle` type: read directory, identify description file as primary, list supporting files
6. During sign-off: present type-appropriate summary alongside pass/fail options

---

## Out of scope

- Video input or screen recording
- Real-time issue capture (browser extension, etc.)
- Automated issue detection (visual regression testing — separate tooling)
- Multi-user QA workflows
