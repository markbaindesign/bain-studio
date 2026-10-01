# ADR 019 — Code-driven WordPress projects use a separate staging app and scripted sync, not Cloudways linked staging

Date: 2026-09-16
Status: Proposed
Amends: [ADR 006](006-cloudways-client-hosting.md) (its "Staging workflow" section)

## Context

ADR 006 made Cloudways linked staging (Application → Staging Management → Create Staging,
with dashboard Push/Pull) the standard dev workflow. In practice the first project built under
that policy, Beato Properties (BEA), never used it: staging (`vcywemwpuh`) and production
(`qwpadhybuj`) are two independent apps on the same server, kept in step by project scripts
(`deploy-code.sh`, `import-local-to-cloudways.sh`, `pull-from-prd.sh`, `pull-tokens.sh`).

The original reason was not written down. When a production → staging sync was needed on
2026-09-16 there was no script for it and no dashboard Pull to fall back on, which surfaced
the gap between ADR 006 and practice. This ADR reconstructs the reasoning from how Cloudways
staging behaves and how BEA is built. Point 5 below is inference, not a recorded fact.

## Research findings

**Folder and access are not a differentiator.** A Cloudways linked staging site is its own
application with its own folder (`/home/master/applications/<id>/public_html`), database and
Application SFTP/SSH credentials; master credentials reach it too. SSH, rsync, SFTP and WP-CLI
work identically on a linked staging app and a standalone one.
Sources: [Cloudways Staging 2.0](https://www.cloudways.com/blog/cloudways-staging-2-0/),
[Cloudways SFTP/SSH credentials](https://www.cloudways.com/blog/manage-sftp-and-ssh-credentials/).

**Where linked staging does not fit a code workflow:**

1. **Incremental push does not delete.** It is rsync-based with no `--delete`; files removed on
   staging stay on live. An open Cloudways feature request asks for a delete option. Every BEA
   CSS build emits new hashed `*.min.HASH.css` files, so stale files would accumulate on live.
   *Single source (Cloudways feedback forum, via search summary) - not independently confirmed.*
2. **Overwrite push is all-or-nothing on files**, including uploads and `.htaccess`. Pushing just
   the theme and custom plugin cleanly means maintaining exclude paths by hand in the dashboard.
   Sources: [Elegant Themes](https://www.elegantthemes.com/blog/divi-resources/how-to-use-the-staging-and-cloning-tools-on-cloudways-divi-hosting),
   [Cloudways enhanced staging](https://www.cloudways.com/blog/announcing-enhanced-staging/).
3. **Push/Pull is a dashboard whole-site copy, not git-aware.** The studio workflow is local →
   commit → scripted rsync of only the custom code → `chown` (BEA ADR 008).
4. **DB push overwrites environment-specific state.** BEA staging holds its own FluentSMTP Gmail
   config and Google OAuth tokens (BEA ADRs 005, 006), which the scripts save/restore. Selected
   tables is possible but chosen manually each time.
5. **Creation order (inference).** A linked staging site must be created from an existing live
   app. BEA's staging app existed from April 2026 as the pre-launch build site, before a
   production app did, so the two could not have been linked.

Also relevant: Pull copies the full media library (BEA staging reached 9.5 GB and had to be
archived, BEA ADR 009), and only one staging site per app is allowed
([Magnifyi review](https://magnifyi.io/cloudways-staging-feature-review-is-it-easy-to-use/)).

**Compared with WP Engine:** separate installs per environment (prod/staging/dev, max one each),
git push per environment, full copy with selected tables, automatic search-replace and
before/after backups ([WP Engine copy](https://wpengine.com/support/copy-site/),
[environments](https://wpengine.com/support/environments/), [git](https://wpengine.com/support/git/)).
Its tooling is stronger for this workflow, but ADR 006's cost and scriptability reasoning still
holds, and the scripted approach closes most of the gap.

## Decision

- **Projects with custom theme/plugin code under git** use a standalone staging app on the same
  Cloudways server, synced by project scripts: code via git + rsync, DB via WP-CLI export/import
  with search-replace and save/restore of environment-specific options.
- Every such project needs scripts for **both directions**: local → staging, and production →
  staging (and production → local). The prod → staging script must neutralise anything that
  acts on real people from staging (outgoing email, booking/cron notifications, calendar
  tokens) and keep staging password-protected and noindexed.
- **Content-only sites** (no custom code in git) may still use Cloudways linked staging and the
  Pull-first convention from ADR 006.

## Consequences

- ADR 006's "Staging workflow" section applies only to content-only sites; add a pointer to
  this ADR there.
- `docs/utilities/cloudways-provisioning.md` step 6 ("Set up staging") needs a branch: Clone App
  (standalone) for code projects, Create Staging for content-only sites.
- More per-project script maintenance, offset by reuse across projects - candidate for a shared
  script in the WordPress factory repos.
- BEA needs a `sync-prd-to-staging.sh`; staging is currently archived (ADR 009) so the first run
  is a full restore.
- If a future project confirms or disproves point 1 (incremental push not deleting), update this
  ADR.
