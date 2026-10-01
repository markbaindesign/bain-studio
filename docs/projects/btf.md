---
tags:
- studio-project
prefix: BTF
name: Bain Theme Factory
status: active
client: Internal
type: internal
repo: git@github.com:markbain/bain-theme-factory.git
sector: Studio tooling
stack: WordPress · FSE block themes · theme.json · DDEV
path: /media/data/dev/bain-theme-factory
asana: "yes"
qa: "no"
inbox: "no"
open_tasks: 19
current_focus: Slipstream shipped; defining the MVP free theme for WordPress.org
next_action: "BTF-014 — Decide what the MVP theme is"
---

# Bain Theme Factory (BTF)

Internal project. Produces WordPress FSE block themes and holds the studio CSS
foundation spec they are built against.

Goal includes a portfolio of simple, useful **free themes on WordPress.org** that
promote the studio's custom theme work. Publishing to the directory itself is
wp-repo-factory's job (plugins first, themes later), not a second pipeline here.

Absorbed `wp-theme-factory` (WTF) on 2026-09-14: its idea generation pipeline
moved to `pipeline/` and its open tasks became BTF-009 to BTF-014.

Themes produced here are **separate repositories** — a theme has to clone into
`wp-content/themes` under its own slug, so it cannot be nested. `/themes/` is
gitignored in this repo and each theme is registered on its own.

## Key files

- `css-foundation-spec.md` — the portable CSS foundation (tokens, fluid scales,
  flow primitive, layer contract). Status: draft, not started.
- `pipeline/` — theme idea generation: `fetch-inspiration.py` pulls new
  WordPress.org and GitHub themes into `inspiration-feed.json`;
  `idea-generation.md` lists the manual inspiration sources
- `CLAUDE.md` — project context and Asana wiring

## Themes produced

| Theme | Repo | Status |
|---|---|---|
| Slipstream | `git@github.com:markbain/slipstream.git` | 0.1.0, unreleased |

## Notes

The block theme playbook that came out of the Slipstream build lives in the
studio KB, not here: `docs/utilities/wp-block-themes.md`. It carries the
theme.json and caching traps that fail silently, and should be read before
starting any block theme.

The CSS foundation spec predates Slipstream and is still marked "not started".
Slipstream implements a large part of it and resolves two of its open questions
— the layer contract, and whether the foundation ships components — so the spec
is now behind the practice.

## Open tasks (active)

- BTF-014 — Decide what the MVP theme is
- BTF-009 — Create theme repo pipeline & skillset
- BTF-010 — A11Y.md (github.com/fecarrico/A11Y.md)
- BTF-011 — Plan demo site creation pipeline
- BTF-034 — Functional testing of wordpress theme test data
- BTF-035 — Automate visual testing?
