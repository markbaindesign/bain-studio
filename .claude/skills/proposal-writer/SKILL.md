---
name: proposal-writer
description: Write or refine a proposal, scope document, or client-facing summary. Invoke with a brief slug or paste text inline. Enforces studio voice and the accuracy guard rails below directly (no external ACCURACY.md file exists).
allowed-tools: [Read, Write]
---

# Proposal Writer

Writes scope documents and proposals in the studio voice — specific, honest, no filler. Does not invent claims.

## Steps

### 1. Load context

If a brief slug is provided, read what exists (many of these paths are aspirational scaffolding that hasn't been built yet — treat a missing file as "not available," not an error, and note the gap in the SKILL VERIFICATION table rather than silently proceeding):
- `{CONTENT_DIR}/pipeline/briefs/{slug}.md`
- `{CONTENT_DIR}/pipeline/athena/{slug}-*.md` (latest Athena report, for scope and estimates)
- `{CONTENT_DIR}/portfolio/project-database.csv` (Mnemosyne) — if missing, verified first-person claims from Mark directly are an acceptable substitute for comps, but must be labeled as such (see BEA Phase 1 proposal draft, 2026-07-09, for the pattern)

Always read, regardless of brief slug:
- **Brand voice** — `{CONTENT_DIR}/internal/brand.md` if it exists; otherwise read the canonical master doc directly at `/media/data/Dropbox/Work/Content/Brand Voice/brand-voice.md`. Apply its `## Core voice` rules plus the `## Contexts` entry for proposals/client messages, if one exists. Do not write a word of client-facing copy before this.

If content is pasted inline, use it directly.

### 2. Write or refine

Produce the requested output. Common modes:

**Full proposal** — SKILL VERIFICATION table first (every claimed skill/comp cited to a project in Mnemosyne, or explicitly marked as Mark's direct first-person account if Mnemosyne is unavailable), then PROJECT BRIEF, PROPOSAL OUTPUT (≤5,000 chars), SCREENING QUESTIONS (pre-approved answers only if `{CONTENT_DIR}/snippets/questions-and-answers.md` exists; otherwise draft fresh and flag them as unreviewed), MILESTONES if fixed-price.

**Scope document** — Deliverables list, timeline, investment. Structured, no fluff.

**Refinement** — Apply studio voice, remove filler phrases, tighten structure. Do not change facts or scope.

### 3. Copywriter voice pass

Before returning output, apply the Copywriter's own voice rules from `.claude/skills/copywriter/SKILL.md` as an explicit self-review pass on the drafted text — do not just assert that studio voice was applied. For each violation found: quote the phrase, state the rule, rewrite it. Then return the corrected text, not a list of suggestions. Flag anything that reads as an unverifiable claim (stats without source, project references not in Mnemosyne) rather than silently keeping or dropping it.

### 4. Guard rails

- No em dashes in external-facing text
- No unverified project references (cite Mnemosyne, or Mark's direct account if Mnemosyne is unreachable — never invent)
- SKILL VERIFICATION table is non-negotiable in full proposals
- Fixed-price proposals must have milestones; hourly must not
- Brand voice (step 1) and the Copywriter pass (step 3) are both required, not optional, for any client-facing output
- The Law of the Gate: never send to a client without Mark's approval

### Output

Return the full written output. If saving to file, write to `{CONTENT_DIR}/pipeline/proposals/{slug}-{YYYY-MM-DD}.md`.
