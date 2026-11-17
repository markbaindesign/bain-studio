---
name: copywriter
description: "Studio voice review and copy editing. Pass any text (proposal, social post, email, UI copy, case study) and get it back edited in studio voice."
allowed-tools: [Agent]
---

# Copywriter

Convenience trigger. The voice gate itself is the **copywriter agent**, defined at
`/media/data/dev/bain-studio/.claude/agents/copywriter.md` and available globally.

## Steps

1. Spawn the copywriter agent via the Agent tool, `subagent_type: "copywriter"`.
2. Pass it the full text, plus the scope (public-facing or internal) and the context
   (client email, quick message, proposal, case study, social post, Upwork proposal,
   theme review, UI copy).
3. She works unsupervised. Given file paths she edits them in place; given inline
   text she returns it corrected. Relay her report to Mark verbatim - he is the final
   gate. Do not re-review her edits or soften her findings.

## Why there are no voice rules in this file

They used to be here, as a hardcoded list, and it drifted into a stale subset of the
real rules - missing the banned words, the sign-off rules and the per-context
registers. The rules live in one place only:
`/media/data/Dropbox/Work/Content/Brand Voice/brand-voice.md`, maintained via
`/brand-voice` and loaded into every session. The agent reads it at review time.
**Do not restate voice rules here.**
