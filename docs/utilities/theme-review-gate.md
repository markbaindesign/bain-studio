---
tags: [tool, wordpress, theme-review, qa]
god: themis
invoke: studio/theme-review/review-gate.py
description: Review gate for a wordpress.org theme review - checks the notes, zip, evidence and comment against the full-review definition, prints PASS/FAIL rows and ends FULL or PARTIAL, and writes the handover page's data from its own results
---

# Theme review gate

`studio/theme-review/review-gate.py` decides what a theme review may be called. It
reads the review's notes, the theme zip, the Trac comment, the evidence folder and the
review project's Asana mirror, prints one row per check like a test run, and ends on
**FULL** or **PARTIAL**, then **ready to post: yes/no**.

Run it after the comment has passed the copywriter and the sign-off and posting task
exists, and before the handover page. See [[theme-review]] for the rest of the tooling.

## Usage

From the review install's root:

```bash
python3 -I /home/bain/ops/bain-studio/studio/theme-review/review-gate.py \
  <reports>/<slug>-<version>.md --handover <reports>/<slug>-<version>-handover.html
```

| Option | Default |
|---|---|
| `--zip` | `<project>/review-zips/<slug>.<version>.zip` |
| `--comment` | `<reports>/<slug>-<version>-trac-comment.txt` |
| `--evidence` | `<reports>/evidence/` |
| `--mirror` | `<project>/asana-mirror.md` |
| `--project` | the current directory |
| `--handover-json FILE` | write the handover fragment to a file |
| `--handover PAGE` | write the fragment into the page's `handover-data` block |
| `--pre-submission` | the studio's own theme, before submission: no Trac ticket |

The slug and version come from the notes file's name.

## Pre-submission reviews

`--pre-submission` is for a studio theme reviewed before it goes to wordpress.org,
installed with `theme-sweep.py install-zip` or `run-local`. There is no ticket, so the
**sign-off and posting task** row prints `N/A` and counts as passed, the last line reads
**ready to submit** instead of ready to post, and the handover fragment sets `ticket` to
`0`, so the page shows no ticket link or button. Every other row, and the exit status, is
unchanged.

## Two answers, kept apart

**Review type.** FULL only when every check in the five-point definition passes. Any
failing row makes it PARTIAL, and the failing rows are the gaps.

**Ready to post.** Both the notes header and the comment claim the type the gate
found, and the posting task exists. A partial review that says it is partial is
ready to post. A review that calls itself full when it is not, is not.

Exit status: `0` ready to post, `1` not ready, `2` could not run (no notes, no zip).

## What it checks

| Group | Row | Passes when |
|---|---|---|
| files | every zip file has a ledger row | each file in the zip is named by a `## File ledger` row in `File \| Lines \| Verdict` form |
| files | every ledger row has lines and a verdict | no row has empty Lines or Verdict, names a file not in the zip, or has a glob whose `(count)` is wrong |
| functions | every function / hook has a verdict | each `function name(` and each `add_action`/`add_filter` hook in the PHP appears, as a whole word, in a `## Functions and hooks` `Name \| Verdict` row with a verdict |
| requirements | handbook page fetched | the gate fetched the required page itself and found its numbered sections |
| requirements | handbook page cited with its read date | the section names the page URL and a date |
| requirements | every handbook section has a verdict | a `§ \| Verdict` row for every section number on the page as fetched today |
| requirements | guideline rows (accessibility-ready only) | the gate fetched the guideline index, and `## Accessibility guidelines` has a `Guideline \| Verdict` row **keyed by each page's URL slug** |
| tiers | tier 2 | `<slug>-<version>-<check>.json` exists for each of `main-landmark`, `local-fonts`, `msgfmt`, `images`, `block-delimiters`, `print-stylesheet` |
| tiers | tier 3 | `<slug>-<version>-cdp.json` from `cdp_check.py --long-title --json` covers 390 and a desktop width (1280 or more), with a keyboard pass at both, a long-title run and no aborted page; screenshots `<slug>-<version>-<view>-<width>.png` at 390 and desktop; for a block theme, `<slug>-<version>-site-editor.json` |
| notes | every template section present | `## ` headings starting Verdict, Handbook required, Tags, Functions and hooks, File ledger, Other checks, Not done, Outcome (and Accessibility guidelines when tagged) |
| notes | Not done is empty | the section is empty or starts "Nothing" / "None". An optional step not run is said after that word |
| claims | notes header / comment claims … | "full review" or "partial review" before the first `##` of the notes, and in the comment, matches the gate's answer |
| posting | sign-off and posting task | a `### …` heading in the mirror containing `<Theme Name>: sign off the <version> review` |

Everything is matched exactly on keys the template prescribes. A guideline row named
"Skip link" does not count for `skip-to-content`. A page that cannot be fetched is a
FAIL row, never a skipped one.

The tier 2 file names are this gate's contract. The scripts that write them are a
follow-up; until they exist, tier 2 fails on every review, so no review comes out
FULL.

## Ledger cells

A File cell is one path, a comma list, or a glob with its count:

| File | Lines | Verdict |
|---|---|---|
| `style.css` | 1-242 | … |
| `parts/header.html, parts/footer.html` | 1 each | … |
| `assets/images/hero-1.jpg, hero-2.jpg` | binary: viewed | … (`hero-2.jpg` inherits `assets/images/`) |
| `assets/fonts/*.woff2 (8)` | binary: name tables | … |

## The handover page

`--handover` replaces three things in the page's data: `review`, `review_note`, and the
**Full-review definition** group, rebuilt from the gate's rows. It appends a
**Review gate (date)** group with every row and sets the Workflow item "Review gate
run" to pass. Everything else on the page is left alone, and running it twice gives
the same page. Statuses are `pass` and `fail`, plus `na` for a row that does not apply
(the posting row on a pre-submission review), so the page can only show what the gate
checked.

## Tests

`studio/tests/test_review_gate.py`, on a fictional theme with stubbed pages. One test
checks that the notes skeleton in `review-template.md` has every section and table
the gate looks for, so the two cannot drift.
