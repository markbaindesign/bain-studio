---
name: recap
description: Project re-entry brief. Run from inside a project directory when opening a new terminal tab or switching focus. Surfaces Asana state, git context, QA inbox/review counts, inbox, open questions, and a synthesised next action.
allowed-tools: [Read, Bash]
---

# Recap

Restore context for the current project. Run from inside the project directory.

## Steps

### 1. Identify the project

Read `CLAUDE.md` in the current directory. Extract:
- `ASANA_TASK_PREFIX`
- `ASANA_PROJECT_NAME`

If no `CLAUDE.md` found, abort: "Not in a recognised project directory."

### 2. Git context

Run the following:

```bash
git branch --show-current
git status --short
git log --oneline -3
```

Note:
- Current branch
- Whether there are uncommitted changes (dirty working tree)
- Last 3 commit messages

### 3. Asana state

Read `.claude/asana-mirror.md`. Extract:
- Tasks marked **In Progress** (look for `status: In Progress` or `## In Progress` section)
- Tasks marked **Blocked**
- Tasks completed in the last 7 days (look for `completed_at` within range)
- Count of total open tasks

### 4. Inbox

Check `.claude/inbox/` for any `.md` files (unread messages). If any exist, list their filenames and first line.

### 5. QA status

Check if a `qa/` directory exists. If it does:

```bash
ls qa/qa-inbox/ 2>/dev/null | wc -l
ls qa/qa-review/ 2>/dev/null | wc -l
```

Report:
- **qa-inbox** count — items waiting to be worked on
- **qa-review** count — items awaiting sign-off

Skip this section silently if `qa/` doesn't exist.

### 6. Open questions

Read `.claude/open-questions.md` if it exists. List any unchecked items (`- [ ]`).

### 7. Synthesise next action

Cross-reference the last commit message(s) with in-progress task titles:
- If a commit message mentions keywords that overlap with an in-progress task title, surface: "You were probably working on **{task}** (last commit: _{message}_)"
- If no overlap, surface the highest-priority in-progress task, or the first open task if none are in progress

### 8. Output the recap

```
## Recap — {PROJECT_NAME} — {YYYY-MM-DD HH:MM}

### Git
Branch: {branch} {[DIRTY] if uncommitted changes}
Recent: {last 3 commits, one per line}

### In progress
{list of in-progress tasks, or "None"}

### Blocked
{list of blocked tasks, or "None"}

### QA  _(omit section if no qa/ folder)_
Inbox: {N} | Review: {N}

### Inbox
{list of unread messages, or "Clear"}

### Open questions
{list of unchecked items, or "None"}

### Next action
→ {synthesised suggestion}
```

Keep it under 30 lines. No padding.
