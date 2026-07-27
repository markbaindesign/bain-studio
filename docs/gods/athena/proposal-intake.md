---
description: Turns raw client input (RFP, emails, call notes) into a proposal skeleton
  mapped to the studio structure, flagging every gap that still needs filling
god: athena
invoke: /proposal-intake
role: Intake / elicitor
tags:
- skill
- agent
---

# Proposal Intake — Elicitor

Takes raw client input and maps it onto the studio's 12-part proposal skeleton, so gaps are visible before any client-facing copy gets written. This is a scaffolding step, not a writing step — output is a working document with source material mapped in and explicit `[NEEDS: ...]` markers, not client-ready prose.

## Invoke

```
/proposal-intake
```

Pass raw client input directly (pasted RFP text, attached files, notes stated inline). Proposal Intake does not read from the pipeline, Mnemosyne, or any snippet library — it works only from what's supplied in the request.

## What it produces

A skeleton mapped to the 12-part structure defined in `$STUDIO_CONTENT_DIR/internal/proposal-template.md` (rationale/source research in the sibling file `$STUDIO_CONTENT_DIR/internal/2026-07-18-proposal-research.md`):

1. Cover, 2. Executive summary, 3. The problem, 4. Proposed approach, 5. Deliverables, 6. Timeline, 7. Investment, 8. Case Studies, 9. Assumptions & out of scope, 10. About / why us, 11. Next steps, 12. Terms

Populated where the source material supports it; every unfilled section is marked `[NEEDS: ...]`. Below the skeleton, a flat checklist of every gap. Sections 10 (About/why us) and 12 (Terms) are pre-filled with studio boilerplate in the template and are rarely gaps.

## Output format

Saved to a file, not returned as chat text — `skeleton-{slug-or-topic}-{YYYY-MM-DD}.md` in the caller's working directory unless an explicit path is given.

## Notes

- No voice pass, no brand voice, no polish — deliberately plain scaffolding. That happens downstream.
- Investment and case studies are almost never present in raw client input; expect these to default to `[NEEDS: ...]` on nearly every run. About/why us and Terms use studio boilerplate from the template, not elicitation.
- Once the gaps are filled (by Mark), the completed skeleton is the required input for `proposal-writer`.

## See also

- [proposal-writer.md](proposal-writer.md) — consumes the completed skeleton, imposes structure/voice, produces the branded PDF
- [athena.md](athena.md) — parent god; proposal-intake and proposal-writer are both part of her household
