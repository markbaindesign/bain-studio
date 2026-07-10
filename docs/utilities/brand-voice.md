---
tags: [skill]
invoke: /brand-voice
description: Tune Mark's brand voice rules — what he would and wouldn't say in a particular context — and maintain the master brand voice doc
---

# brand-voice

Interviews Mark to capture and refine his writing voice, one context at a time (cold outreach, client messages, social posts, proposals, etc), and keeps the results in a single canonical file.

## Usage

```
/brand-voice                      # list documented contexts, offer to tune one or run an audit
/brand-voice show                 # print the full master doc
/brand-voice audit                # check for contradictions between contexts and Core voice
/brand-voice "cold outreach"      # targeted interview for that context
```

## Files

- **Master doc:** `/media/data/Dropbox/Work/Content/Brand Voice/brand-voice.md` — canonical source, personal/general (not studio-only). Structured as `## Core voice` (always-on rules) plus `## Contexts` (situational registers layered on top).
- **Agent-facing pointer:** `{STUDIO_CONTENT_DIR}/internal/brand.md` — the compact summary read by Copywriter, Nike, Aura, and Anteros. Points to the master doc rather than duplicating it.

## Design notes

- Only records rules Mark has explicitly confirmed in conversation — never inferred from adjacent contexts.
- Each context is captured via interview: a concrete example of what he'd say, what he wouldn't, how it differs from Core voice, and any fixed conventions (sign-offs, emoji, etc).
- `audit` mode flags contexts that silently contradict Core voice or each other, without auto-fixing — Mark decides which side wins.

## Source

`.claude/skills/brand-voice/SKILL.md` — symlinked to `~/.claude/skills/brand-voice` for access from any project.
