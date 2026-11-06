# ADR 024 — After a host cutover, sweep the database for every hostname the site was ever reachable on

Date: 2026-10-15
Status: Accepted (2026-10-15)
Related: [dev-ops](../utilities/dev-ops.md), [ADR 023](023-contact-form-bot-protection-via-cloudflare-turnstile.md),
the EBIZG `Dev Ops/` note in that client's Dropbox folder

> **Redacted 2026-11-06.** Client names, domains, provider hostnames and application
> IDs were removed from this ADR; project prefixes are kept. The decisions and the
> reasoning are unchanged. What was removed is in
> `$STUDIO_CONTENT_DIR/internal/studio-infrastructure-identifiers.md` or in that
> project's `Dev Ops/` note in Dropbox. See ADR 021, BSTD-875.

## Context

EBIZG changed host on 2026-10-07. The cutover replaced the install's provider staging
hostname with the production domain,
and a later search for that hostname found nothing.

On 2026-10-15 the live main menu, Elementor content, footer widgets, theme settings and images
were found to still point at a **second** WP Engine hostname for the same install: the older
the provider's CNAME host. There were 1,152 occurrences, over both `http://` and
`https://` and in JSON-escaped form (`https:\/\/...`) inside Elementor data. Visitors
clicking those links left the live domain for the WP Engine hostname. The hostname also wasn't
on the new Turnstile widget's domain list, so the contact form broke there ("Unable to connect
to website").

The miss happened because the cutover searched for the one hostname we knew about, not for
every hostname the site had been reachable on. Hosts often give an install more than one
default name (WP Engine has `<install>.wpengine.com` and `<install>.wpenginepowered.com`).
Content built while the site was being set up can use whichever one the editor happened to be
on.

## Decision

1. **Before a cutover, list every hostname the site has been reachable on.** That includes:
   - the old live domain(s);
   - the host's default names (for WP Engine both `<install>.wpengine.com` and
     `<install>.wpenginepowered.com`; for Cloudways the `*.cloudwaysapps.com` app URL);
   - staging and temporary domains;
   - local domains (`.ddev.site`, `.test`) if the database ever came from local.

   Get the list from the host's dashboard, **and** from `wp db search` for the host's domain
   patterns. Don't rely on memory.
2. **Back up the database first** (`wp db export` to a non-public path, e.g. WP Engine's
   `_wpeprivate/`).
3. **Replace each hostname in this order**, using WP-CLI with `--all-tables-with-prefix
   --precise --skip-columns=guid`:
   1. `https://<old>` -> `https://<live>`
   2. `http://<old>` -> `https://<live>`
   3. `https:\/\/<old>` -> `https:\/\/<live>` (JSON-escaped, e.g. Elementor data)
   4. `http:\/\/<old>` -> `https:\/\/<live>`
   5. bare `<old>` -> `<live>`, to catch what's left (CDN-proxied URLs like `i0.wp.com/<old>/...`,
      email addresses)

   Do a dry run of every pass first. Over SSH gateways that strip quoting (WP Engine), send the
   passes as a PHP script on stdin (`wp eval-file -` with `WP_CLI::run_command`), not as
   command arguments.
4. **Look at the options before running a pass.** Run the pass, but save and restore any option
   that ties the site to an external account by URL, such as Google Site Kit's Search Console
   property. Then check those integrations by hand.
5. **Never rewrite `guid`.** Guids are permanent post identifiers, not links.
6. **Verify, then flush.** Afterwards, `wp db search <old>` must find matches only in `guid`. Flush
   the object cache, page cache and builder CSS (`wp elementor flush-css`). Then fetch key pages
   with a full browser user agent and confirm the old hostnames are gone. Allow for the CDN edge
   copy (`max-age`) to expire before calling it done.
7. **Add the sweep to the cutover checklist**, and run it again once a week or so after cutover in
   case content edited on an old hostname comes back.

## Consequences

- Cutovers take a little longer. In return, links that quietly send visitors to another domain
  don't stay unnoticed until someone stumbles on them.
- Hostnames that stay reachable after cutover (host default names can't always be retired)
  still need to be allowed wherever the site checks its own domain, such as Turnstile widgets
  (ADR 023), CORS rules and API key referrer restrictions.
- `dev-ops.md`'s single-pass `wp search-replace` example is fine for a local pull. It is not
  enough for a production cutover, which follows this ADR instead.
