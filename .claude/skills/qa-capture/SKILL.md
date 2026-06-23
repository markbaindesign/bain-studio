---
name: qa-capture
description: Quickly log a screenshot as an Asana task without breaking focus. Reads the image, proposes a title and severity, asks one confirmation question, creates the task. Use when you spot an issue mid-session and want to capture it without switching context.
allowed-tools: [Read, Bash]
---

# QA Capture

Log a screenshot as an Asana task in under 30 seconds. No QA pipeline, no review session — just capture and move on.

## Usage

```
/qa-capture
/qa-capture "optional extra context for all items"
```

Drop screenshots into `qa/qa-inbox/` in the current project, then invoke. The skill finds them automatically — no path needed.

---

## Steps

### 1. Identify the project

Read `CLAUDE.md` in the current directory to get `ASANA_TASK_PREFIX` and `ASANA_PROJECT_NAME`.

If not in a project directory, ask: "Which project is this for?" and accept a prefix (e.g. `NORE`, `BSTD`, `KF-WEB`).

### 2. Find screenshots in qa-inbox

```bash
ls {PROJECT_ROOT}/qa/qa-inbox/
```

Filter for image files (`.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`) and files that do NOT already start with a `{PREFIX}-QA-` ref (those are already registered).

If no unregistered images found, report "No screenshots in qa/qa-inbox/ to log." and stop.

If multiple images found, list them and process each one in turn (one confirmation per image).

### 3. Analyse the screenshot

From what you see in the image, determine:

- **Title** — a short, specific task title. Describe the symptom, not the cause. Examples:
  - "Hero image missing on mobile"
  - "Dashboard gnucash totals show as zero"
  - "Contact form submit button unresponsive on iOS"
- **Severity** — pick one:
  - `high` — broken functionality, data loss, or visible to clients/end users
  - `medium` — degraded experience, workaround exists
  - `low` — cosmetic, polish, edge case
- **Feature area** — one or two words: e.g. `dashboard`, `forms`, `mobile`, `nav`, `sync`
- **Description** — one sentence of what's wrong, incorporating any extra context the user provided

### 4. Dedupe check

Before asking the user anything, grep the project mirror for possible duplicates.

Extract keywords from the proposed title: split on spaces, drop words shorter than 4 characters and common stop words (the, and, for, with, on, in, at, to, of, is, are, was). Use the remaining words.

```bash
grep -i "{keyword1}\|{keyword2}\|{keyword3}" {PROJECT_ROOT}/.claude/asana-mirror.md | grep "^### "
```

Score each match by how many keywords appear in the task title. Flag any task with 2+ keyword matches as a likely duplicate.

**If likely duplicates found**, prepend a warning to the confirmation question:

```
Possible duplicate(s):
- {LOCAL_ID} — {task title} ({section})
- {LOCAL_ID} — {task title} ({section})
```

Do not block — the user decides. Just surface it.

**If no matches**, proceed silently.

### 5. Confirm with the user

Present a single `AskUserQuestion` with the proposed task (and any duplicate warning from step 4):

```
[Possible duplicate: BSTD-021 — Dashboard gnucash totals incorrect (DOING)]

Title: {title}
Severity: {severity}
Area: {feature area}
Screenshot: {absolute path}
```

Options:
- **Create task** — go ahead as proposed
- **Edit title** — user will type a correction (use "Other" input)
- **Skip** — discard, don't create anything

If "Edit title" is chosen, use the corrected title and proceed.
If "Skip", stop.

### 6. Create the Asana task

```bash
python3 /media/data/dev/bain-studio/studio/sync.py \
  --create-task \
  --project {PREFIX} \
  --task-name "{title}" \
  --task-notes "Severity: {severity} | Area: {feature area}

{description}

Screenshot: {absolute path}" \
  --task-section "NEXT UP"
```

### 7. Confirm and get out of the way

Report one line:

```
Logged {LOCAL_ID} — {title}
```

Nothing else. The user is back to work.

---

## Notes

- Screenshots stay in `qa/qa-inbox/` — do not move them. The path in the task notes is the reference.
- Already-registered images (filename starts with `{PREFIX}-QA-`) are skipped — they've been through `/qa` already.
- If the screenshot is ambiguous (e.g. blank, or you can't tell what's wrong), say so and ask for a one-line description before proposing a title.
- This skill does NOT go through the qa-inbox pipeline. Use `/qa` for interactive QA sessions with review and sign-off.
