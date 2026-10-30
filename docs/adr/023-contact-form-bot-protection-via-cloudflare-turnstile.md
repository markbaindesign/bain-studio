# ADR 023 — Contact-form bot protection via Cloudflare Turnstile, widgets in the studio's Cloudflare account

Date: 2026-10-15
Status: Accepted (2026-10-15)
Related: Techstyle `Dev Ops/devops-notes.md` ("Contact form spam protection: Cloudflare Turnstile - 2026-10-15"),
Ebiz Global `Dev Ops/devops.md` sections 16 and 17

## Context

On 2026-10-15 a phishing "formal enquiry" came through the Techstyle contact form. It had a fake
aerospace-company sender and a Proton Drive PDF whose "View shared document" button led to a
credential-harvesting page. Client contact forms are an open route for this kind of mail, and
the notifications land in client inboxes looking as if they came from the client's own site.

Client sites use different form plugins. Techstyle uses Contact Form 7 and Ebiz Global uses
Forminator. Both have Cloudflare Turnstile support built in, so no extra plugin is needed.
Turnstile is free, has no image puzzles for most visitors, and is set up through an API.

## Decision

1. **Client contact forms get a Cloudflare Turnstile widget**, in managed mode, through the form
   plugin's own Turnstile support. Don't add a separate CAPTCHA plugin.
2. **Widgets live in the studio's Cloudflare account** (Mark's), one per site, named
   "<Client> - contact form". They're created through the API with an account-owned token that
   has Turnstile Edit permission only (`~/.config/cloudflare/turnstile.env`).
3. **Each widget's domain list covers every hostname the form renders on.** That means the live
   domain, the local ddev domain, every staging and host-default hostname (for example
   `<install>.wpenginepowered.com` and the older `<install>.wpengine.com`), and any hostname
   still linked from the site. A `www` that redirects to the apex doesn't need adding.
4. **Keys stay off the command line.** Write the sitekey and secret straight from the API
   response to `~/.config/cloudflare/<client>-turnstile.env` (chmod 600). Pass them to WP-CLI
   on stdin, never as arguments. Print only the sitekey.
5. **Roll out local, then staging, then production**, backing up the form definition before each
   change. On each environment, verify:
   - the public page HTML (fetched with a full browser user agent, after flushing caches,
     including the CDN edge copy) carries the sitekey;
   - a POST without a token is rejected;
   - a real browser submission passes. On production, mark the test clearly, because the
     notification reaches the client.

## Consequences

- Automated (bot) submissions are blocked. Hand-typed phishing like the 2026-10-15 enquiry is
  **not**: Turnstile only proves a human-driven browser. Client education and inbox filtering
  still matter.
- If the studio stops working with a client, its widget stays in the studio's Cloudflare
  account. Hand-over means either transferring it or having the client create their own widget
  and swap the keys.
- A hostname missing from the widget breaks the form for anyone who reaches it ("Unable to
  connect to website"). On Ebiz Global, old links to `ebizglobalweb.wpengine.com` caused exactly
  this. Before a cutover or migration, also search the database for every old hostname.
- A leaked secret is rotated with the API (`.../challenges/widgets/<sitekey>/rotate_secret`,
  `invalidate_immediately: true`) and updated on every environment.
- A CDN-cached page served without the widget makes every real submission fail, because the
  server still demands a token. Flushing caches and checking the public HTML is part of the
  rollout, not an optional extra.
