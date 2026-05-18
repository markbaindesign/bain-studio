---
name: pm-retro
description: Run a session retrospective. Extracts what was learned and routes each learning to the right place -- CLAUDE.md, rules, skills, docs, or ADRs. Invoke at the end of any working session.
---

# Session Retrospective

Review everything that happened in this session and produce a structured retrospective.

## Steps

1. **Summarise the session** in 2-3 sentences. What was the goal, what was completed, what was left unfinished.

2. **Extract learnings** by scanning the session for:
   - Decisions made (architectural or otherwise)
   - Constraints discovered (hosting, plugin, PHP version, client preference)
   - Patterns that worked or failed
   - Anything that had to be re-explained or corrected mid-session
   - Gotchas, edge cases, or non-obvious behaviour encountered

3. **Route each learning** to the correct destination:

   | Learning type | Destination |
   |---|---|
   | Project-wide conventions, data model, naming rules | `CLAUDE.md` |
   | Coding standards, patterns, anti-patterns | `.claude/rules/` |
   | Reusable workflows or domain knowledge | `.claude/skills/` |
   | Architectural or technology decisions | `docs/adr/NNN-title.md` |
   | General project reference | `docs/` |

4. **Output the retrospective** in the following format:

---

## Session Retro — YYYY-MM-DD

### Summary
What was done this session.

### Learnings

#### CLAUDE.md additions
- Each item as a bullet, ready to paste in.

#### Rule additions (`.claude/rules/`)
- Filename suggestion and content for any new rules.

#### Skill additions (`.claude/skills/`)
- Skill name and a one-line description for any new skills worth creating.

#### ADRs to write
- ADR title, decision summary, and date for any decisions that should be recorded.

#### Docs to update
- Filename and what needs adding or changing.

#### Nothing to action
- Any learnings that don't warrant a permanent record, noted here for completeness.

---

## Notes

- Do not pad the output. If there are no ADRs to write, omit that section.
- Phrase CLAUDE.md additions as terse bullet points, not prose.
- If a learning contradicts something already in CLAUDE.md or an existing ADR, flag the conflict explicitly rather than silently overwriting it.
