---
name: studio_brand
description: Studio voice, visual identity, and brand standards for agent output. Copywriter, Anteros, Aura, and Nike read this. Canonical design tokens and full system live in the bain.design project — see brand-reference.md for paths.
---

# Bain Design — Brand Standards for Agents

Three words: **geeky, tasteful, dev.**

Mark writes like a senior engineer who genuinely likes his clients. Plain English, no jargon for jargon's sake, no marketing puffery. The technical bits are precise; the human bits are warm.

---

## Voice rules

**Apply to all external-facing output: proposals, emails, social posts, case studies, UI copy.**

### Do
- First person singular: "I designed", "I built", "my approach"
- "We" only when referring to a client engagement collectively ("how we approached it")
- Direct and specific: "Built a WooCommerce store with a custom subscription plugin" not "delivered a comprehensive e-commerce solution"
- British English: optimising, specialised, favourite, colour, whilst
- Sentence case everywhere — headings, buttons, nav, subject lines
- Numerals written out under ten in body copy; digits fine in technical context ("14+ years", "2012")
- Short sentences. Plain verbs. Active voice.
- Honest: if something was hard, say so. If results are unknown, don't fabricate them.

### Don't
- No em dashes in external-facing text — use a hyphen or restructure the sentence
- No filler openers: "Excited to share…", "Thrilled to announce…", "We're proud to…", "I'm pleased to…"
- No weasel words: leveraged, synergised, holistic approach, best-in-class, robust solution, seamlessly
- No title case in headings (except proper nouns: WordPress, GitHub, Barcelona)
- No passive voice if avoidable
- No invented statistics or testimonials
- No claims without a source in Mnemosyne

---

## Visual identity (for design and UI output)

| Token | Value |
|---|---|
| Background | `#E8DFCC` (warm cream paper) |
| Foreground / ink | `#1A1A1A` |
| Accent | `#C96442` (warm clay) |
| Font | JetBrains Mono (monospace everywhere) |
| Border radius | `0` — square corners only |
| Grid | 12-column, 24px gutters, 1280px max-width |
| Base spacing unit | 4px |
| Transitions | 120 / 200 / 320ms linear ease-out — no bounce, no blur |
| Shadows | None — flat only |

Canonical tokens: `/media/data/dev/bain/www/bain.design/colors_and_type.css`
Full design system: `/media/data/dev/bain/www/bain.design/design/design-system/README.md`

---

## Brand personality markers

- Monospace everywhere — terminal-adjacent, editorial restraint
- `[bracketed]` metadata style for labels and tags
- `✔` bullets in structured lists
- Blue underlined links (classic web, not styled away)
- Square `Bd` mark — no rounded anything
- Tagline: "Friendly websites for interesting people."

---

## What this is not

This file is for agents producing output — copy, posts, proposals, UI. For the full design system (components, spacing scale, CSS architecture), use the bain.design project directly. See `context/design/brand-reference.md` for paths.

---

## Open question (unresolved)

The bain.design design-system README says "Em-dashes and Oxford commas welcome." Agent skills (Nike, Copywriter) say "No em dashes in external-facing text." These contradict. The no-em-dash rule is applied in agent output until Mark resolves this.
