---
tags:
- studio-project
prefix: ASP
name: Algolia Search Plugin
status: active
client: Internal
type: internal
sector: WordPress plugins
stack: WordPress · PHP · Algolia · WP-CLI · DDEV · PHPUnit (Brain Monkey)
path: /media/data/dev/ddev/algolia-search
asana: "yes"
qa: "no"
inbox: "no"
open_tasks: 51
current_focus: Hotfix 2.9.1 (--post_ids, multi-index saves, WPML per-language routing)
next_action: Release bd-search 2.9.1 (ASP-062), then per-language index settings (ASP-056)
repo: git@github.com:markbaindesign/algolia-search.git
---

# Algolia Search Plugin (ASP)

The studio's own Algolia search plugin for WordPress, **bd-search** (display name "BD Algolia Search"), plus the test site that develops it. Indexes WordPress content into Algolia with one index per language (WPML), named indices with routing, code-first index config via per-site child plugins (`new-child-plugin.sh`, `_template/`), and bespoke InstantSearch front ends.

- **Local:** https://algolia-search.ddev.site (DDEV)
- **Algolia app (test):** `BBY7J34O4Z`, kept alive by algolia-pulse
- **Used on:** KF (kf-21, `kf-search` child), Film English (`fe-search`), MWE
- **Plugin path:** `public_html/wp-content/plugins/bd-search/`

## Notes

- Git flow: `master` / `develop`, tags `X.Y.Z` (no `v`). Latest release 2.9.0; hotfix 2.9.1 in progress.
- Unit tests: `vendor/bin/phpunit` in the plugin dir. Host PHP lacks extensions, so run via `ddev exec` or a one-off container from the ddev web image.
- Third-party Algolia plugins are kept as **reference only** in `Dropbox/Work/Resources/Dev/algolia-reference/` (see NOTICE.md). Never copy code from them.
- Docs: `Dropbox/Work/Projects/internal/bd-search/Docs/`. Comparison with the official plugins, product options: `Algolia plugin comparison/2026-10-20-algolia-plugin-comparison.md`.
- Repo was previously also checked out at `vvv/clients/www/algolia-search` (VVV); the DDEV path is current.
