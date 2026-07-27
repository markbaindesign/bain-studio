---
name: proposal-writer
description: Turn a completed proposal skeleton (from proposal-intake) or other supplied content into a client-ready proposal in studio voice, using the studio's researched proposal structure, then generate the branded PDF. Always scans the invoking folder for a proposal-intake skeleton, plus whatever's supplied with the invocation. Does not touch the pipeline, Mnemosyne, or snippet libraries.
allowed-tools: [Read, Write, Bash, Glob]
---

# Proposal Writer

Turns a filled-in proposal skeleton — or other supplied content — into a client-ready proposal in studio voice, then produces the branded PDF. Imposes structure, studio consistency, and brand voice; it does not gather or elicit content itself (that's `proposal-intake`).

Source material is always the current working directory (the folder this skill was invoked from), plus anything supplied directly in the request (pasted text, attached files, facts stated inline). Does not read from or write to the pipeline, Mnemosyne, or any snippet library — if comps or estimates are needed, the caller supplies them.

If the input still contains `[NEEDS: ...]` markers, stop and report them back rather than writing around the gap or inventing a fill.

## Steps

### 1. Read source material

Always scan the current working directory (the folder this skill was invoked from) for a `proposal-intake` skeleton — files matching `skeleton-*.md`. If more than one is present, use the most recent by date in the filename and note the others.

Also take whatever's supplied directly in the request — pasted text, attached files, facts stated inline. Combine it with the skeleton if both are present.

If neither the folder scan nor the request turns up anything usable, say so and stop rather than guessing at content.

### 2. Load brand voice (always, mandatory)

Read the master brand voice doc at `/media/data/Dropbox/Work/Content/Brand Voice/brand-voice.md`. Apply its `## Core voice` rules plus any `## Contexts` entry for proposals/client messages. Do not write a word of client-facing copy before this.

### 3. Load the proposal template

```bash
source /media/data/dev/bain-studio/studio/.env
cat "$STUDIO_CONTENT_DIR/internal/proposal-template.md"
```

This is the working template — 12-part structure, fixed boilerplate for "About / why us" and
"Terms" already written, `[NEEDS: ...]` markers on the sections that vary per client.
Rationale/source research for the structure is in the sibling file
`$STUDIO_CONTENT_DIR/internal/2026-07-18-proposal-research.md` if background is needed, but
the template file is what to actually fill in.

### 4. Write or refine

**New proposal** — Work through the template top to bottom, replacing each `[NEEDS: ...]`
marker with content drawn from the skeleton/source material gathered in step 1. Leave the
"About / why us" and "Terms" sections as-is unless this specific engagement genuinely
requires different terms. Investment tiers (Essential/Recommended/Complete) are optional —
use them only for projects large or ambiguous enough that scope is a real client decision;
skip them for small, well-defined jobs.

Non-negotiable sections: the problem, deliverables, investment, assumptions & out of scope, next steps. Keep the whole document to 6-8 pages; the executive summary must stand alone.

**Refinement** — Apply studio voice to an existing proposal draft, remove filler, tighten structure. Do not change facts or scope.

### 5. Write

Use only the facts, figures, and comps gathered in step 1. Never invent client details, project references, or statistics. If a case study or comps are wanted but weren't supplied, mark the gap inline as a bracketed `[NEEDS: ...]` note rather than fabricating something or silently dropping the section.

### 6. Copywriter voice pass

Apply the Copywriter's voice rules (`/home/bain/.claude/skills/copywriter/SKILL.md`) as an explicit self-review pass on the drafted text — quote each violation found, state the rule, rewrite it, and apply the fix. Do not just assert that studio voice was applied.

### 7. Generate the branded PDF

Once the `.md` draft is saved, run `brand-doc` on it to produce the client-ready PDF (see `/home/bain/.claude/skills/brand-doc/SKILL.md` for the invocation contract). This is not optional — every proposal-writer run ends with a PDF, not just a markdown draft.

### Output

Save the finished proposal to a file — do not return it as chat text. If the caller gave an explicit save location, use it. Otherwise save into the current working directory (the directory this skill was invoked from), named `proposal-{slug-or-topic}-{YYYY-MM-DD}.md`, with the PDF alongside it. After saving, reply with both file paths and a one-line summary of what was produced.
