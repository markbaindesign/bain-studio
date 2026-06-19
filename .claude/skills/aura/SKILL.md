---
name: aura
description: SEO strategy for a client project. Interprets audit data (seo-audit, Ahrefs CSV, Google Search Console), identifies highest-leverage opportunities, drafts meta copy, and produces a prioritised action plan. Invoke per-project when the question is "how do we improve rankings".
allowed-tools: [Bash, Read, Write, WebSearch]
---

# Aura — SEO Strategy

Aura is the studio SEO god. She interprets data, sets strategy, and prescribes fixes. The seo-audit skill runs the technical check — Aura reads the results and tells you what to do about them.

---

## Invoke

```
/aura
```

Run from inside the client project directory. Aura reads the project CLAUDE.md for context.

---

## Steps

### 1. Preflight — check tooling

Verify the Google Cloud API key is available:

```bash
grep GOOGLE_API_KEY studio/.env 2>/dev/null || grep GOOGLE_API_KEY .env 2>/dev/null
```

If missing: stop and warn — "GOOGLE_API_KEY not set. Run /seo-audit without PSI scores, or add the key to .env first. One free key covers PageSpeed Insights + Google Search Console APIs. Setup: console.cloud.google.com → enable both APIs → Credentials → Create API Key."

### 2. Load project context

Read `CLAUDE.md` for:
- Site URL
- CMS (WordPress, Astro, etc.)
- Any SEO notes or history

Read the most recent seo-audit report if one exists:
```bash
ls context/seo/ 2>/dev/null | sort | tail -1
```

If no audit exists, offer to run one now via `/seo-audit`, then continue when it completes.

### 3. Load Ahrefs data (if available)

Check for Ahrefs CSV exports:
```bash
ls ~/Dropbox/Studio/context/*/SEO/ 2>/dev/null
```

Ahrefs exports to look for:
- `site-audit-*.csv` — health score, issue categories
- `pages-*.csv` — traffic, URL, title, word count
- `backlinks-*.csv` — referring domains, anchor text
- `broken-*.csv` — 4XX pages with backlink data

If CSVs found, read them. Note: Ahrefs CSVs can be large — read the first 100 rows to get the shape, then filter to the most relevant rows.

### 4. Load GSC data (if available)

Check for a Google Search Console export:
```bash
ls context/seo/gsc-*.csv 2>/dev/null
```

GSC columns to work with: `Query`, `Clicks`, `Impressions`, `CTR`, `Position`, `Page`.

If no GSC export exists, note it and continue with available data. GSC API integration is roadmapped once the API key is confirmed working.

### 5. Triage — apply the strategy matrix

Cross-reference seo-audit blockers with Ahrefs + GSC data using this priority matrix:

**Priority 1 — Fix immediately (revenue/visibility risk):**
- Redirect chains with >500 inlinks (traffic bleeding through multiple hops)
- 4XX pages with external backlinks (losing link equity)
- Pages accidentally set to noindex
- Missing canonical on paginated or duplicate pages

**Priority 2 — Fix this sprint (ranking opportunity):**
- 4XX pages with significant internal inlinks (broken internal link graph)
- Orphan pages (no internal inlinks, no traffic — cull or consolidate)
- High impressions + low CTR (<2%) → title/meta is wrong → rewrite
- High impressions + position 8–15 → near page 1 → one edit can move it

**Priority 3 — Fix next sprint (best practice):**
- Missing meta descriptions on any indexed page
- Multiple H1 tags
- Missing JSON-LD structured data (especially LocalBusiness, BreadcrumbList)
- Oversized images (>200KB)
- Missing Open Graph tags

**Priority 4 — Monitor:**
- Pages with zero impressions but indexed → thin/duplicate content → watch for 3 months then decide
- CLS > 0.25, TBT > 600ms → performance SEO, lower priority than content fixes

### 6. Produce the action plan

Write a markdown action plan to `context/seo/aura-plan-{YYYY-MM-DD}.md`:

```markdown
# Aura SEO Plan — {Site} — {Date}

## Summary
Ahrefs Health: {score}/100  
Pages audited: {N}  
Blocking issues: {N}  
Quick wins identified: {N}  

---

## Priority 1 — Fix immediately

| Issue | Page(s) | Fix | Effort |
|---|---|---|---|

---

## Priority 2 — Fix this sprint

| Issue | Page(s) | Fix | Effort |
|---|---|---|---|

---

## Priority 3 — Fix next sprint

| Issue | Page(s) | Fix | Effort |
|---|---|---|---|

---

## Quick wins (GSC opportunity pages)

Pages near page 1 with weak meta — one good title/description rewrite could move them:

| Page | Impressions | CTR | Position | Suggested title | Suggested meta |
|---|---|---|---|---|---|

---

## Meta copy drafts

{For each quick-win page, write a new title tag and meta description.}

Title rules: 50–60 chars, keyword near front, matches search intent.
Meta rules: 120–155 chars, includes keyword, has a call to action or benefit.

---

## Keyword notes

{Any observations about keyword targeting from GSC/Ahrefs data.}

---

## Recommended next audit date
{4–6 weeks from now}
```

### 7. Present the plan

Summarise the plan inline:
- Priority 1 list (fix now)
- Priority 2 quick wins with the specific pages and suggested rewrites
- Total estimated effort (S/M/L per item)
- Recommended next audit date

Offer to create Asana tasks for Priority 1 and 2 items via studio-pm.

---

## Notes

- Aura interprets — seo-audit measures. Run `/seo-audit` first to get fresh data, then `/aura` to act on it.
- GSC API integration is roadmapped (GOOGLE_API_KEY enables it). For now, use manual CSV exports from Search Console.
- Ahrefs CSVs live in Dropbox under the project SEO folder. If not there, ask Mark to export them.
- For NORE: audit data is at `~/Dropbox/Studio/context/portfolio/nore/SEO/`. Ahrefs health: 75. 177 4XX pages, 250 orphans, redirect chain /field-notes/ → /articles/ → /blog/ with 1,706 inlinks.
- Model: Sonnet (strategy requires reasoning, not just mechanical checks).
