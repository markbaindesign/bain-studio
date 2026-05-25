---
name: pm-onboard
description: Onboard a project into the studio PM system, or update an existing one to current standards. Elicits Asana GID, task prefix, project name, client contacts, and tone from the user, then writes the Asana section to CLAUDE.md, creates the .claude/ scaffold, seeds asana-ids.json, and runs an initial sync. Use when starting a new client project, wiring up an existing one to the studio PM, or auditing/updating an existing setup.
allowed-tools: [Read, Write, Edit, Bash]
---

# PM Onboard / Update Skill

Wire up or update the current project in the studio PM system. First audit existing config, then fill gaps and align to current standards.

---

## Step 1 — Audit current state

Read `CLAUDE.md` if it exists. Also check for these files:

```bash
ls .claude/ 2>/dev/null
cat .claude/asana-ids.json 2>/dev/null
cat .claude/open-questions.md 2>/dev/null
ls .claude/adr/ 2>/dev/null
```

Determine what's already present:

| Item | Present? |
|------|----------|
| `ASANA_PROJECT_GID` in CLAUDE.md | yes / no |
| `ASANA_TASK_PREFIX` in CLAUDE.md | yes / no |
| `ASANA_PROJECT_NAME` in CLAUDE.md | yes / no |
| `## Studio PM` section in CLAUDE.md | yes / no |
| `.claude/asana-ids.json` exists | yes / no |
| `.claude/open-questions.md` exists | yes / no |
| `.claude/adr/` directory exists | yes / no |

Set `MODE`:
- If `ASANA_PROJECT_GID` is already present → **update mode** (fill gaps, align to current setup)
- If `ASANA_PROJECT_GID` is missing → **onboard mode** (full setup from scratch)

Tell the user which mode you're in and summarise what's missing before continuing.

---

## Step 2 — Confirm Asana use (onboard mode only)

If in onboard mode, ask: "Does this project use Asana for task tracking?" If no, skip Steps 3–6 and go to Step 4b. If yes, continue with Step 3.

---

## Step 3 — Elicit required fields

Ask for any fields that are missing. Show your suggested value and let the user confirm or override. Ask one prompt at a time — do not batch all at once.

**Required Asana fields (skip if already present):**

1. **Asana Project GID** — `ASANA_PROJECT_GID`
   - Say: "Paste the Asana project GID. Find it in the project URL: app.asana.com/0/**[GID]**/list"
   - No default — must be provided.

2. **Task prefix** — `ASANA_TASK_PREFIX`
   - Suggest: uppercase initials of the project name, 2–4 chars (e.g. `acme-corp` → `ACM`)
   - Check `~/.claude/studio/projects.md` if it exists to avoid collisions.

3. **Project name** — `ASANA_PROJECT_NAME`
   - Suggest: a clean version of the directory name (e.g. `acme_corp` → `Acme Corp`)

**Optional Studio PM fields:**

4. **Client name** — full name and role (e.g. "Jane Smith — e-commerce retailer, London") → CLAUDE.md
5. **Client tone** — one line (e.g. "Warm, professional, concise. No jargon.") → CLAUDE.md
6. **PM / client contact** — name and email → `.claude/settings.local.json` (gitignored)
7. **Billing rate** — e.g. `£48/hr` → `.claude/settings.local.json` (gitignored)

In **update mode**, only ask for fields that are genuinely missing. If all fields are present, skip this step entirely.

---

## Step 4 — Write to CLAUDE.md

**4a — Asana section:**

If `ASANA_PROJECT_GID` / `ASANA_TASK_PREFIX` / `ASANA_PROJECT_NAME` are missing or need updating, write or update the `## Asana` section:

```markdown
## Asana

ASANA_PROJECT_GID: {gid}
ASANA_TASK_PREFIX: {prefix}
ASANA_PROJECT_NAME: {name}
```

**4b — Studio PM section (CLAUDE.md):**

If client name or tone were provided and are not already documented, append a `## Studio PM` section to CLAUDE.md:

```markdown
## Studio PM

- **Client:** {client name and role}
- **Tone:** {tone note}
```

Do not include contact details or billing rate here — those go in the local settings file (Step 4c). Do not duplicate information already present.

**4c — Sensitive fields (.claude/settings.local.json):**

If contact or billing rate were provided, write them to `.claude/settings.local.json` under an `"env"` key so they stay gitignored:

```json
{
  "env": {
    "CLIENT_CONTACT": "{name} ({email})",
    "CLIENT_BILLING_RATE": "{rate}"
  }
}
```

Read the existing `.claude/settings.local.json` first and merge — do not overwrite other keys. Confirm `.claude/settings.local.json` is in `.gitignore`; add it if not.

---

## Step 5 — Scaffold .claude/

Create any missing files:

**`asana-ids.json`** (if missing or empty):

```bash
python3 - <<'EOF'
import json
from pathlib import Path
ids_file = Path(".claude/asana-ids.json")
ids_file.parent.mkdir(exist_ok=True)
if not ids_file.exists():
    ids_file.write_text(json.dumps({
        "custom_field_gid": None,
        "last_synced_field_gid": None,
        "tasks": {},
        "next_seq": 1,
        "posted_progress": {}
    }, indent=2))
    print("asana-ids.json written")
else:
    print("asana-ids.json already exists — skipping")
EOF
```

**`open-questions.md`** (if missing):

```markdown
# Open Questions

Questions awaiting client or stakeholder input.

<!-- Format: - [ ] Question — *asked YYYY-MM-DD* -->
```

**`adr/` directory** (if missing):

```bash
mkdir -p .claude/adr
```

**`.claude/settings.json` permissions (merge, do not overwrite):**

Ensure the following entries are in the `permissions.allow` array. Read the file first, merge, and write back only if something is missing:

```python
import json
from pathlib import Path

required = ["Bash(*)", "Read(*)", "Write(*)", "Edit(*)", "WebSearch(*)", "WebFetch(*)"]
f = Path(".claude/settings.json")
data = json.loads(f.read_text()) if f.exists() else {}
allow = data.setdefault("permissions", {}).setdefault("allow", [])
added = [p for p in required if p not in allow]
if added:
    allow.extend(added)
    f.write_text(json.dumps(data, indent=2) + "\n")
    print(f"Added to settings.json: {added}")
else:
    print("settings.json permissions already complete")
```

---

## Step 6 — Set up Asana custom fields

Create and attach the "Local ID" and "Last Synced" custom fields for the project:

```bash
python3 ~/.claude/studio/sync.py --setup --project {PREFIX}
```

Replace `{PREFIX}` with the actual `ASANA_TASK_PREFIX`. This is safe to re-run — fields already configured are skipped.

---

## Step 7 — Run sync

```bash
python3 ~/.claude/studio/sync.py --project {PREFIX}
```

Report: tasks found, whether the mirror was written, any errors.

---

## Step 8 — Confirm

Tell the user:

- **What changed** (in update mode, distinguish "already present" from "added now")
- Where the mirror lives: `.claude/asana-mirror.md`
- That overnight sync runs at 2am, or they can run `/sync` any time
- If any gaps remain (e.g. optional fields they skipped), note them briefly
