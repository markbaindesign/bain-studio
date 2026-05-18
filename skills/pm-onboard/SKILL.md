---
name: pm-onboard
description: Onboard a project into the studio PM system. Elicits Asana GID, task prefix, project name, client contacts, and tone from the user, then writes the Asana section to CLAUDE.md, creates the .claude/ scaffold, seeds asana-ids.json, and runs an initial sync. Use when starting a new client project or wiring up an existing one to the studio PM.
allowed-tools: [Read, Write, Edit, Bash]
---

# PM Onboard Skill

Wire up the current project to the studio PM system. Collect the required details, update CLAUDE.md, scaffold `.claude/`, and run the first sync.

---

## Step 1 — Read current state

Read `CLAUDE.md` in the current working directory. Note:
- What's already there (client name, contacts, tech stack)
- Whether `ASANA_PROJECT_GID` is already present (if so, confirm the user wants to update it)
- The project directory name (used to suggest a prefix)

---

## Step 2 — Elicit required fields

Ask the user for the following, one prompt at a time. Show your suggested value (if you can infer one) and let them confirm or override.

**Required:**

1. **Asana Project GID** — `ASANA_PROJECT_GID`
   - Say: "Paste the Asana project GID. Find it in the project URL: app.asana.com/0/**[GID]**/list"
   - No default — must be provided.

2. **Task prefix** — `ASANA_TASK_PREFIX`
   - Suggest: uppercase initials of the project name, 2–4 chars (e.g. `acme-corp` → `ACM`, `client-site` → `CLI`)
   - Must be unique across studio projects. Check `~/dev/bain-studio/studio/projects.md` if it exists.

3. **Project name** — `ASANA_PROJECT_NAME`
   - Suggest: a clean version of the directory name (e.g. `acme_corp` → `Acme Corp`)
   - Used in mirrors and morning reports.

**Optional (skip if already in CLAUDE.md):**

4. **Client name** — full name and role (e.g. "Jane Smith — e-commerce retailer, London")
5. **PM / client contact** — name and email for the person you correspond with
6. **Billing rate** — hourly rate (e.g. `£48/hr`)
7. **Client tone** — one line describing the communication style (e.g. "Warm, professional, concise. No jargon.")

---

## Step 3 — Write to CLAUDE.md

Append an `## Asana` section to `CLAUDE.md` (or update the existing one):

```markdown
## Asana

ASANA_PROJECT_GID: {gid}
ASANA_TASK_PREFIX: {prefix}
ASANA_PROJECT_NAME: {name}
```

If optional fields were provided and are not already documented elsewhere in CLAUDE.md, also append a `## Studio PM` section:

```markdown
## Studio PM

- **Client:** {client name and role}
- **Contact:** {name} ({email})
- **Billing rate:** {rate}
- **Tone:** {tone note}
```

Do not duplicate information already present in CLAUDE.md.

---

## Step 4 — Scaffold .claude/

Create the `.claude/` directory in the project root if it doesn't exist.

Create `.claude/asana-ids.json` with the shared workspace field GID pre-seeded. Read the field GID from the studio `.env`:

```bash
python3 - <<'EOF'
import os, json
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path("~/dev/bain-studio/studio/.env").expanduser())
field_gid = os.getenv("ASANA_LOCAL_ID_FIELD_GID", "")
ids_file = Path(".claude/asana-ids.json")
ids_file.parent.mkdir(exist_ok=True)
ids_file.write_text(json.dumps({
    "custom_field_gid": field_gid,
    "tasks": {},
    "next_seq": 1,
    "posted_progress": {}
}, indent=2))
print(f"asana-ids.json written (field GID: {field_gid or 'NOT SET — check .env'})")
EOF
```

Create `.claude/open-questions.md` if it doesn't exist:

```markdown
# Open Questions

Questions awaiting client or stakeholder input.

<!-- Format: - [ ] Question — *asked YYYY-MM-DD* -->
```

Create `.claude/adr/` directory if it doesn't exist.

---

## Step 5 — Add Local ID custom field to the Asana project

Before running the sync, attach the shared "Local ID" custom field to the project so the sync can write IDs back to tasks:

```bash
python3 - <<'EOF'
import os, requests
from dotenv import load_dotenv
load_dotenv(os.path.expanduser("~/dev/bain-studio/studio/.env"))
token = os.environ["ASANA_PAT"]
gid = "{GID}"
field_gid = os.environ["ASANA_LOCAL_ID_FIELD_GID"]
r = requests.post(
    f"https://app.asana.com/api/1.0/projects/{gid}/addCustomFieldSetting",
    headers={"Authorization": f"Bearer {token}"},
    json={"data": {"custom_field": field_gid, "is_important": False}}
)
if r.status_code in (200, 201):
    print("Custom field added.")
elif r.status_code == 400 and "already exists" in r.text:
    print("Custom field already present — skipping.")
else:
    print(f"Warning: {r.status_code} {r.text}")
EOF
```

Replace `{GID}` with the actual `ASANA_PROJECT_GID`.

---

## Step 6 — Run initial sync

```bash
python3 ~/dev/bain-studio/studio/sync.py --project {PREFIX}
```

Report the result: how many tasks found, whether the mirror was written, any errors.

---

## Step 7 — Confirm

Tell the user:
- What was written to CLAUDE.md
- Where the mirror is: `.claude/asana-mirror.md`
- That overnight sync runs at 2am, or they can run `/sync` any time
- Next step: add tasks in Asana assigned to BainBot to see them in the mirror
