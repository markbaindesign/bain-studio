---
name: ga-report
description: Pull Google Analytics 4 data for a client project and compile a branded benchmark report with action points. Authenticates via service account, fetches sessions/users/channels/pages/devices, draws charts, writes a markdown report to the client's Dropbox folder, and outputs a branded PDF via brand-doc.
allowed-tools: [Read, Bash, Write]
---

# GA Report

Pull GA4 data and compile a client-ready benchmark report.

## Usage

```
/ga-report NORE
/ga-report NORE --property 542141660
/ga-report NORE --days 30
/ga-report NORE --property 542141660 --days 90
```

Arguments:
- `PROJECT` — project prefix (required). Used to look up client name and output path.
- `--property ID` — GA4 property ID (numeric). If omitted, reads `ga4_property:` from the project file or prompts.
- `--days N` — reporting period in days (default: 90).

---

## Auth setup (one-time per workspace)

The fetcher authenticates via a Google service account.

**Requirements:**
1. A Google Cloud project with the **Google Analytics Data API** enabled
2. A service account with the JSON key downloaded
3. The service account email added as a **Viewer** on the GA4 property
4. `GOOGLE_SA_JSON=/path/to/sa.json` added to `studio/.env`

Recommended key location: `~/.config/bain-studio/google-sa.json` (outside any git repo)

If `GOOGLE_SA_JSON` is not set, ask Mark for the path before proceeding.

---

## Steps

### 1. Parse arguments

Extract `PROJECT`, `--property`, and `--days` from the invocation. Uppercase the prefix.

### 2. Look up project details

Read the project file from `docs/projects/{slug}.md` (match by prefix). Extract:
- `name:` — client/project name for the report title
- `ga4_property:` — GA4 property ID
- `client_docs:` — the client's Dropbox docs folder (where the report is saved, see step 7)

If `--property` was not supplied and no property ID is found in the project file, ask for it.

### 3. Check credentials

```bash
source /media/data/dev/bain-studio/studio/.env
echo $GOOGLE_SA_JSON
```

If `GOOGLE_SA_JSON` is empty or the file does not exist, stop and explain the one-time auth setup above.

### 4. Fetch GA4 data

```bash
python3 /media/data/dev/bain-studio/studio/collectors/ga4_report.py \
  --property {PROPERTY_ID} \
  --sa-json {GOOGLE_SA_JSON} \
  --days {DAYS} > {SCRATCH}/ga.json
```

Save the output to a file in the scratchpad: the chart step (7) reads it.

If this fails with a permission error, the service account likely hasn't been added to the GA4 property. Show the service account email from the JSON file and instruct Mark to add it in GA4 → Admin → Property Access Management.

Capture the JSON output into a variable for analysis.

By default the collector excludes sessions whose landing page is "(not set)" from
every figure (`"excludes_not_set_landing": true`). They have no page view, usually
because a visitor returned to an idle tab after GA4's 30-minute session timeout, so
they add bounces but tell you nothing about pages. They are not bots: GA4 already
drops known bots. Their session count is in `not_set.current` and
`not_set.previous`. Pass `--include-not-set` only when raw GA4 totals are needed,
for example to match figures in the GA4 interface.

### 5. Analyse the data

Read the JSON and calculate:

**Period-over-period changes** — for each metric in `current` vs `previous`:
```
pct_change = (current - previous) / previous * 100
```
Format as `+X.X%` or `-X.X%` with trend arrow (↑ / ↓ / →).

**Channel shares** — sessions per channel as % of total sessions.

**Device split** — mobile/desktop/tablet as % of sessions.

**Engagement summary:**
- Engagement rate (GA4) = engaged sessions / total sessions
- Average session duration in minutes:seconds
- Bounce rate

### 6. Generate action points

Based on the data, generate 5-8 prioritised action points. Use these rules as a starting point — apply judgment:

| Signal | Action |
|--------|--------|
| Bounce rate > 65% on top pages | Audit landing page relevance and CTA clarity |
| Mobile sessions > 60% but engagement rate < 50% | Mobile UX audit — check tap targets, layout, speed |
| Organic search < 25% of sessions | SEO opportunity — content gap analysis |
| New users > 90% of total users | Retention play — email capture, return pathways |
| Sessions declining > 15% period-over-period | Investigate cause: technical, content, or acquisition |
| Single page dominates (> 40% of sessions) | Homepage dependency — diversify entry points |
| Direct traffic > 40% | Strong brand recognition — leverage with referral/affiliate |
| Average session < 1 minute | Content not landing — review messaging, readability |
| No key events configured | Set up conversion tracking — form submits, CTA clicks |
| Top landing page has high bounce | A/B test hero message and CTA above fold |

Label each: **[HIGH]**, **[MEDIUM]**, or **[LOW]** based on impact.

### 7. Write the report

Client reports are stored with the client, **never in the studio**. Do not
write to `$STUDIO_CONTENT_DIR/reports/`.

Determine the output path from the project file's `client_docs:` field:
```bash
CLIENT_DOCS="{client_docs from the project file}"
REPORT_DIR="$CLIENT_DOCS/analytics"
mkdir -p "$REPORT_DIR"
REPORT_PATH="$REPORT_DIR/ga-benchmark-$(date +%Y-%m-%d).md"
```

If `client_docs:` is missing, do not guess it from `client:`: the Dropbox folder
names don't reliably match (NORE's client is "Suze", but its folder is `NORE/`).
Look in `/media/data/Dropbox/Work/Projects/Client/` for the client's folder and
read its `CLAUDE.md`, which says where docs belong. The standard layout from
`/onboard-client` is `{Client}/Docs/`, but some clients keep docs deeper (KF uses
`Khyentse Foundation/New KF Website/Docs/`). Confirm the folder with Mark, then add
`client_docs:` to the project file so the next run doesn't need to ask.

Draw the charts into a folder next to the report:
```bash
CHARTS="ga-benchmark-$(date +%Y-%m-%d)-charts"
python3 /media/data/dev/bain-studio/studio/collectors/ga4_charts.py {SCRATCH}/ga.json "$REPORT_DIR/$CHARTS"
```
This writes `trend.png` (daily sessions, 7-day average, this period against the
previous one), `channels.png` and `countries.png`, sized to brand-doc's text width
on its white body page. Embed them with paths relative to the report, as in the
template below. Look at the trend chart before writing: a peak or dip usually has a
cause worth one caption line (a campaign, a story launch, an outage). Find it with a
landing-page query for those dates rather than guessing. Keep the tables: they are
the accessible version of each chart.

Write a markdown report with this structure:

```markdown
---
title: Analytics Benchmark — {Client Name}
subtitle: {Start Date} – {End Date} ({N} days)
date: {today}
project: {PREFIX}
---

## Executive Summary

{3-5 bullet points summarising the headline findings. Be specific — include numbers.
Example: "Organic search drives 41% of sessions, up 12% on the previous period, indicating
strong SEO performance. However, mobile users show a 58% bounce rate against a 34% desktop
rate — a gap that warrants investigation."}

## Key Metrics

| Metric | {Period} | {Prev Period} | Change |
|--------|----------|---------------|--------|
| Sessions | {n} | {n} | {±%} ↑↓ |
| Users | {n} | {n} | {±%} |
| New Users | {n} | {n} | {±%} |
| Pageviews | {n} | {n} | {±%} |
| Engagement Rate | {x}% | {x}% | {±pp} |
| Avg. Session Duration | {m:ss} | {m:ss} | {±%} |
| Bounce Rate | {x}% | {x}% | {±pp} |

![Daily sessions, this period vs previous]({CHARTS}/trend.png)

{One caption line: what the trend shows, naming the cause of any peak or dip.}

{Note under the table: "Excludes {n} sessions with no recorded landing page
({n} in the previous period). These are visitors returning to idle tabs, not
bots." Omit if `excludes_not_set_landing` is false.}

## Traffic by Channel

![Sessions by channel]({CHARTS}/channels.png)

| Channel | Sessions | Share | Users | Engagement |
|---------|----------|-------|-------|------------|
{rows sorted by sessions descending}

## Top 10 Pages

| Page | Sessions | Views | Avg. Duration | Engagement |
|------|----------|-------|---------------|------------|
{rows}

## Audience

### Devices

| Device | Sessions | Share | Engagement |
|--------|----------|-------|------------|
{rows}

### Top Countries

![Sessions by country]({CHARTS}/countries.png)

| Country | Sessions | Users |
|---------|----------|-------|
{top 5-8 rows}

{if events}
## Key Events

| Event | Count | Users |
|-------|-------|-------|
{rows}
{end if}

## Action Points

{For each action point:}
**{N}. {SHORT TITLE}** `[PRIORITY]`

{One or two sentences explaining what the data shows and what to do about it. Be specific.}

---
{Repeat for each action point}
```

### 8. Brand the report

```
/brand-doc {REPORT_PATH}
```

### 9. Confirm

Report:
```
GA report written: {REPORT_PATH}
PDF: {PDF_PATH}
Period: {start} – {end} ({N} days)
Sessions: {n} ({change})
```

---

## Notes

- The service account email must be added to the GA4 property **before** running. Google shows an error 403 if not.
- Reports are written to `{client_docs}/analytics/` in the client's Dropbox folder, never to the studio's `$STUDIO_CONTENT_DIR/reports/`.
- The `--days 90` default is a good benchmark period. Use `--days 30` for monthly reports.
- If the property has no data (new site), the report will note it and suggest baseline setup actions instead.
