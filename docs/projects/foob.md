---
tags:
- studio-project
prefix: FOOB
name: Foobot API Plugin
status: active
client: Internal
type: internal
repo: git@github.com:markbaindesign/wp-foobot-api.git
sector: WordPress Plugin
stack: WordPress · PHP · DDEV · PHPUnit · GitHub Actions
path: /media/data/dev/ddev/wp-foobot-api-plugin
asana: "yes"
qa: "no"
inbox: "no"
open_tasks: 0
current_focus: ""
next_action: ""
---

# Foobot API Plugin (FOOB)

Internal WordPress plugin ("Air Quality Data from Foobot", slug `aq-data-foobot`) published to WordPress.org under the approved slug `air-quality-data-from-foobot`. Pulls air quality data from the Foobot API and displays it via a shortcode, with an admin settings page (device list, test connection, admin-bar reading) and a PHPUnit/PHPCS/GitHub Actions pipeline.

## Deployment

GitHub Actions: `test.yml` runs PHPUnit + PHPCS on every push/PR to `master`/`develop`. `deploy.yml` triggers on any `*.*.*` tag push, re-runs tests, then commits to the WordPress.org SVN repo (`air-quality-data-from-foobot`) and attaches a zip to a matching GitHub Release. Requires `SVN_USERNAME`/`SVN_PASSWORD` repo secrets (configured).

## Notes

- Local dev via DDEV (moved from VVV in July 2026) at `https://wp-foobot-api.ddev.site`
- Demo site: https://foobot.bain.design
- 1.3.0 released 2026-07-28: admin UX additions (device list, masked API key, test connection, admin bar reading), several security fixes (XSS escaping, uninstall cleanup, API key URL exposure), and CI/testing infrastructure added for the first time
