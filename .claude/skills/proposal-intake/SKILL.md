---
name: proposal-intake
description: Turn raw client input (RFP, emails, call notes, brief) into a proposal skeleton mapped to the studio's proposal structure, then elicit answers to every gap one at a time from Mark before saving. Feeds proposal-writer. Does not touch the pipeline, Mnemosyne, or snippet libraries — always scans the invoking folder for source material, plus whatever's supplied with the invocation.
allowed-tools: [Read, Write, Glob]
---

# Proposal Intake

Takes raw client input, structures it against the studio's 12-part proposal skeleton, then walks Mark through every resulting gap one question at a time until the skeleton is complete. This is a scaffolding step, not a writing step — the saved output is a working document with source material mapped in, not client-ready prose. **The skeleton is never sent to the client** — it is internal-only, a handoff artifact for `proposal-writer`, which is the only skill that produces client-facing output.

Source material is always the current working directory (the folder this skill was invoked from), plus anything supplied directly in the request (pasted text, attached files, notes stated inline). Does not read from or write to the pipeline, Mnemosyne, or any snippet library.

## Steps

### 1. Read source material

Always scan the current working directory (the folder this skill was invoked from) for anything that looks like client source material — RFPs, briefs, notes, transcripts, emails saved as files (`.md`, `.txt`, `.pdf`, `.docx`, etc). List what you find before reading it, so it's clear what's feeding the skeleton. Skip anything already produced by this pipeline (existing `skeleton-*.md` or `proposal-*.md` files) — those are output, not source.

Also take whatever's supplied directly in the request — pasted text, attached files, notes stated inline. Combine it with what the folder scan found.

If neither the folder scan nor the request turns up anything usable, say so and stop rather than guessing at content.

Read everything gathered, from both sources, in full before mapping anything.

### 2. Map onto the skeleton

Populate what the source material supports; mark everything else as a gap. Use this structure:

```bash
source /media/data/dev/bain-studio/studio/.env
cat "$STUDIO_CONTENT_DIR/internal/proposal-template.md"
```

(Rationale/source research for the structure is in the sibling file
`$STUDIO_CONTENT_DIR/internal/2026-07-18-proposal-research.md` if background is needed.)

1. **Cover** — client name (from source, or `[NEEDS: client name]`)
2. **Executive summary** — client's stated goal, in their words if available
3. **The problem** — pull 2 specifics directly from the source; do not paraphrase into generic language
4. **Proposed approach** — draft a phase/workstream breakdown if the source implies one; otherwise `[NEEDS: approach]`
5. **Deliverables** — list anything explicitly requested or implied; flag anything under-specified as `[NEEDS: deliverable count/detail]`
6. **Timeline** — dates/deadlines mentioned in source; otherwise `[NEEDS: timeline]`
7. **Investment** — this is almost never in the source. Default to `[NEEDS: pricing — tier structure? breakdown by part? payment terms?]`
8. **Case Studies** — leave as `[NEEDS: comps/case studies — sector-matched]` unless the caller supplies specific ones
9. **Assumptions & out of scope** — draft likely exclusions based on what's requested vs. adjacent scope not mentioned; flag for review, don't assume final
10. **About / why us** — already covered by studio boilerplate in the template; no gap to elicit unless this engagement needs a different pitch
11. **Next steps** — `[NEEDS: next action + validity date]`
12. **Terms** — already covered by studio boilerplate in the template; no gap to elicit unless this engagement needs different terms

### 3. Elicit answers, one question at a time

Do not dump the `[NEEDS: ...]` list and wait for a bulk reply. Step through the skeleton in order (cover through terms) and for each gap:

1. Ask a single, specific question — give the surrounding context you already have (e.g. "Investment: the source doesn't mention budget. Fixed-price or hourly? Any figure or range Mark has in mind?"), not just the bare `[NEEDS: ...]` label.
2. Wait for the answer before moving to the next gap.
3. Write the answer straight into the skeleton section it belongs to, replacing the `[NEEDS: ...]` marker.
4. If Mark's answer is itself "I don't know yet" or "skip it," leave the marker in place rather than inventing a placeholder, and move on — don't get stuck.

Sections with no gap (fully supported by source material) are skipped in this pass — nothing to elicit.

### 4. Do not write final copy

Keep language close to source material and to Mark's own answers, not polished prose — no studio voice pass, no brand voice pass. That happens in `proposal-writer`, once the skeleton is complete.

### Output

Once every gap has been stepped through (answered or explicitly left open), save the skeleton to a file — do not return it as chat text. If the caller gave an explicit save location, use it. Otherwise save into the current working directory (the directory this skill was invoked from), named `skeleton-{slug-or-topic}-{YYYY-MM-DD}.md` — this exact `skeleton-*.md` pattern is what `proposal-writer` scans for, so don't deviate from it. After saving, reply with the file path and a short summary of what's still marked `[NEEDS: ...]`, if anything.

This file is a working document, not a deliverable — do not send it, or any part of it, to the client under any circumstances.
