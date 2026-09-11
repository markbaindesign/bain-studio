---
tags: [utility, devops, hosting, wordpress, wp-engine]
description: Mothball a WP Engine staging install down to a minimal holding site — strip themes, plugins and uploads from disk, keep the environment (URL, SSH, DB) alive so it can be re-synced on demand.
---

# WP Engine — mothballing a staging install

**Status:** in use. First applied on MWE staging (`mwestaging`), Apr–May 2026.

## Why

On WP Engine, a staging environment's hostname and SSH identity are generated when the
environment is created (`<name>.wpenginepowered.com`, `<name>.ssh.wpengine.net`) and cannot be
chosen. Deleting a staging environment and standing a new one up later means:

- a new, different staging URL, so every bookmark, allowlist, DNS/redirect note and client link
  goes stale
- a new SSH host and user, so local SSH config, deploy remotes and `.claude/settings.local.json`
  permission entries all have to be redone
- repeating the whole environment setup overhead each time

Keeping the environment but leaving a full site running on it has its own costs: plugin and core
update prompts, security surface, and disk footprint against the plan's storage.

Mothballing keeps the environment identity and drops the running site.

## What it is

A **filesystem strip with the database left intact**:

| Path | Action |
|---|---|
| `wp-content/themes/` | Delete contents, leave WP's stock `index.php` stub |
| `wp-content/plugins/` | Delete contents, leave the `index.php` stub |
| `wp-content/uploads/` | Delete media (year folders can stay as empty shells) |
| `wp-content/mu-plugins/` | **Leave alone** — WP Engine's platform mu-plugins (cache, sign-on, security auditor, update-source selector) live here and the platform expects them |
| Database | Leave as-is — posts, users, options, `active_plugins` all retained |

Net effect: nothing to update, no third-party PHP executing, storage footprint collapses to the
database plus mu-plugins, and the URL / SSH / DB / environment all stay exactly where they were.

## Preconditions

- The environment is behind WP Engine's password protection (a stripped install serves a broken
  or default-theme front end — do not leave it publicly reachable).
- Nothing is deploying to this environment automatically (a git push or a scheduled sync will
  refill it).
- Any local-only content on staging has been pulled first. The strip is not reversible from
  staging itself.

## Procedure

```bash
# 1. SSH in (install name, not the account name)
ssh <install>@<install>.ssh.wpengine.net
cd /sites/<install>

# 2. Record what was active, before touching anything
wp option get active_plugins --format=json > ~/active_plugins.before.json
wp theme list --format=csv > ~/themes.before.csv
wp plugin list --format=csv > ~/plugins.before.csv

# 3. Strip
rm -rf wp-content/plugins/*      # keeps the dir; re-add index.php if it went
rm -rf wp-content/themes/*
rm -rf wp-content/uploads/*

# 4. Confirm the stubs are still there
ls -la wp-content/plugins wp-content/themes
```

Leave `wp-content/mu-plugins/`, `object-cache.php` and `advanced-cache.php` in place.

## What goes quiet (and what doesn't)

The point of the strip is noise reduction, so be clear about which noise it actually removes.

Silenced:

- **Security plugin alerts** (Wordfence and friends) — the files are gone, so nothing scans,
  nothing emails, and there is no "site not scanned recently" nag from this install.
- **Plugin update nags** — WordPress builds its update list by enumerating `wp-content/plugins/`
  via `get_plugins()`. Nothing installed means nothing to check and an empty Updates screen.
- **Theme update nags** — same mechanism, same result.

Not silenced:

- **WordPress core** update checks and core auto-update result emails, which do not depend on any
  plugin. On WP Engine core is platform-managed, so this is usually quiet anyway — but that is the
  platform's doing, not the strip's.
- **Anything running outside the install**: Wordfence Central, uptime monitors, WP Engine's own
  security-auditor mu-plugin, or any scanner pointed at the URL.

### Outbound mail is NOT trapped on WP Engine staging — tested

Tested on `mwestaging`, 2026-09-09. WP Engine does **not** sandbox outbound mail on a staging
environment: a `wp_mail()` fired from WP-Cron on the web runtime (`sapi=fpm-fcgi`) returned `true`
and the message was delivered to an external inbox within seconds. WP Engine's own
`sendmail_path` wrapper is configured on the web nodes, and only a `wp_mail_from` filter is in
play, which rewrites the envelope sender to `wordpress@wpenginepowered.com`.

Two things follow:

- **A stripped staging install can still email real people.** Its database is a copy of
  production, so `admin_email` and every user row hold live client addresses. On MWE staging,
  `admin_email` is the client's own address.
- **Removing a mail-suppressing plugin re-arms the nags it was suppressing.** MWE's
  `active_plugins` included `disable-auto-update-email-notifications`; with the plugins directory
  emptied, nothing suppresses core auto-update emails any more.

So before stripping a client environment, either point `admin_email` at your own address, or drop
a permanent mu-plugin that short-circuits mail:

```php
<?php
// wp-content/mu-plugins/zz-block-outbound-mail.php — staging only, never production.
add_filter( 'pre_wp_mail', '__return_false' );
```

A mu-plugin is the right home for it: it survives the strip (mu-plugins are left in place) and
cannot be deactivated from the admin.

**Testing method, for reuse:** do not test this over SSH. WP Engine's SSH gateway is a separate
container from the web nodes, and `wp_mail()` there fails with `Could not instantiate mail
function` because `/usr/sbin/sendmail` does not exist in the gateway — a false negative that looks
like proof mail is dead. Test the real runtime instead: drop a temporary mu-plugin registering a
callback that calls `wp_mail()` and logs the result with `error_log()`, schedule it with
`wp cron event schedule <hook> now`, wait for WP Engine's system cron to fire it, then read
`wp-content/debug.log` and check the destination inbox. Remove the mu-plugin afterwards.

## Restoring

Use WP Engine's **Copy environment** (production → staging) in the portal, which repopulates
files and database together. A `git push` to the environment plus a media sync also works if the
theme and custom plugins are the only things needed and the database is still current.

After restoring an ACF Pro project this way, run the ACF JSON import step — see the ACF Pro
section in `/media/data/dev/CLAUDE.md`.

## Caveats

- **`active_plugins` can be silently rewritten.** WordPress validates active plugins on admin
  load and deactivates any whose files are missing. If anyone opens `wp-admin` on the stripped
  install, the record of what was active may be lost — hence step 2 above. (On MWE staging the
  option survived intact, but do not rely on that.)
- Attachment posts remain in the database after the uploads are deleted, so media counts still
  look populated while the files are gone. That is expected and resolves on the next full copy.
- WP Engine's own overnight backup/copy jobs write into the environment (e.g. a `wp-content/mysql.sql`
  dump). Seeing recent mtimes on `wp-content/` does not mean someone restored the site.
- This is a staging technique. Never apply it to a production install.

## Where it applies

Any WP Engine install being parked rather than retired. The same reasoning applies on Cloudways,
though there the staging hostname is under our control, so the URL-preservation argument is
weaker and deleting the app is often the better call.
