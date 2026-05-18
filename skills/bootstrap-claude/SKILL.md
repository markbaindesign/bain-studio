---
name: bootstrap-claude
description: Bootstrap a new Claude project — links an Asana project and writes default permissions to .claude/settings.json. Use when starting a new project, setting up Claude in a repo, or saying "bootstrap this project".
argument-hint: [asana-gid]
allowed-tools: [Bash, Read, Write, Edit]
---

# Bootstrap Claude Skill

Set up Claude for the current project. Two steps: link Asana, write default permissions.

Arguments provided: $ARGUMENTS

---

## Step 1 — Link Asana Project

### 1a. Check if already linked

Read `CLAUDE.md` (if it exists) and `.claude/` for any line matching `ASANA_PROJECT_GID`.
If found, report it and skip to Step 2.

### 1b. Search by name

Search Asana for a project matching the current directory name (case-insensitive, partial match OK):

```bash
curl -s "https://app.asana.com/api/1.0/projects?workspace=$ASANA_WORKSPACE_GID&opt_fields=name,gid&limit=100" \
  -H "Authorization: Bearer $ASANA_TOKEN"
```

If a match is found, confirm it with the user before using it.

### 1c. Ask if not found

If no match is found and no GID was passed as an argument, ask the user:

> I couldn't find an Asana project matching "**{dir-name}**". Please paste the project GID (found in the project URL on app.asana.com).

If a GID was passed as `$ARGUMENTS`, use that directly.

### 1d. Save to CLAUDE.md

Append (or create) `CLAUDE.md` at the project root with:

```markdown
## Asana

ASANA_PROJECT_GID: {GID}
```

If CLAUDE.md already exists, read it first and insert the Asana section without duplicating content.

---

## Step 2 — Write Default Permissions

Create `.claude/settings.json` in the project root. If it already exists, read it first and merge — do not overwrite existing keys.

Write the following defaults:

```json
{
  "permissions": {
    "allow": [
      "Bash(git *)",
      "Bash(git log*)",
      "Bash(git diff*)",
      "Bash(git status)",
      "Bash(npm run *)",
      "Bash(npm install)",
      "Bash(npm ci)",
      "Bash(ls *)",
      "Bash(find . *)",
      "Bash(grep *)",
      "WebSearch",
      "WebFetch(*)"
    ]
  }
}
```

Ensure the `.claude/` directory exists (`mkdir -p .claude`) before writing.

---

## Step 3 — Report

Print a summary:

- Asana project GID linked (with a link: `https://app.asana.com/0/{GID}`)
- `.claude/settings.json` written (list the permissions added)
- `CLAUDE.md` updated

If anything was skipped because it already existed, say so.
