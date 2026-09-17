---
name: check-inbox
description: Read and process any pending messages in the current project's .claude/inbox/ (and studio/inbox/ in bain-studio). Surfaces alerts, handoffs, and events from other agents or the studio system. Archives processed messages.
allowed-tools: [Read, Bash, Edit]
---

# Check Inbox

Process all pending messages for the current project.

## Steps

### 1. Find the inbox

Check both of these, relative to the current project root (the directory containing `CLAUDE.md`):

- `.claude/inbox/` — project inboxes
- `studio/inbox/` — the studio inbox. Only exists in bain-studio; messages sent `to: studio`
  land here, not in `.claude/inbox/`.

```bash
ls .claude/inbox/msg-*.md studio/inbox/msg-*.md 2>/dev/null
```

Hermes' daily sweep posts each message to Slack and stamps it `notified_at`, but leaves it in
the inbox — so a message with `notified_at` is still unread here. Only this skill archives.

If neither inbox has any `msg-*.md` files, report "Inbox empty." and stop.

### 2. Read each message

For each `msg-*.md` file across both inboxes (oldest first — sort by filename):

Parse the frontmatter:
- `from` — sending agent or system
- `type` — `event`, `handoff`, `alert`, `report`, or `note`
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

**note:**
Something another session wants Mark to know or decide — often a finding outside its own
project. Summarise it and surface any suggested next step; don't act on it without Mark.

**report:**
A completed-work summary from another agent. File it mentally as context; no action required.

### 4. Archive processed messages

Move each processed message into the `processed/` folder of the inbox it came from:

```bash
for d in .claude/inbox studio/inbox; do
  ls $d/msg-*.md >/dev/null 2>&1 || continue
  mkdir -p $d/processed && mv $d/msg-*.md $d/processed/
done
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
