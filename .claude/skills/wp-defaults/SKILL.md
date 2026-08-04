---
name: wp-defaults
description: Apply Bain Design's standard defaults to a fresh WordPress install — debug wp-config constants, and removal of default bundled content/plugins (Hello Dolly, Akismet, Jetpack, sample post/page/comment). Run inside a DDEV WordPress project directory right after `wp core install`. Fresh installs only — an existing site pulled into DDEV keeps its own wp-config and content untouched.
argument-hint: [path]
allowed-tools: [Bash]
---

# WP Defaults

Routine cleanup Mark does on every fresh WordPress install, automated so it
happens the same way every time.

**Fresh installs only.** If the project is an existing site pulled into
DDEV, do not run this — it would stomp on the client's own `wp-config.php`
and could delete real content that happens to share a title with WordPress's
default sample content.

Arguments: $ARGUMENTS — optional path to the DDEV project directory. If
omitted, use the current directory.

---

## Step 0 — Confirm context

Verify this looks like a DDEV WordPress project with WordPress already
installed:

```bash
ddev wp core is-installed
```

If this fails (DDEV not running, or WP not installed yet), stop and report —
don't guess at what state the project is in. This skill runs *after*
`wp core install`, not instead of it.

---

## Step 1 — wp-config debug constants

```bash
ddev wp config set WP_DEBUG true --raw --type=constant
ddev wp config set WP_DEBUG_LOG true --raw --type=constant
ddev wp config set WP_DEBUG_DISPLAY false --raw --type=constant
ddev wp config set SCRIPT_DEBUG true --raw --type=constant
```

---

## Step 2 — Remove default sample content

WordPress's own installer creates a "Hello world!" post, a "Sample Page",
and one comment on that post. Find and delete them by exact title match
(don't assume IDs 1/2 — safer against any variation in install order):

```bash
ddev wp post delete $(ddev wp post list --post_type=post --title="Hello world!" --field=ID --format=csv) --force
ddev wp post delete $(ddev wp post list --post_type=page --title="Sample Page" --field=ID --format=csv) --force
```

Deleting the post cascades to its comments, so there's no separate comment
deletion needed once the post itself is gone. If either title isn't found
(empty ID list), skip that delete silently rather than erroring on an empty
argument.

---

## Step 3 — Remove default bundled plugins

```bash
ddev wp plugin delete hello
ddev wp plugin delete akismet
```

Hello Dolly's plugin slug is `hello` (the folder is `hello.php`, not
`hello-dolly`) — using the wrong slug doesn't error, `wp plugin delete` just
reports "already deleted" and exits 0 while leaving the real plugin in
place, so double check the plugin is actually gone (`wp plugin list` or
`ls wp-content/plugins/`) rather than trusting the delete command's own exit
code.

Jetpack is not bundled by a plain `wp core download` + `wp core install` —
it only shows up on some hosting providers' images. Check before deleting:

```bash
ddev wp plugin is-installed jetpack && ddev wp plugin delete jetpack
```

`is-installed` correctly exits 1 when absent, so the `&&` guard skips the
delete cleanly in the normal fresh-install case.

If any `plugin delete` fails because the plugin isn't present, don't treat
it as an error — report it as "not present, skipped" and continue.

---

## Step 4 — Report

```
wp-defaults: {path}
  ✓ WP_DEBUG=true, WP_DEBUG_LOG=true, WP_DEBUG_DISPLAY=false, SCRIPT_DEBUG=true
  ✓ Removed sample post/page (or: "not found, skipped")
  ✓ Removed hello-dolly, akismet  (note any "not present, skipped")
```

---

## Guard rails

- **Never run this against an existing-site pull.** If unsure which case
  this is, ask rather than assume.
- **Don't delete anything by ID without confirming by title first** — a
  client's real content could coincidentally occupy post ID 1 or 2 on an
  existing site; title-matching against WordPress's exact default strings is
  the safeguard, and only applies at all on a fresh install where those
  titles are known to be the installer's own placeholders.
