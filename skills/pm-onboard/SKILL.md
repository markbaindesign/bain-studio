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
import os, json
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path("~/.claude/studio/.env").expanduser())
field_gid = os.getenv("ASANA_LOCAL_ID_FIELD_GID", "")
ids_file = Path(".claude/asana-ids.json")
ids_file.parent.mkdir(exist_ok=True)
if not ids_file.exists():
    ids_file.write_text(json.dumps({
        "custom_field_gid": field_gid,
        "tasks": {},
        "next_seq": 1,
        "posted_progress": {}
    }, indent=2))
    print(f"asana-ids.json written (field GID: {field_gid or 'NOT SET — check .env'})")
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

---

## Step 6 — Check and add Asana custom field

Check whether the "Local ID" custom field is already attached to the project, then add it if not:

```bash
python3 - <<'EOF'
import os, requests
from dotenv import load_dotenv
load_dotenv(os.path.expanduser("~/.claude/studio/.env"))
token = os.environ["ASANA_PAT"]
gid = "{GID}"
field_gid = os.environ["ASANA_LOCAL_ID_FIELD_GID"]

# Check if already attached
r = requests.get(
    f"https://app.asana.com/api/1.0/projects/{gid}/custom_field_settings",
    headers={"Authorization": f"Bearer {token}"}
)
fields = [f["custom_field"]["gid"] for f in r.json().get("data", [])]
if field_gid in fields:
    print("Local ID custom field already present — skipping.")
else:
    r = requests.post(
        f"https://app.asana.com/api/1.0/projects/{gid}/addCustomFieldSetting",
        headers={"Authorization": f"Bearer {token}"},
        json={"data": {"custom_field": field_gid, "is_important": False}}
    )
    if r.status_code in (200, 201):
        print("Custom field added.")
    else:
        print(f"Warning: {r.status_code} {r.text}")
EOF
```

Replace `{GID}` with the actual `ASANA_PROJECT_GID`.

In **update mode**, always run this check — it's safe to run on an already-configured project.

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
