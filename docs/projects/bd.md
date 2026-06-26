---
tags:
- studio-project
prefix: BD
name: Bain Website
status: active
client: Internal
type: internal
stack: WordPress · DDEV · PHP · Grunt
path: /media/data/dev/bain/www/bain.design
asana: "yes"
qa: "yes"
inbox: "yes"
repo: git@github.com:markbaindesign/markbaindesign-wp.git
---

# Bain Website (BD)

Studio portfolio and design website. Custom WordPress theme (`bain-design-theme`) and companion plugin (`bd-custom`). DDEV local dev.

- **Local:** https://bain.design.ddev.site
- **Production:** https://bain.design

## Open tasks (active)

- BD-018 — Port studio cats to bash (terminal launcher)
- BD-019 — Rename project to [BDW]
- BD-020 — Promote Mark to project admin

## Notes

- CPTs use `bd324_` prefix; plugin must be active for CPTs to register
- New styles go in `theme.css` inside the appropriate `@layer`
- Asana project GID: `1215368887959233`
