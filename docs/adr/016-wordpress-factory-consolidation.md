# ADR 016 — Four WordPress factory repos consolidate into one

Date: 2026-09-11
Status: Accepted

## Context

Four repositories in the dev root claimed overlapping territory around building WordPress
themes, and two of them were not repositories at all:

| Directory | State on 2026-09-11 | Contents |
|---|---|---|
| `bain-theme-factory` | git, single commit, created that morning | Slipstream (a complete block theme), `css-foundation-spec.md` |
| `wp-theme-factory` | git, 3 commits, stalled on an unmerged branch since 2026-07-22 | `pipeline/` - an inspiration scraper |
| `wp-repo-factory` | **not a git repo**, untouched since 2026-06-04 | `spec.md` only |
| `wp-scaffold` | **not a git repo** | `PLAN.md` only |

The split did not follow any dimension of the actual work. Interrogating it surfaced two
axes that do: **audience** (client site vs product for distribution) and **theme type**
(classic PHP vs block). That is a 2x2, and no repo mapped onto a cell of it. The four
existed because each was created in response to a different moment.

Two further findings shaped the decision:

- **wp-theme-factory is not a theme factory.** Its six open Asana tasks - MVP theme, repo
  pipeline and skillset, demo site pipeline, naming convention, stock images, an a11y
  reference - are about choosing, naming, packaging and promoting a product line. None is
  about building a theme. Its `repo pipeline & skillset` task restates `wp-repo-factory`'s
  entire spec in one line.
- **wp-scaffold is the only item with a recorded cost.** Its PLAN notes that `ebiz-global`
  and `techstyle` were both built with WordPress at the repo root instead of `public_html/`,
  because `/onboard-client` does the structure by hand. That is damage already incurred and
  certain to recur.

## Decision

Four repos become two.

### 1. One scaffolder - the existing `scaffold-dir`, extended with `--type`

Everything generated above `wp-content/` - the DDEV config, `.gitignore`, `wp-cli.yml`,
`scripts/`, `import/`, `export/`, `backups/`, `docs/`, `qa/` - is project-type agnostic.
Only the theme inside varies. Splitting into a script per type would duplicate the shared
80%, including the `docroot: public_html` line already got wrong twice.

**That shared skeleton is already built.** `/scaffold-dir`'s `scaffold.py` (BSTD-790,
commit eaf86b9, 2026-09-10) creates it and writes the three-tier `.gitignore` and the DDEV
docroot. So the scaffolder is not a new tool: `--type` is added to `scaffold.py`, and
**no `wp-scaffold` repo is created**. Theme templates and fixtures live in
`bain-studio/templates/wp/`, referenced by path.

This also keeps the shape the studio's tooling rule asks for - `scaffold.py` does the work,
the skill is a trigger for a long argument list - and keeps project creation inside the
existing `/commission` → `/scaffold-dir` → `/register-project` chain.

v1 supports three types:

- `classic-client` - client site, classic PHP theme
- `block-client` - client site, block theme
- `block-product` - block theme bound for the wordpress.org theme directory

No `classic-product`. Starting a new classic theme for wordpress.org today is a dead end.

`block-product` differs from the client types by addition (wordpress.org-format `readme.txt`,
GPL headers, translation-ready strings) and by subtraction (no `import/` or `backups/` -
there is no client database; and **no custom post types**).

**The shared skeleton is the union of the three sources**, resolving the disagreement noted
under Consequences. `scaffold.py` today creates `.claude/`, `qa/`, `bin/`, `export/`,
`import/`, `scripts/` and `public_html/`; it must additionally create `context/`, `docs/`,
`backups/`, `wp-cli.yml` (with `path: public_html`) and `README.md`. Directories are created
empty with `.gitkeep` rather than left to appear ad hoc.

### 2. Content seeding is a separate, re-runnable command

`seed.sh`, not a `--content` flag at scaffold time. A design gets reseeded many times during
a build, and the command must also work on projects that already exist - including the two
built wrong.

Two datasets, because their purposes are opposites:

- `--unit-test` imports WordPress's maintained theme unit test data. Deliberately hostile:
  untitled posts, absurd title lengths, deeply nested comments, every image alignment. Its
  job is to find where the CSS fails. Core post types only, so it works on a product theme.
  Near-zero build cost - wire up `wp import`.
- `--demo` inserts plausible portfolio, client and testimonial content for showing a client
  their site mid-build. Requires custom post types, therefore **client projects only**.

Stress data is a gate - imported, acted on, discarded. Demo content is an artifact that
lives with the project. Different lifecycles, so different mechanisms.

### 3. Demo content ships as committed fixtures

`--demo` reads JSON fixtures committed to `wp-scaffold`, authored once with AI assistance.
Seeding is then a deterministic import: no tokens per run, reproducible, hand-editable when
a line reads badly. An optional per-sector AI rewrite can come later if the base mechanism
proves worth extending.

### 4. Custom post types are the hard line between client and product

Confirmed against the WordPress Theme Review team's published requirements: themes submitted
to wordpress.org must not include custom post types, and must exclude "functionality that is
not related to design and presentation."

So portfolio, clients and testimonials are client-side only. For a client project, seeding
them and registering them in the `{slug}-custom` plugin is the same job - `seed.sh` must
wire `cpt-example.php` into a real `register_post_type`, not merely insert posts.

*Source note: this rests on the Theme Review team's own requirements page, the authoritative
primary source for the rule. It has not been independently corroborated, because any second
source would be citing this one.*

### 5. wp-repo-factory merges into wp-theme-factory, which is renamed

`wp-repo-factory`'s `spec.md` moves into `wp-theme-factory`, and that repo is renamed to
reflect what it is: the **product line** - themes and plugins bound for wordpress.org,
covering idea generation, demo sites, naming, the SVN pipeline and the `Tested up to`
maintenance cron.

The merge runs in this direction because `wp-theme-factory` has the git history, the Asana
project (WTF) and six live tasks, while `wp-repo-factory` has a single markdown file, no git
and no Asana. Merging into the one with infrastructure is far cheaper than the reverse.

### 6. bain-theme-factory is dissolved; Slipstream is a product

The decisions above hollowed it out. Scaffolding belongs to `scaffold-dir`; the
`wp-block-theme` skill written the same day lives in `bain-skills`. What remained was
Slipstream and a superseded spec.

- **Slipstream is a product**, and moves to the renamed product repo to be finished and
  submitted. An earlier draft of this ADR called it a reference implementation and "explicitly
  not a candidate product", on the reasoning that a wordpress.org theme needs neutrality.
  That reasoning was wrong - opinionated themes ship there routinely - and Mark's call is that
  it is a product. Its README already lists what stands between it and submission: the
  upstream `OFL.txt` for both font families is not yet shipped (OFL 1.1 requires the notice to
  travel with the files), pattern copy is placeholder with real facts needed wherever there
  are `[square brackets]`, `patterns/plate.php` draws stand-ins where photographs go, and
  there is no `style.min.css`.
- **The block template is forked from Slipstream once**, now, and the two then diverge. The
  fork keeps the bones - `theme.json` structure, the layer contract and `foundation.css`, the
  `functions.php` enqueues, the nine templates and two parts - and drops the signature moves
  (the slip wordmark, the bracket marks, the ink block styles) along with the
  `remove_theme_support( 'core-block-patterns' )` call, which is a bespoke choice rather than
  a studio default. It lands in `bain-studio/templates/wp/block/`. After the cut, changes to
  Slipstream do not propagate to the template and vice versa.
- **`css-foundation-spec.md`** becomes a decision record in `bain-studio/docs/`. It is
  not merely stale - Slipstream **contradicted** it. The spec proposes a named-line grid
  (`.l-page`) for containment; Slipstream deliberately ships no such thing, because
  `useRootPaddingAwareAlignments` already puts the gutter on the root and lets `alignfull`
  break out. Left marked "draft, not started" it reads as pending work, which is misleading.
  Its one genuinely open thread is the **non-WordPress** case the spec wanted to serve;
  Slipstream answers only the WordPress half, by handing containment to WordPress.

## Resolved — `scaffold-dir` already existed

Found immediately after the decisions above were first taken, and it reshaped decisions 1
and 6.

`bain-studio` was sitting on `feature/bstd-790-scaffold-wp-gitignore`, one commit (eaf86b9,
2026-09-10), which taught `/scaffold-dir` WordPress-aware scaffolding: a 273-line
`scaffold.py` creating `.claude/`, `qa/`, `bin/`, `export/`, `import/`, `scripts/` and
`public_html/`, writing the three-tier `.gitignore` and setting DDEV's docroot to
`public_html`, with `--wordpress`, `--ddev`, `--plugin`, `--theme` and `--mu-plugin`.
BSTD-790 is at Looper Status **Review**, not merged. It writes no theme or plugin files.

Building a separate `new-project.sh` would therefore have been a second scaffolder
duplicating a first that was awaiting review - precisely the duplication this ADR exists to
end. Resolved by extending `scaffold-dir` rather than replacing it, and by not creating the
`wp-scaffold` repo at all. Decisions 1 and 6 above are written as resolved.

## Consequences

- Four repos become one: the renamed product repo. Building moves into `bain-studio`
  (`scaffold-dir` plus `templates/wp/`), and the block theme knowledge is already in
  `bain-skills`. `bain-theme-factory`, `wp-repo-factory` and `wp-scaffold` all disappear -
  the last was never created.
- The product repo must become a real git repo. It is one today (`wp-theme-factory`), but
  needs the rename and the merge.
- BSTD-790 must be reviewed and merged before `--type` is added on top of it.
- `/onboard-client` step 4 should call `/scaffold-dir` instead of building structure by hand.
- **`docs/utilities/wp-project-layout.md` is authoritative for the shared skeleton, not
  `wp-scaffold/PLAN.md`.** The layout doc was written 2026-09-09, after the same two projects
  drifted, and the two disagree: the layout doc carries `bin/`, `context/`, `.claude/` and
  `CLAUDE.md`, which the PLAN omits; the PLAN carries `backups/`, `wp-cli.yml` and `README.md`,
  which the layout doc omits. Reconcile them before writing `new-project.sh` - building from
  the PLAN alone would reproduce the drift the layout doc exists to prevent. Where they
  conflict, the layout doc wins.
- `docs/utilities/wp-project-layout.md` will need updating once the scaffolder exists, to
  point at it as the way the layout is produced.
- `ebiz-global` and `techstyle` remain mis-structured. Restructuring them onto `public_html/`
  is separate work - it touches `.ddev/config.yaml`, `wp-config.php` paths and git history.
- BTF's Asana project is emptied. Its seven tasks were closed on 2026-09-11: BTF-004 as
  genuinely complete (the `wp-block-theme` skill), the other six migrated to BSTD-796 through
  BSTD-801, each original carrying a comment pointing at its new id. BTF-002 was already
  deleted in Asana; the mirror was stale.
- Those six are knowledge tasks feeding the skill, not scaffolding tasks, so they live in
  BSTD rather than following the repo into `wp-scaffold`.
- `Dropbox/Work/Projects/internal/project-scaffold/wp-project-scaffold.md` is a VVV-era
  checklist superseded by `wp-scaffold/PLAN.md` and this ADR. It should be archived.
- Nothing has been moved or deleted on disk as of this ADR. The repo changes are pending.

## Sequencing

1. Review and merge BSTD-790 (`feature/bstd-790-scaffold-wp-gitignore`).
2. Extend `scaffold.py` to create the union skeleton - add `context/`, `docs/`, `backups/`,
   `wp-cli.yml`, `README.md`.
3. Fork the neutral block template out of Slipstream into `bain-studio/templates/wp/block/`.
4. Add `--type classic-client|block-client|block-product` to `scaffold.py`.
5. Add seeding, `--unit-test` first - it is nearly free.
6. Merge `wp-repo-factory` into `wp-theme-factory`, rename it, move Slipstream in.
7. Delete `bain-theme-factory`; retire `css-foundation-spec.md` into a decision record,
   keeping the non-WordPress question open.
8. Repoint `/onboard-client` step 4 at `/scaffold-dir`.
