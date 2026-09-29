# ADR 020 — Staging is kept out of search engines by code, not by basic auth

Date: 2026-09-17
Status: Proposed
Amends: [ADR 019](019-separate-staging-apps-for-code-projects.md) (its "keep staging
password-protected and noindexed" clause)

## Context

Client staging sites are protected with HTTP Basic Auth. The stated purpose is to keep
staging away from crawlers and avoid duplicate-content penalties against production — not
to protect secrets.

That protection has a real day-to-day cost, which surfaced on KF on 2026-09-16/17:

- **LastPass cannot autofill it.** Basic Auth uses a native browser dialog, not a DOM form.
  Password managers autofill by injecting into the DOM, so they structurally cannot reach it.
  This is not a misconfiguration and no amount of LastPass setup will fix it.
- **The prompt appears three times per page load**, not once.
- Working around it with the ModHeader extension consumed most of two working days and was
  never made reliable across more than one site.
- Agents (Claude Code) get 401s and cannot verify anything over HTTP without a credentials file.

## Research findings

**Why three prompts.** Basic Auth credentials are cached per *origin*, but several
subresources are fetched in separate credential contexts, each triggering its own challenge:

1. The document itself.
2. `/site.webmanifest`. Per the Web App Manifest spec the manifest is fetched with credentials
   mode `omit` **even when same-origin**, unless the link opts in with
   `crossorigin="use-credentials"`. KF already sets that attribute — it stops the manifest
   *failing*, but a prompt still occurs when no credentials are yet cached for the origin.
3. Favicon / apple-touch-icon. Separate fetch contexts, and `crossorigin` cannot be applied
   to them.

Sources: [Chromium discussion](https://groups.google.com/a/chromium.org/g/chromium-discuss/c/ZLXwilWYwZs),
[PWAs behind Basic Auth](https://thatemil.com/blog/2018/02/21/pwa-basic-auth/),
[401 on a webmanifest file](https://medium.com/@aurelien.delogu/401-error-on-a-webmanifest-file-cb9e3678b9f3).

This is not fixable while Basic Auth is on. Only something that supplies credentials to every
request — a browser password manager, or removing the auth — eliminates it.

**What was actually protecting KF staging (measured 2026-09-17):**

| | State |
|---|---|
| Basic Auth | on |
| `robots.txt` | `Disallow: /` (WP Engine platform) |
| `X-Robots-Tag` | absent |
| `<meta name="robots">` noindex | **absent** |
| `blog_public` | **1 — indexing allowed** |
| Canonical | **self-referential to the staging domain** |

So Basic Auth was load-bearing. Remove it and staging would have been indexable, with a
self-canonical — precisely the duplicate-content case it was meant to prevent.

**`blog_public` cannot be relied on as a setting.** A WP Engine "Copy environment"
production → staging — whether triggered from the portal or by `scripts/sync_staging.sh`,
which is a wrapper around the same WP Engine API operation — carries production's
`blog_public = 1` across and silently re-opens staging to indexing. Any fix that lives in a
database option will be undone by the next sync, and nobody will notice.

**`robots.txt` and `noindex` work against each other.** `Disallow: /` prevents crawling, so a
crawler never fetches the page and never sees the `noindex`. Google may still index a URL it
finds linked elsewhere, showing it without a snippet. `noindex` is the mechanism that actually
prevents indexing, and it requires the page to be crawlable.

## Decision

- **Indexing protection lives in code, keyed on environment.** In the project's custom
  functions plugin:

  ```php
  if ( wp_get_environment_type() !== 'production' ) {
      add_filter( 'pre_option_blog_public', '__return_zero' );
  }
  ```

  It deploys with every release, survives every sync, covers staging and dev, and cannot be
  toggled back by accident. Implemented for KF in `95b1fcff` (release 2.12.0).

- **Basic Auth is no longer the mechanism that keeps staging out of search results.** It may
  be kept as defence in depth, but it is now optional rather than load-bearing, and a project
  may drop it to remove the three-prompt friction.

- **Where Basic Auth is kept**, agents and scripts authenticate via `~/.netrc` (one `machine`
  block per host, `chmod 600`). Browser access is the operator's own choice; ModHeader is not
  recommended, having proved unreliable across profiles.

- **Verify per environment that `wp_get_environment_type()` is correct before relying on this.**
  It defaults to `production` when `WP_ENVIRONMENT_TYPE` is undefined, so an unset staging
  environment would silently get no protection. KF verified 2026-09-17: staging reports
  `staging`, production reports `production`.

## Consequences

- ADR 019's "keep staging password-protected and noindexed" is narrowed: noindexed is
  mandatory and now enforced in code; password-protected becomes optional.
- Every code-driven project needs this filter added. It is a candidate for the shared
  WordPress factory boilerplate rather than per-project copies.
- A release that ships this must verify **production is unaffected** — a false positive would
  deindex the live site. KF's 2.12.0 test plan section 8 covers this explicitly.
- If Basic Auth is dropped on a site, the WP Engine platform `robots.txt` `Disallow: /` should
  ideally be relaxed so crawlers can fetch the page and see the `noindex`. That is a platform
  setting, not a repo change.
- Staging still holds drafts and unpublished content that production does not. Dropping Basic
  Auth makes that readable by anyone with the URL. Acceptable for a copy of a public site;
  reconsider for any project handling personal or confidential data.
- `~/.netrc` becomes part of the workstation rebuild record
  (`context/internal/workstation-rebuild.md`).
