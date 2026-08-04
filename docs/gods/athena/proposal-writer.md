---
description: Turns a completed proposal skeleton into a client-ready proposal in
  studio voice and generates the branded PDF
god: athena
invoke: /proposal-writer
role: Proposal writer
tags:
- skill
- agent
---

# Proposal Writer

Turns a filled-in proposal skeleton — or other supplied content — into a client-ready proposal in studio voice, then produces the branded PDF. Imposes structure, studio consistency, and brand voice; it does not gather or elicit content itself (that's `proposal-intake`).

## Invoke

```
/proposal-writer
```

Pass the completed skeleton from `proposal-intake`, or other proposal content directly (pasted text, attached files, facts stated inline). Proposal Writer does not read from the pipeline, Mnemosyne, or any snippet library — if comps, briefs, or estimates are needed, the caller supplies them.

If the input still contains `[NEEDS: ...]` markers, it stops and reports them back rather than writing around the gap or inventing a fill.

## Steps

1. **Load brand voice** — reads the master doc at `/media/data/Dropbox/Work/Content/Brand Voice/brand-voice.md`, mandatory before any copy is written
2. **Load the proposal template** — reads `$STUDIO_CONTENT_DIR/internal/proposal-template.md` (11-part structure, studio boilerplate for About/why us and Terms already written, `[NEEDS: ...]` markers on the sections that vary per client); rationale/source research in the sibling `$STUDIO_CONTENT_DIR/internal/2026-07-18-proposal-research.md`
3. **Write or refine** — new proposal works through the template top to bottom; refinement mode applies studio voice to an existing draft without changing facts or scope
4. **Write** — uses only facts/figures/comps supplied; never invents; unresolved gaps stay flagged
5. **Copywriter voice pass** — applies the Copywriter's voice rules (`/home/bain/.claude/skills/copywriter/SKILL.md`) as an explicit self-review, not an assertion
6. **Generate the branded PDF** — runs `brand-doc` on the finished draft; every run ends with a PDF, not just markdown

## Output format

Saved to a file, not returned as chat text — `proposal-{slug-or-topic}-{YYYY-MM-DD}.md` plus the branded PDF alongside it, in the caller's working directory unless an explicit path is given.

## Notes

- Fully decoupled from the Upwork prospecting pipeline (PIPE) — that pipeline generates and sends its own proposals internally and never hands off to this skill. See `athena.md` → Prospecting (Upwork Pipeline).
- No independent guardrails — voice and accuracy come only from brand voice (step 1) and the Copywriter pass (step 4), not from rules duplicated in this skill.
- No SKILL VERIFICATION table — output is the proposal document and PDF only.

## See also

- [proposal-intake.md](proposal-intake.md) — produces the skeleton this skill consumes
- [athena.md](athena.md) — parent god; proposal-intake and proposal-writer are both part of her household
