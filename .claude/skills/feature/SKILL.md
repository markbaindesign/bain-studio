---
name: feature
description: Capture a feature request — scope it, create an Asana task, and (if large) write a lightweight spec. Works in any active project directory.
allowed-tools: [Read, Write, Edit, Bash]
---

# /feature — Feature Capture

Captures a feature request for the current project. Small features become tasks; larger ones get a spec file first.

## Usage

```
/feature                          — prompted capture
/feature add dark mode toggle     — inline capture
/feature --from-backlog BSTD      — review collector-harvested backlog
```

---

## Step 1 — Identify the project

Read `CLAUDE.md` in the current working directory. Extract:
- `ASANA_TASK_PREFIX` (e.g. `BSTD`, `KF-WEB`)
- `ASANA_PROJECT_GID`

If no CLAUDE.md or prefix found, abort: "Run /feature from a project directory."

---

## Step 2 — Capture the feature

**If args were provided inline** (e.g. `/feature add dark mode toggle`): use the args as the feature name/description. Skip the prompt.

**If `--from-backlog {PREFIX}` was given**: read `$STUDIO_CONTENT_DIR/pipeline/feature-backlog/{PREFIX}.md`. List each item and ask Mark to select one to promote, or type a new one. Once selected, remove the item from the backlog file.

**If no args**: ask:
> "What's the feature? One line — name or description."

---

## Step 3 — Scope check

Ask:
> "Rough size — is this under 4 hours or more?"
> Options: **Task** (under 4h, no spec needed) / **Feature** (4h+, write a spec)

If Mark already gave enough context to judge, skip the question and decide yourself.

---

## Step 4 — Mint a feature ref

Read `.claude/feature-counter.json` in the project root. If it doesn't exist, create it:
```json
{"last": 0}
```

Increment `last` by 1, write back, and format the ref:
```
{PREFIX}-FEAT-{NNN}   e.g. BSTD-FEAT-007
```

---

## Step 5a — Task path (under 4h)

Create an Asana task directly via the mirror:

1. Read `.claude/asana-mirror.md`
2. Find the `TO DO` section for this project
3. Append a new task block:

```
### {PREFIX}-FEAT-{NNN} — {name}
- **Local ID:** {PREFIX}-FEAT-{NNN}
- **Asana ID:** (pending sync)
- **Section:** TO DO
- **Priority:** none
- **Due:** none
- **Start:** none
- **Assignee:** Mark Bain (507443625075)
- **Assignee Status:** inbox
- **Tags:** none
- **Followers:** none
- **Dependencies:** none
- **Dependents:** none
- **Notes:** {description}
- **Blockers:** None identified.
- **Progress:** none
- **Comments:** none
- **Modified:** {YYYY-MM-DDTHH:MM:SS}
- **URL:** (pending sync)
```

4. Run sync to push to Asana:
```bash
cd /media/data/dev/bain-studio && python3 studio/sync.py --project {PREFIX}
```

---

## Step 5b — Feature path (4h+)

First write the spec file, then create the task linking to it.

**Write spec:**

```bash
mkdir -p .claude/features
```

File: `.claude/features/{slug}.md`

```markdown
---
ref: {PREFIX}-FEAT-{NNN}
status: backlog
created: {YYYY-MM-DD}
---
# {name}

## What
{one paragraph — what this feature does}

## Why
{motivation — what pain does it solve or opportunity does it unlock}

## Rough scope
{bullet list of work items}

## Done when
{acceptance criteria — what does working look like}
```

Ask Mark to fill in any sections left blank, or fill in from context if enough was provided.

**Then create the Asana task** (same as Step 5a), but add to Notes:
```
Spec: .claude/features/{slug}.md
Branch: feature/{PREFIX-FEAT-NNN}-{slug}
```

Run sync after writing the mirror entry.

---

## Step 6 — Confirm

Report:
```
Feature captured: {PREFIX}-FEAT-{NNN}
Name: {name}
Size: Task / Feature spec
Task: created in TO DO (syncing to Asana)
Branch: feature/{PREFIX-FEAT-NNN}-{slug}   ← use this when you work it
Spec: .claude/features/{slug}.md            ← (feature path only)
```

---

## Notes

- The feature counter file is `.claude/feature-counter.json` — gitignored in most projects
- Feature spec files in `.claude/features/` are project-local and not committed unless the project opts in
- `--from-backlog` reads from items harvested by `obsidian_collector.py` via `#feature {PREFIX}` tags
- Branch naming follows the same pattern as the task-looper: `feature/{ref}-{slug}`
