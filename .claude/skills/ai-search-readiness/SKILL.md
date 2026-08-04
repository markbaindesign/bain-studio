---
name: ai-search-readiness
description: Assess whether a site is ready to be crawled and cited by AI search tools (ChatGPT, Perplexity, Google AI Overviews, Claude) — AI bot access, llms.txt, structured data, and JS-rendering dependency. Distinct from /seo-audit (traditional technical SEO). Produces a report with prioritised action points, brandable via /brand-doc.
---

# AI Search Readiness Audit

Run a technical audit of how ready a site is to be crawled, understood, and cited by AI
crawlers and answer engines — as opposed to traditional search engine crawlers, which
`/seo-audit` already covers.

## When to use this vs. /seo-audit

- `/seo-audit` — titles, meta descriptions, canonicals, sitemaps, PageSpeed/Core Web Vitals.
- `/ai-search-readiness` (this skill) — AI-bot-specific robots.txt rules, llms.txt,
  structured data as an AI-citation signal, and JS-rendering dependency (many AI crawlers
  do not execute JavaScript).

They're complementary — run both for a full picture. If the user asks for "AI readiness,"
"AI SEO," "AI search," or similar, use this skill. If they cross-reference Google Analytics,
also check for an "AI Assistant" / AI-referral channel in GA4 (via `/ga-report`) as a
real-world signal that AI tools are already sending traffic.

## Steps

### 1. Identify URL and pages

Use the URL from the invocation argument. Default to the homepage; add up to 5
project-specific pages if the user names them or if the project's CLAUDE.md identifies
key content pages (evergreen educational/guide content is the highest-value target —
that's what AI answer engines cite most).

### 2. Determine output path

Save alongside other audits for this engagement — typically
`context/ai-search/ai-search-readiness-{YYYY-MM-DD}.md` in the current project directory,
or the equivalent working folder if this is prospecting/portfolio research rather than an
active client project.

### 3. Run the audit script

```bash
python3 /media/data/dev/bain-studio/studio/ai_search_readiness.py {BASE_URL} \
  --pages {COMMA_SEPARATED_PATHS} \
  --output {OUTPUT_PATH}
```

Runs in a few seconds — no external API calls, just direct fetches of robots.txt,
llms.txt, and the page(s) themselves.

The script checks:
- **AI bot crawl access** — explicit robots.txt rules (or lack thereof) for GPTBot,
  ChatGPT-User, ClaudeBot, Claude-Web, anthropic-ai, PerplexityBot, Google-Extended,
  Applebot-Extended, CCBot, Bytespider, Amazonbot.
- **llms.txt** — presence of the emerging curated-summary convention at the site root.
- **Structured data** — JSON-LD blocks and their `@type`s per page.
- **JS-rendering dependency** — raw HTML text length and SPA framework markers
  (Next.js, React root, Angular, Nuxt) as a proxy for whether a non-JS-executing
  crawler can read the real content.

### 4. Fill in Action Points

The script leaves an `## Action Points` placeholder. Replace it using this signal → action
framework — apply judgment, don't mechanically dump every row:

| Signal | Action | Priority |
|---|---|---|
| Any AI bot explicitly blocked | Remove the block (or confirm it's intentional) — this is a hard stop, not a degradation | HIGH |
| No JSON-LD on high-traffic/evergreen pages | Add `Organization` sitewide + `Article`/`FAQPage` on top content pages — highest-leverage lever for AI citation | HIGH |
| Content is JS-dependent (SPA markers or low text length) | Server-render or prerender key pages; AI crawlers that skip JS execution see nothing | HIGH |
| No llms.txt | Publish one — low effort, points AI crawlers at curated key content | MEDIUM |
| Meta description missing/too long | Fix per `/seo-audit` findings — AI summarizers often pull from it | MEDIUM |
| Existing "AI Assistant" GA4 channel already present | Note it as a baseline and recommend monthly monitoring post-fix | LOW |
| No AI-referral traffic yet in GA4 | Frame fixes as building a new channel rather than recovering a declining one | LOW |

Label each action point **[HIGH]**, **[MEDIUM]**, or **[LOW]**. Be specific — cite the
actual page, bot, or number from the report, not a generic restatement of the rule.

### 5. Read and summarise

Present to the user:
- Any blocking issues (bot blocks, JS-dependent content) — these are hard stops.
- Warning count (missing llms.txt, missing structured data).
- The filled-in action points, most impactful first.
- Any wins worth noting (e.g. "all major AI bots already have crawl access").

### 6. Offer to brand it

```
/brand-doc {OUTPUT_PATH}
```

**Known brand-doc gotcha:** its markdown renderer auto-links bare URLs, then separately
treats `_..._` as italics — if a URL contains an underscore (e.g. `sitemap_index.xml`),
the two regexes collide and corrupt the generated link markup, crashing the PDF build.
Avoid this by never writing a bare `https://...` URL containing an underscore in the
report; drop the scheme (`example.com/path_here`) or otherwise keep bare URLs
underscore-free. Also avoid headings that are just `/` (e.g. `### /`) — the anchor-slug
generator produces an empty name and crashes; write `### Homepage (/)` instead.

### 7. Offer to add blockers to backlog

If blocking issues were found, offer to add them as Asana tasks via studio-pm.

---

## Notes

- Script: `/media/data/dev/bain-studio/studio/ai_search_readiness.py`
- Works on any public URL — not WordPress-specific.
- Reports are dated and never overwritten — rerun after fixes to compare.
- "Explicitly allowed" vs. "inherits wildcard" both count as PASS (bot can crawl), but
  the distinction matters if the user wants deliberate, documented AI-bot policy rather
  than an accidental default-allow.
