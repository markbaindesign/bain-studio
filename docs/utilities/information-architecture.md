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

**The inventory is a flat list of destinations.** Structure and navigation are two views over
it, not the thing itself. Make either one the spine and it becomes the truth by default, with
the other recorded as a set of exceptions to it, which is exactly the bias this stage exists
to avoid.

**A destination is anything the site goes to**, not only a WordPress page. A taxonomy archive
is not a page to WordPress and is entirely a page to the client, who put it in the menu.
Inventory it, classified by what renders there, rather than reporting it as an anomaly.

One row per destination, carrying its place in the page tree *and* its place in each menu.
A row at tree depth 0 and menu depth 1 is a top-level page the navigation presents as a
child. That is not an error in either place. It is the finding.

**Take it from production.** Only the live site has an accurate structure. A local DDEV or
VVV copy is a snapshot of whenever it was pulled, and clients add, rename and delete pages
without telling anyone, so a local copy will quietly disagree with the site the client is
looking at. An IA review built on a stale tree is worse than none, because it looks
authoritative.

```bash
site-inventory.py --url https://{production}/ --title "{Client}"
```

That reads `/wp-json/wp/v2/pages`, which carries real `post_parent` values. If the REST API
is closed, the tool falls back to the XML sitemap, hierarchy becomes inferred from path depth
and the output says so. Where that matters, run WP-CLI against production over SSH instead:

```bash
site-inventory.py --wp . --wp-cmd "wp ssh --host=prod"
```

The same reasoning drives `/prod-reconcile`: production is the source of truth for content,
and local is the source of truth for code.

Read the navigation at the same time, as a **separate** fact:

```bash
site-inventory.py --url https://{production}/ --menus
```

A menu is not the page tree. Menu items carry their own parent, so a menu can nest two pages
that have no parent-child relationship and can leave out pages that do. Read the **front end**
for this, not the database: plenty of sites do not use `wp_nav_menu` at all, and a mega-menu
plugin, a page builder or hand written markup produce navigation with no WordPress menu markup
on it. The front end is also the structure the client and their visitors actually experience,
which is the thing an IA review is about.

**Where the front end and the database disagree, that disagreement is the finding.** A menu
nesting four top-level pages under About Us tells you what the client believes the structure
is, whatever `post_parent` says. Record both and reconcile them in stage 3.

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

- `/prod-reconcile` — the same production-first principle, applied to content before a deploy
- `docs/utilities/seo-audit.md` — technical audit, overlaps stage 2 but does not replace it
- `docs/gods/aura/aura.md` — SEO strategy, reads audit data
- `/harmonia` — layout architecture, which is the next question after this one
