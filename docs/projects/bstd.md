---
tags:
- studio-project
prefix: BSTD
name: Bain Studio
status: active
client: Internal
type: internal
repo: git@github.com:markbain/bain-studio.git
sector: Studio tooling
stack: Python · Flask · Claude Code
path: /media/data/dev/bain-studio
asana: "yes"
qa: "yes"
inbox: "yes"
open_tasks: 16
current_focus: Olympus model build-out and infrastructure clarity
next_action: "BSTD-010 — Audit and complete studio dashboard"
---

# Bain Studio (BSTD)

Internal project. Studio AI operating layer, tooling, and infrastructure.

## Key files

- `docs/Pantheon.md` — founding architecture doc
- `studio/sync.py` — Hermes sync loop
- `studio/dashboard/server.py` — Flask finance dashboard
- `studio/notifier.py` — Slack notifier
- `studio/projects.json` — project registry

## Open tasks (active)

- BSTD-010 — Audit and complete studio dashboard
- BSTD-021 — Add API cost tracker to studio dashboard
- BSTD-012 — Backfill Mnemosyne
- BSTD-023 — Create the studio brand voice
- BSTD-024 — Use AI to contribute to WordPress
- BSTD-025 — Create a skill to open single project in terminal
- BSTD-029 — Confirm Mod 130 / IRPF netting with gestor
- BSTD-030 — Backfill Q1 IVA Soportado (€141.11)
- BSTD-031 — Complete subscription/DD account mapping
- BSTD-032 — Research best hosting for client staging
- BSTD-033 — Create dev-ops.md
- BSTD-034 — Create CRM
- BSTD-035 — Promote Mark to project admin
- BSTD-019 — Fix VVV shutdown password prompt
- BSTD-005 — Replace ASANA_PAT with bainbot token
- BSTD-020 — LinkedIn job check

## Notes

- Asana project GID: `1215208851588912`
- All Asana mutations via `sync.py` (bainbot PAT), never MCP tools directly
