---
tags: [utility, hermes, asana]
god: hermes
command: python3 studio/scripts/asana_conform.py
description: Check the Asana template and every registered project against studio conventions. Read-only.
---

# asana-conform

Reports where an Asana project has drifted from the conventions the studio's tooling
actually reads. Read-only: it makes no Asana writes, so it is safe to run unattended and
from the ops worktree.

```bash
python3 studio/scripts/asana_conform.py              # template + every registered project
python3 studio/scripts/asana_conform.py --project TSTY
python3 studio/scripts/asana_conform.py --template
python3 studio/scripts/asana_conform.py --json
```

Exit code is 1 when any **error** is found, 0 otherwise, so it works as a scheduled check.

## What it checks, and why each check is there

Only conventions something reads are checked. A field no skill or script references is not
drift, it is decoration.

| Check | Level | Because |
|---|---|---|
| `NEXT UP` present | error | `sync.py --create-task` defaults to it, as does `/qa-capture` |
| `DONE` present | error | `/studio-ghost-projects` reads it |
| `Local ID` / `Last Synced` attached, by the shared GID | error | every mirror, every local ID and looper routing depend on them. A project with its own copies of these fields carries local IDs in a different field from SL's, and multi-homing silently carries nothing across |
| `Priority` is the canonical field GID | error | `sync.py` matches Priority by GID, never by name. A project on a different `Priority` field mirrors `none` while Asana holds a value |
| Tasks holding a priority only on the duplicate field, or disagreeing between the two | error | the mirror, and therefore `/studio-looper`'s ordering, reads the canonical field alone |
| `DOING`, `TO DO`, `STALLED`, `SOMEDAY/MAYBE` present | warn | `/blocked-sweep` expects `STALLED`; the rest are convention |
| Section order | warn | cosmetic, but it is how every project reads at a glance |
| Duplicate section names, stray `Untitled section` | warn | duplication leftovers |
| A `Scope` or `Features` field still holding the template's placeholder options verbatim | warn | those fields are project-local, so duplication copies a previous client's list into every new project. Holding the full set unedited means it was never authored |
| Field attached twice | warn | ambiguous for anything matching by name |

Queue projects (`SL`, `SLT`, `SLK`) run their own section set by design, per ADR 009 and
ADR 017, so their sections are not checked.

## What it does not do

It does not fix anything. Conforming the template is a separate, deliberate write — see the
audit at `$STUDIO_CONTENT_DIR/research/2026-11-06-asana-project-audit.md` for the findings
this check was built from, and for what has to happen in the Asana UI because the API has no
endpoint for it (deleting an enum option, rules, saved views, field order).
