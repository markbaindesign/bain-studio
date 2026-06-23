---
name: qa-capture
description: Quickly log a screenshot as an Asana task without breaking focus. Reads the image, proposes a title and severity, asks one confirmation question, creates the task. Use when you spot an issue mid-session and want to capture it without switching context.
allowed-tools: [Read, Bash]
---

# QA Capture

Log a screenshot as an Asana task in under 30 seconds. No QA pipeline, no review session — just capture and move on.

## Usage

```
/qa-capture qa/qa-inbox/screenshot.png
/qa-capture qa/qa-inbox/screenshot.png "optional extra context"
```

Screenshots are saved to `qa/qa-inbox/` in the current project. Drop the screenshot there, then invoke with the filename. Extra context is optional — use it to add detail that isn't visible in the image (e.g. "happens only on mobile", "introduced after the last deploy").

---

## Steps

### 1. Read the screenshot

Use the Read tool on the provided path. If the file does not exist, report that and stop.

### 2. Identify the project

Read `CLAUDE.md` in the current directory to get `ASANA_TASK_PREFIX` and `ASANA_PROJECT_NAME`.

If not in a project directory, ask: "Which project is this for?" and accept a prefix (e.g. `NORE`, `BSTD`, `KF-WEB`).

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

### 4. Confirm with the user

Present a single `AskUserQuestion` with the proposed task:

```
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

### 5. Create the Asana task

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

### 6. Confirm and get out of the way

Report one line:

```
Logged {LOCAL_ID} — {title}
```

Nothing else. The user is back to work.

---

## Notes

- Screenshot lives in `qa/qa-inbox/` — do not move it. The path in the task notes is the reference.
- If the screenshot is ambiguous (e.g. blank, or you can't tell what's wrong), say so and ask for a one-line description before proposing a title.
- This skill does NOT go through the qa-inbox pipeline. Use `/qa` for interactive QA sessions with review and sign-off.
