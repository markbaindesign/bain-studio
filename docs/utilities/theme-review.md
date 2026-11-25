---
tags: [tool, wordpress, theme-review, qa]
god: themis
invoke: studio/theme-review/theme-sweep.py
description: Tooling for wordpress.org theme reviews - the mechanical sweep, the CDP rendering and keyboard check, and the house review template - run against a DDEV review install
---

# Theme review tooling

Tools for reviewing themes submitted to the wordpress.org theme directory, in
`studio/theme-review/`. They produce **candidates, never findings**: every row is
something a reviewer opens and judges.

| File | What it does |
|---|---|
| `theme-sweep.py` | Fetches and installs a submitted zip, restores the content baseline, crawls with `WP_DEBUG` on, runs Theme Check, checks the header, tags, prefixes, text domain, remote hosts, minified sources, screenshot and custom logo. Writes `<slug>-<version>-sweep.md`. |
| `cdp/cdp_check.py` | Headless Chromium at 390 and 1440: overflow, a whole-page keyboard pass and the open-menu keyboard pass on every page, optionally again with a long site title. `--json` for the review gate. |
| `review-gate.py` | Checks a review's notes, zip, evidence and comment against the full-review definition, ends FULL or PARTIAL and ready to post or not, and fills the handover page. See [[theme-review-gate]]. |
| `review-template.md` | The house format: full and partial review defined, order of checks, Trac status, the notes and comment skeletons, the handover page as the last step. |
| `README.md` | Detail on each check and the licence notes. |

## Where it runs from

The review install reads these files from the **ops worktree**,
`/home/bain/ops/bain-studio/studio/theme-review/` (ADR 014), not from the dev
checkout, so a branch switch here never changes the template a review is reading.
A change reaches reviews when it is released and deployed with
`studio/scripts/ops-deploy.sh`. The review project's own `CLAUDE.md` names its
symlink and commands.

## Usage

From the review install's root:

```bash
THEME_REVIEW_REPORTS=<reviews folder>/<theme> \
  python3 -I /home/bain/ops/bain-studio/studio/theme-review/theme-sweep.py run <slug> <version>

python3 -I /home/bain/ops/bain-studio/studio/theme-review/cdp/cdp_check.py \
  https://<site> <slug> / /sample-page/ --long-title \
  --json <reviews folder>/<theme>/evidence/<slug>-<version>-cdp.json
```

`theme-sweep.py reset` puts the content baseline back after a theme has changed it.

## Tests

```bash
python3 -m pytest studio/tests/test_theme_sweep.py studio/tests/test_theme_review_cdp.py
```

They cover the file-reading half of the sweep and the summaries in `cdp_check.py`.
The DDEV and Chromium halves are checked by running the tools on a real zip in the
review install.

## Keep it public-safe

This repo is public. No theme author, ticket number, review outcome or machine path
beyond the studio's own goes in these files: the template's lessons are written
about "a theme", and the review notes themselves live in Dropbox.
