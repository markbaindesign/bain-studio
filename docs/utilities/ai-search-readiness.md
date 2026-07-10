---
tags: [skill]
invoke: /ai-search-readiness
description: Technical audit of AI-crawler readiness (bot access, llms.txt, structured data, JS-rendering dependency) — distinct from /seo-audit
---

# ai-search-readiness

Assesses whether a site is ready to be crawled and cited by AI search tools (ChatGPT, Perplexity, Google AI Overviews, Claude) — AI bot access, `llms.txt`, structured data, and JS-rendering dependency. Complementary to `/seo-audit`, which covers traditional technical SEO (titles, meta, sitemaps, Core Web Vitals) rather than AI-crawler-specific signals.

## Usage

```
/ai-search-readiness {url}
```

Runs `studio/ai_search_readiness.py` against the given URL and produces a dated report with prioritised action points. Reports are never overwritten — rerun after fixes to compare.

## What it checks

- Explicit `robots.txt` rules for AI bot user-agents (GPTBot, ChatGPT-User, ClaudeBot, anthropic-ai, PerplexityBot, Google-Extended, etc) vs. inherited wildcard allow/deny
- `llms.txt` presence
- Structured data as an AI-citation signal
- JS-rendering dependency — many AI crawlers don't execute JavaScript, so content that only renders client-side is invisible to them

## Notes

- Works on any public URL — not WordPress-specific
- Report output is brandable via `/brand-doc`
- Known blooper: bare URLs containing an underscore can collide with the report's link-markup regex and crash the PDF build — keep bare URLs underscore-free or drop the scheme; also avoid headings that are just `/`
- Can offer to add blocking issues to the Asana backlog via studio-pm

## Source

`.claude/skills/ai-search-readiness/SKILL.md` — symlinked to `~/.claude/skills/ai-search-readiness` for access from any project. Script: `studio/ai_search_readiness.py`.
