---
name: looper-onboard
description: Onboard a project onto the Studio Looper — wires the shared Local ID/Last Synced custom fields, runs the first real sync so existing tasks get proper prefixed IDs, and verifies bainbot actually has access. Run this any time a project gains Asana wiring, before multi-homing any of its tasks into Studio Looper (SL). Args: prefix
allowed-tools: [Read, Edit, Bash, AskUserQuestion]
---

# Looper Onboard

A project can look fully wired (Asana block in its CLAUDE.md, `sync.py --setup` run, GID present)
and still silently fail the moment a task is multi-homed into Studio Looper (SL). This skill exists
because that exact failure happened with FOOB: `--setup` had wired the custom fields, but no real
sync had ever run, so no FOOB task had a `FOOB-NNN` Local ID yet. When a FOOB task was multi-homed
into SL, sync.py had no foreign ID to preserve and would have assigned it a fresh `SL-NNN` ID
instead — which breaks `studio-looper`'s prefix-based routing back to the FOOB repo (Step 4a
resolves the project purely from the ID prefix). Separately, bainbot turned out not to actually be
a member of the FOOB Asana project despite being told it was — the register-project skill only
asks the user to confirm this, it never verifies it.

Both gaps are silent until a real sync or a real looper run hits them. This skill verifies both,
for real, before either happens.

Arguments: $ARGUMENTS
- First arg: project prefix (e.g. `FOOB`)

## Step 1 — Resolve the project

```bash
python3 - <<'PYEOF'
import json, os, sys
prefix = sys.argv[1]
projects = json.load(open('/media/data/dev/bain-studio/studio/projects.json'))
for p in projects:
    cm = os.path.join(p['path'], 'CLAUDE.md')
    if os.path.exists(cm) and f'ASANA_TASK_PREFIX: {prefix}' in open(cm).read():
        print(p['path']); sys.exit(0)
print('NOT_FOUND')
PYEOF
```

If `NOT_FOUND`: stop and tell the user to run `/register-project` first (this prefix isn't in
`projects.json` with a matching `ASANA_TASK_PREFIX` in its CLAUDE.md).

## Step 2 — Confirm the Asana block is complete

Read `{path}/CLAUDE.md`. It must have all three of `ASANA_PROJECT_GID`, `ASANA_TASK_PREFIX`,
`ASANA_PROJECT_NAME`. If any are missing, stop and point to `/register-project`'s Step 4.

## Step 3 — Wire the shared custom fields

```bash
python3 /media/data/dev/bain-studio/studio/sync.py --setup --project {PREFIX}
```

This is safe to re-run. It attaches the studio-wide `Local ID` / `Last Synced` custom fields
(shared GIDs from `studio/.env` — `ASANA_LOCAL_ID_FIELD_GID` / `ASANA_LAST_SYNCED_FIELD_GID`) to
this project. **The shared GIDs matter**: if a project's fields were ever created fresh instead of
reusing the shared ones (e.g. `.env` vars were unset at the time), its Local ID values live in a
different Asana custom field than SL's, and multi-homing would carry no value across at all.

## Step 4 — Run a real sync (this is the step `--setup` alone skips)

```bash
python3 /media/data/dev/bain-studio/studio/sync.py --project {PREFIX}
```

This does two things at once, and both are the actual point of this skill:

1. **Tests bainbot's access for real.** A `403 Forbidden` fetching tasks means bainbot is not
   actually a member of the Asana project, no matter what the user was told or believes. Do not
   accept "I confirmed it" as ground truth anywhere in this flow — this API call is the ground
   truth. If it 403s: tell the user plainly, ask them to add bainbot as a member, then retry this
   step. Do not proceed past a 403.
2. **Assigns Local IDs to every existing task.** Without this, the project's `asana-ids.json` has
   `"tasks": {}` even though the fields are wired — nothing has an ID yet to preserve when
   multi-homed.

## Step 5 — Verify readiness

Read `{path}/asana-ids.json`.

**Field GIDs match the shared config** (skip if `studio/.env` doesn't set these — some setups are
intentionally standalone):
```bash
grep -E "ASANA_LOCAL_ID_FIELD_GID|ASANA_LAST_SYNCED_FIELD_GID" /media/data/dev/bain-studio/studio/.env
```
Compare against `custom_field_gid` / `last_synced_field_gid` in the project's `asana-ids.json`.
Mismatch = **FAIL** — this project's Local IDs won't carry over into SL at all.

**Tasks have real prefixed IDs**:
- If `tasks` is empty: not a failure, but **not yet proven either** — note "no tasks in this
  project yet; Local IDs will be assigned as tasks are added, but this hasn't actually been
  exercised. Re-run Step 4 (or just this skill) after adding at least one task, and before
  multi-homing anything into SL for the first time."
- If `tasks` is non-empty: confirm at least one value matches `^{PREFIX}-\d+$`. Anything else is
  a **FAIL** — the prefix isn't what's actually being assigned.

**Prefix uniqueness** — a collision would make routing ambiguous:
```bash
grep -rl "ASANA_TASK_PREFIX: {PREFIX}" $(python3 -c "import json; print(' '.join(p['path']+'/CLAUDE.md' for p in json.load(open('/media/data/dev/bain-studio/studio/projects.json'))))") 2>/dev/null
```
More than one file = **FAIL**, name the colliding projects.

## Step 6 — Report

```
looper-onboard: {name} ({PREFIX})
  ✓/✗ Asana block complete
  ✓/✗ Shared custom fields wired
  ✓/✗ bainbot access confirmed (real sync, not just asked)
  ✓/✗/… Local IDs assigned ({N} tasks, prefix {PREFIX}-NNN / no tasks yet)
  ✓/✗ Prefix unique across registry

{PREFIX} is ready to multi-home tasks into Studio Looper. / {PREFIX} is NOT ready: {specific blocking reason(s)}.
```

## Note for `/register-project`

`register-project`'s Asana step currently ends at "tell the user to confirm bainbot is a member...
and run `sync.py --setup`". That's necessary but not sufficient — it stops one step short of
proving either claim true. When wiring an *existing* Asana project via `register-project`, follow
up by running `/looper-onboard {PREFIX}` before considering that project ready for the Looper.
