---
tags: [utility, research, wordpress, open-source, contribution]
god: hephaestus
description: Research report on third-party WordPress plugins actively seeking contributors via GitHub good-first-issue and help-wanted labels.
---

# WordPress Third-Party Plugins — Contributor Research

**Researched:** 2026-06-25
**Task:** BSTD-040
**Related:** docs/utilities/wp-contributor.md (core/Gutenberg research)

---

## TL;DR

WooCommerce is the standout target with 52 open `good-first-issue` items — the largest active backlog of any WordPress plugin on GitHub. Yoast SEO (12) and WP Playground (12) are strong secondary options. Action Scheduler is niche but very approachable (4 issues, focused codebase).

---

## Shortlist

| Plugin | Repo | Good First Issues | Help Wanted | Stack | Notes |
|--------|------|:-----------------:|:-----------:|-------|-------|
| WooCommerce | `woocommerce/woocommerce` | 52 | - | PHP + React | Largest backlog, very active, full CI |
| Yoast SEO | `Yoast/wordpress-seo` | 12 | - | PHP + JS | Some issues are old (2019-era), but recent ones active |
| WP Playground | `WordPress/wordpress-playground` | 12 | - | TypeScript | First-party but plugin-scoped; docs/UI tasks common |
| Action Scheduler | `woocommerce/action-scheduler` | 4 | - | PHP | Small focused lib, used by many plugins |

---

## Per-Plugin Detail

### WooCommerce — `woocommerce/woocommerce`

- **Stars:** ~10,000+
- **Good first issues:** 52 open
- **Sample issues:**
  - #56445 — Admin Order Search using Customer Name does not return all matching orders
  - #45137 — Standardization of quotation marks in all textual content
  - #42113 — HTML tags not allowed when displaying Cart Item Data
  - #31046 — Usage tracking cron event set without action if tracking disabled
- **Contribution notes:**
  - Full CONTRIBUTING.md and PR checklist
  - GitHub Actions CI runs PHPUnit + Jest
  - Issues well-labelled: `good first issue`, `type:bug`, `type:enhancement`
  - React (JS) issues tend to be isolated; PHP issues are core logic
- **API query:**
  ```bash
  gh api "search/issues?q=label:\"good+first+issue\"+repo:woocommerce/woocommerce+state:open&per_page=20"
  ```

### Yoast SEO — `Yoast/wordpress-seo`

- **Stars:** ~2,000+
- **Good first issues:** 12 open
- **Sample issues:**
  - #20864 — Use CPT/taxonomy slug instead of rewrite slug in settings URLs
  - #4333 — Tools > File Editor should give more descriptive error messages
  - #8502 — Error message when widget blog feed can't be loaded
- **Contribution notes:**
  - Some issues are several years old — check `updated` date before picking up
  - PHP + JS (React-based analysis tools)
  - Good documentation on setting up local dev environment
- **API query:**
  ```bash
  gh api "search/issues?q=label:\"good+first+issue\"+repo:Yoast/wordpress-seo+state:open&per_page=20"
  ```

### WordPress Playground — `WordPress/wordpress-playground`

- **Stars:** ~1,300+
- **Good first issues:** 12 open
- **Sample issues:**
  - #3171 — Add link to blueprint editor at Launch Playground Panel
  - #2816 — CLI throws message for invalid WordPress version
  - #2540 — Add instructions for editing documentation with GitHub UI
  - #2042 — Show error message when using invalid plugin/theme slugs
- **Contribution notes:**
  - TypeScript-heavy; not PHP like typical plugins
  - Docs and UI tasks are common — lower barrier to entry
  - First-party WordPress project but ships as a plugin/npm package
- **API query:**
  ```bash
  gh api "search/issues?q=label:\"good+first+issue\"+repo:WordPress/wordpress-playground+state:open&per_page=20"
  ```

### Action Scheduler — `woocommerce/action-scheduler`

- **Stars:** ~700+
- **Good first issues:** 4 open
- **Sample issues:**
  - #980 — 10x time limit in failure log entries
  - #947 — Find a way to disable logs for specific actions/jobs
  - #944 — Remove grunt-phpcs?
- **Contribution notes:**
  - Very focused PHP library — easier to understand the full codebase
  - Used by WooCommerce, Jetpack, and many others as a dependency
  - Smaller community but responsive maintainers

---

## Repos Checked But Not Recommended

| Repo | Reason |
|------|--------|
| `Automattic/jetpack` | Monorepo — vast scope, no `good first issue` labels found, complex local setup |
| `wp-media/wp-rocket` | 1 good-first-issue, commercial plugin, limited contributor programme |
| `reduxframework/redux-framework` | 0 contributor labels found |
| `GoogleChromeLabs/pwa-wp` | Archived / low activity |

---

## Recommended Starting Point

**WooCommerce** — largest active backlog, well-maintained CI, widely deployed (shipping a fix here has real impact), and issues span PHP and React so there's always something at the right skill level.

Secondary: **Yoast SEO** (check issue recency before picking up) or **Action Scheduler** (small scope, high impact).

---

## Next Step

Run `/feature BSTD` to register the WP contributor factory as a feature, or move the `wp-contributor-spec.md` draft forward via `/nurture`.
