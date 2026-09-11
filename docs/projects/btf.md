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
open_tasks: 1
current_focus: Slipstream shipped; CSS foundation spec still a draft
next_action: "BTF-001 — Review WordPress Playground + GitHub for block theme development"
---

# Bain Theme Factory (BTF)

Internal project. Produces WordPress FSE block themes and holds the studio CSS
foundation spec they are built against.

Themes produced here are **separate repositories** — a theme has to clone into
`wp-content/themes` under its own slug, so it cannot be nested. `/themes/` is
gitignored in this repo and each theme is registered on its own.

## Key files

- `css-foundation-spec.md` — the portable CSS foundation (tokens, fluid scales,
  flow primitive, layer contract). Status: draft, not started.
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

- BTF-001 — Streamlining block theme development with WordPress Playground and GitHub
