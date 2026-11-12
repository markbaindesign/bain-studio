---
tags:
  - workflow
  - utility
  - ia
  - content
description: How a site refresh gets its structure — inventory and evidence first, restructuring second, navigation last. Covers the claude.ai IA project and the source document format.
---

# Information Architecture

How the studio decides the structure of a site it is rebuilding or refreshing.

The principle: **audit before opinion.** Without evidence an IA session is an exchange of
preferences, and the client's preference wins because it is their site. With an inventory in
front of both parties, "these nine pages had no visit in twelve months" settles what no
argument can. Everything below exists to get that table on the table before anyone starts
moving boxes.

## Stages

| # | Stage | Produces | Where |
|---|---|---|---|
| 1 | Inventory | Every URL, its parent, its template | Local, scripted |
| 2 | Evidence | One row per page: traffic, queries, last modified | Local, scripted |
| 3 | Disposition | keep / merge / drop per page, with a reason | Local, written up |
| 4 | Restructure | The grouping, naming and depth, as a chart | claude.ai IA project |
| 5 | Navigation | Main, footer and any other menus | claude.ai IA project |
| 6 | Sign-off | Client's yes on the chart | Client's Dropbox `Docs/` |

Stages 1 to 3 are deterministic and belong in scripts. Stages 4 and 5 are judgement and
belong in conversation. Do not let them blur: a restructure started before the evidence is in
is guesswork wearing a chart.

### 1. Inventory

Every page, with true parentage rather than hierarchy guessed from URL depth. Against a local
DDEV or VVV copy of a WordPress site:

```bash
wp post list --post_type=page --fields=ID,post_title,post_name,post_parent --format=csv
```

With only a live URL, fall back to `/sitemap.xml` or `/wp-json/wp/v2/pages`, and note in the
write-up that parentage was inferred.

### 2. Evidence

Join to each row: GA4 sessions and entrances over twelve months, Search Console impressions
and clicks, and the last-modified date. Twelve months, because anything shorter misreads a
seasonal business as a dead one.

This is the gap in the current tooling. `/seo-audit` covers robots, metadata and Core Web
Vitals; `/ga-report` pulls GA4 into a client PDF. Neither produces the per-page inventory
with traffic joined to it, which is the artefact the whole workflow rests on. Until it
exists, the join is done by hand.

### 3. Disposition

One of four statuses per page, each traceable to its row:

| Status | Means | Obligation |
|---|---|---|
| `keep` | Earns its place, unchanged | — |
| `new` | To be written | — |
| `merge` | Absorbs one or more old pages | A redirect from every absorbed path |
| `drop` | Removed | A redirect to a sensible parent |

Every `merge` and every `drop` creates a redirect. Collect them as you go; a redirect map
assembled after launch is a redirect map with holes in it.

### 4 and 5. Restructure and navigate

Done in the claude.ai Information Architecture project. Its instructions and the chart
template live in `$STUDIO_CONTENT_DIR/internal/information-architecture/`.

The source of truth is a Markdown document: a `## Structure` section as a nested list, and
an optional `## Navigation` section of `###` lists referencing pages by path.

```markdown
## Structure

- Home `/` {front-page} [new]
- Work `/work/` {archive-project} [new]
  - Project `/work/{project}/` {single-project} [new]
- Contact `/contact/` {page} [keep]

## Navigation

### Main
- Work -> `/work/`
- Contact -> `/contact/`
```

Structure and navigation are deliberately separate. Structure answers where content lives and
what its URL is; navigation answers what gets exposed, where, and in what order. A page in no
menu is still part of the site, and a menu may promote a page from any depth.

Keep navigation until structure is signed off. Clients have only ever had to think about
menus, so given a menu to look at they will debate labels and never reach the grouping, which
is the decision that actually costs money to get wrong.

The chart's default view shows names and grouping only. Templates, statuses and redirect
notes sit behind a toggle, because a client shown build metadata argues about the wrong
things.

## Commercial note

The audit is its own stage with its own deliverable, scoped and paid for separately from the
rebuild. It routinely changes what the client wants built, which is a poor outcome to
discover inside a fixed-price build quote.

## What is not built

- The stage 2 join. No script yet; done by hand.
- The inventory extractor. Discussed, not written.
- Any PDF of the chart. The chart itself is the deliverable for now.

## See also

- `docs/utilities/seo-audit.md` — technical audit, overlaps stage 2 but does not replace it
- `docs/gods/aura/aura.md` — SEO strategy, reads audit data
- `/harmonia` — layout architecture, which is the next question after this one
