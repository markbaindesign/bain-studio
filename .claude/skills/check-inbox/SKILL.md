---
name: check-inbox
description: Read and process any pending messages in the current project's .claude/inbox/. Surfaces alerts, handoffs, and events from other agents or the studio system. Archives processed messages.
allowed-tools: [Read, Bash, Edit]
---

# Check Inbox

Process all pending messages in `.claude/inbox/` for the current project.

## Steps

### 1. Find the inbox

The inbox is at `.claude/inbox/` relative to the current project root (the directory containing `CLAUDE.md`).

If the inbox doesn't exist or is empty, report "Inbox empty." and stop.

### 2. Read each message

For each `msg-*.md` file in the inbox (oldest first — sort by filename):

Parse the frontmatter:
- `from` — sending agent or system
- `type` — `event`, `handoff`, `alert`, or `report`
- `subject` — one-line summary
- `priority` — `low`, `normal`, `high`, or `urgent`
- `sent_at` — when it was sent

Read the body below the `---` closing fence.

### 3. Act on the message

**alert / urgent or high priority:**
Surface immediately and prominently. If it describes a broken build, failed deploy, or blocking error — investigate now before continuing.

**handoff:**
The sending agent is passing work to this session. Read the body carefully — it will describe what was done, what is next, and any open questions. Treat it as a briefing for the current session.

**event:**
Informational. Note it in the session summary but no action required unless the body says otherwise.

**report:**
A completed-work summary from another agent. File it mentally as context; no action required.

### 4. Archive processed messages

Move each processed message to `.claude/inbox/processed/`:

```bash
mkdir -p .claude/inbox/processed
mv .claude/inbox/msg-*.md .claude/inbox/processed/
```

### 5. Report

Output a summary:

```
## Inbox — {N} message(s)

- [{priority}] {subject} (from: {from}, {sent_at})
  {One line summary of action taken or noted}

{If inbox was empty:}
Inbox empty.
```

If any message was `urgent` or described a blocker, flag it clearly at the top of the report before the list.
