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
| 3 | Content audit | What each destination is worth, and what is missing | Local, part scripted |
| 4 | Disposition | keep / merge / drop / new per destination, with a reason | Local, written up |
| 5 | Restructure | The grouping, naming and depth, as a chart | claude.ai IA project |
| 6 | Navigation | Main, footer and any other menus | claude.ai IA project |
| 7 | Sign-off | Client's yes on the chart | Client's Dropbox `Docs/` |

Stages 1 and 2 are deterministic and belong in scripts. Stage 3 is half each. Stages 4 to 6
are judgement. Do not let them blur: a restructure started before the audit is in is
guesswork wearing a chart.

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

#### Triage before the client sees it

The client's time goes on decisions. An inventory handed over raw makes them mark tag
archives "delete" one by one and puzzle over a login page from a membership plugin removed
years ago. Every such row is a decision the studio could have taken, or one with no decision
in it at all. So the inventory is triaged before it leaves the studio, every time:

| Row | Treatment |
|---|---|
| Archive WordPress generates (tag, category, author, date, custom taxonomy, search, feed, pagination) in no menu | Removed. Nothing to decide |
| The same archive linked from a menu | Kept, marked `check`. The client put it there, which is a decision |
| Known obsolete: plugin leftovers, test pages, duplicates the studio is sure of | Removed, with the reason |
| Probably obsolete, or not content (a page that only lists one tag's posts) | Kept, marked `check` with the reason, for the client to confirm |

The tool removes generated archives by default. Known rows come from a per-project rules file
kept in the client's Dropbox `Docs/Information Architecture/` folder, never in a public repo:

```text
# action  path glob            reason the client reads
drop      /login/              membership plugin, removed
check     /video-library/      a listing of one tag's posts, not content
```

```bash
site-inventory.py --url https://{production}/ --menus --content --format csv \
  --rules "{Dropbox}/Docs/Information Architecture/inventory-rules.txt" \
  --excluded {date}-inventory-excluded.csv -o {date}-inventory.csv
```

Write the rules file by reading the raw inventory once before the first handover: a row the
studio would mark without asking the client belongs in it. **Nothing vanishes silently.** The
removed rows go to the `--excluded` file with a disposition of `drop`, because a removed page
still needs a redirect (stage 4). Keep it next to the inventory.

### 2. Evidence

Join to each row: GA4 sessions and entrances over twelve months, Search Console impressions
and clicks, and the last-modified date. Twelve months, because anything shorter misreads a
seasonal business as a dead one.

This is the gap in the current tooling. `/seo-audit` covers robots, metadata and Core Web
Vitals; `/ga-report` pulls GA4 into a client PDF. Neither produces the per-page inventory
with traffic joined to it, which is the artefact the whole workflow rests on. Until it
exists, the join is done by hand.

### 3. Content audit

Traffic says what gets visited. It does not say whether what is there is any good, and it
says nothing at all about what is absent. Audit the content before rebuilding the tree, or
the new structure is a tidier arrangement of the same problems.

**What is there.** Per destination, and largely scriptable: word count, last modified, the
H1, the meta description, images and how many lack alt text, internal links in and out,
broken links, and whether two destinations say the same thing in different words. Thin,
stale and duplicated content is found here, not in the traffic.

**What is missing.** This cannot be found by looking at the site, which is the trap. A site
audit can only tell you what is weak, never what is absent. Gaps come from outside it:

| Source of a gap | What it shows |
|---|---|
| The client's goals and audiences | Who the site must serve, and for whom there is no content |
| The journeys the site must support | A step with no page: no pricing, no proof, no next action |
| Search Console queries | Demand with impressions and no page that answers it |
| Competitor sites | What the sector treats as table stakes |
| The client's own list | What they have been meaning to write for two years |

Every gap becomes a `new` destination in the disposition, and `new` pages are the reason an
IA review is worth paying for. A review that only prunes produces a smaller version of the
site the client already had.

### 4. Disposition

One of four statuses per destination, each traceable to its row and its audit:

| Status | Means | Obligation |
|---|---|---|
| `keep` | Earns its place, unchanged | — |
| `new` | A gap found in stage 3. To be written | A brief, and someone to write it |
| `merge` | Absorbs one or more old pages | A redirect from every absorbed path |
| `drop` | Removed | A redirect to a sensible parent |

Every `merge` and every `drop` creates a redirect. Collect them as you go; a redirect map
assembled after launch is a redirect map with holes in it.

### 5 and 6. Restructure and navigate

Done in the claude.ai Information Architecture project. Its instructions and the chart
template live in this repo, in `studio/ia/`:

| File | What it is |
|---|---|
| `studio/ia/project-instructions.md` | The project's instructions: source document format, how to restructure and chart |
| `studio/ia/sitemap-chart-template.html` | The chart the project renders a sitemap into |

The repo is the only copy. The claude.ai project reads both through the GitHub integration,
as project knowledge on `main`, so it follows released versions only. Its Instructions box
holds one line pointing at them, because GitHub files can fill a project's knowledge but not
its instructions:

> Follow `project-instructions.md` in this project's knowledge, and render charts with
> `sitemap-chart-template.html`.

Syncing is manual. After a release that changes either file, click **Sync now** in the
project's knowledge. A file or folder added since the repository was attached may not appear
in the picker even after a sync: remove the repository from the project and add it again.

`site-inventory.py` (bain-tools) writes an existing site's first source document in this
format: `## Structure` from the site, `## Navigation` from its menus with `--menus`.

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
