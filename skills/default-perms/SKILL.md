---
name: default-perms
description: Write default permissions to .claude/settings.json for the current project. Use when setting up a new project or when asked to add default permissions.
allowed-tools: [Bash, Read, Write, Edit]
---

# Default Permissions Skill

Write the standard default permissions to `.claude/settings.json` in the current project.

---

## Step 1 — Check for existing settings

Check if `.claude/settings.json` already exists:

```bash
ls .claude/settings.json 2>/dev/null
```

If it exists, read it first so you can merge without overwriting unrelated keys.

## Step 2 — Write permissions

Ensure the `.claude/` directory exists:

```bash
mkdir -p .claude
```

Write (or merge) the following permissions into `.claude/settings.json`:

```json
{
  "permissions": {
    "allow": [
      "Bash(*)",
      "Read(*)",
      "Write(*)",
      "Edit(*)",
      "WebSearch(*)",
      "WebFetch(*)",
      "mcp__plugin_asana_asana__*"
    ]
  }
}
```

If the file already exists, merge the `allow` array — add any missing entries from the list above without removing entries that are already there. Preserve all other existing keys.

## Step 3 — Report

Confirm `.claude/settings.json` has been written and list the permissions now in the allow list.
