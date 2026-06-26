---
tags:
- studio-project
prefix: KF-WEB
name: Khyentse Foundation Website
status: active
client: Khyentse Foundation
type: client
repo: git@bitbucket.org:markbaindesign/kf-21.git
sector: Non-profit · Religion · Culture
stack: WordPress · Custom Theme · 15 custom plugins · VVV · WP Engine
path: /media/data/dev/vvv/clients/www/kf-21
asana: "yes"
qa: "no"
inbox: "no"
open_tasks: 0
current_focus: ""
next_action: ""
---

# Khyentse Foundation Website (KF-WEB)

Client project. Custom WordPress theme + 15 custom plugins. 21st anniversary website. Local dev via VVV at `http://kf-21.test/`. Hosted on WP Engine. PHP 8.3.

## Key contacts

- **Khyentse Foundation** — client

## Deployment

CI/CD via Bitbucket Pipelines. Push to `main` → production. `release_script.sh` manages versioning and branch workflow.

## Notes

- Local dev: VVV at `kf-21.test`
- Hosted on WP Engine (not Cloudways)
- Grunt for SCSS/JS build
- Multilingual (i18n)
