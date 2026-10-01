---
tags:
- studio-project
prefix: MWE
name: Middle Way Education
status: active
client: Middle Way Education
type: client
repo: git@bitbucket.org:markbaindesign/middlewayeducation.git
sector: Education · Buddhist-informed curriculum
stack: WordPress · Custom Theme (middle-way-theme) · custom plugins (mwe-search, mwe-curriculum, mwe-glossary, mwe-member) · bd-search (shared Algolia plugin) · Algolia · VVV · WP Engine
path: /media/data/dev/vvv/clients/www/middlewayeducation
asana: "yes"
qa: "no"
inbox: "no"
open_tasks: 0
current_focus: "Coding Algolia replica-index config into bd-search/mwe-search instead of one-off dashboard/API changes"
next_action: "Verify whether the wp_resources_date replica is actually ordering results by date on production"
---

# Middle Way Education (MWE)

Client project. Custom WordPress theme (`middle-way-theme`) plus several custom plugins (`mwe-search`, `mwe-curriculum`, `mwe-glossary`, `mwe-member`), all built on a shared, going-public search plugin (`bd-search`, developed in the separate `algolia-search` repo and symlinked in). Search is powered by Algolia, one separate application per environment (local, development, staging, production). Local dev via VVV at `https://middlewayeducation.test/`. Hosted on WP Engine (production install `middlewayedu`, staging install `mwestaging`).

## Key contacts

- **Middle Way Education** — client

## Related repos

- `bd-search` (shared Algolia search plugin, being split to a public GitHub repo): `/media/data/dev/vvv/clients/www/algolia-search` — symlinked into this project's `wp-content/plugins/bd-search`

## Notes

- Local dev: VVV at `middlewayeducation.test`
- Hosted on WP Engine, not Cloudways
- No Asana project yet — not wired into Studio Looper
- Per-environment config (`wp-config.php`) uses a single `$environments` lookup array rather than duplicated if/elseif blocks; secrets (Algolia keys, DB creds) stay hardcoded per environment's own gitignored file rather than in any git-tracked or cross-environment-synced file, since WP Engine's prod→staging Copy Environment only search-replaces its own known defaults, not custom code
- WPBakery on production is unlicensed (per Technical Audit doc) - do not repeat the "bundled with CleverCourse" claim from the issued BEA proposal
