---
name: issue
description: Report a QA issue for the current project. Assigns a reference number, creates a structured file in qa/qa-inbox/, and logs it. Invoke when you want to register a bug, visual problem, or QA item without running the full /qa workflow.
allowed-tools: [Bash, Read, Write]
---

# Issue — QA Issue Reporter

Registers a new QA issue for the current project. Assigns a reference number, writes a structured file to `qa/qa-inbox/`, and appends to `qa/qa-log.md`. Does not fix anything — just intake and registration.

Use `/qa` to work through issues once they are registered.

---

## Invoke

```
/issue
/issue broken contact form on mobile
```

If a description is passed inline, use it. Otherwise, ask.

---

## Steps

### 1. Scaffold check

Confirm `qa/` exists in the current project root. If not, stop and tell Mark to run `/qa` first to set up the QA structure.

### 2. Gather the issue details

If invoked with an inline description, use that as the starting point.

Ask for any missing fields using `AskUserQuestion`:

**Required:**
- **Description** — one line, plain English: what is broken or wrong
- **Severity** — `critical` / `high` / `medium` / `low`
- **Feature area** — what part of the site (e.g. "contact form", "mobile nav", "checkout", "homepage hero")
- **Type** — `description` (text only) / `image` (screenshot exists) / `bundle` (multiple files)

**Optional:**
- **Steps to reproduce** — if the issue is not obvious from the description
- **Expected behaviour** — what should happen
- **Actual behaviour** — what actually happens
- **Notes** — any extra context

If an inline description was provided, ask only for the fields that are still missing (severity and feature area at minimum).

### 3. Assign the reference number

Read `qa/qa-counter.json`:
```bash
cat qa/qa-counter.json
```

If the file doesn't exist, read `CLAUDE.md` for `ASANA_TASK_PREFIX`. Create the counter:
```json
{"prefix": "PREFIX", "next": 1}
```

Mint the ref: `{prefix}-QA-{next:03d}` (zero-padded, minimum 3 digits).
Increment `next` and write `qa-counter.json` back.

### 4. Write the issue file

Filename: `qa/qa-inbox/{ref}-{slug}.md`

Slug: lowercase, hyphens, max 6 words from the description.
Example: `NORE-QA-007-contact-form-broken-mobile.md`

File content:

```markdown
---
ref: {ref}
type: {type}
severity: {severity}
feature: {feature area}
opened: {YYYY-MM-DD}
---

## {description}

## Steps to reproduce

{steps, or "Not provided."}

## Expected

{expected, or "Not provided."}

## Actual

{actual, or "Not provided."}

## Notes

{notes, or "None."}
```

If type is `image` or `bundle`, add a note: "Attach screenshot(s) to this folder alongside this file."

### 5. Append to the log

Append one row to `qa/qa-log.md`:

```
| {ref} | {YYYY-MM-DD} | {description} | open | |
```

If `qa-log.md` doesn't exist, create it with the header first:
```
| ref | opened | description | status | closed |
|-----|--------|-------------|--------|--------|
```

### 6. Confirm

Report back:

```
{ref} registered — {description}
Severity: {severity} | Feature: {feature area}
File: qa/qa-inbox/{filename}

Run /qa to work through it.
```

---

## Notes

- `/issue` is intake only — it does not investigate or fix anything.
- If the issue is urgent (critical/high), mention it in the confirmation so Mark can prioritise.
- Images and bundles: the skill creates the markdown file; Mark drops the screenshot(s) into `qa/qa-inbox/` alongside it manually.
- Works in any project that has `qa/` set up. Run `/qa` first if the structure doesn't exist yet.
