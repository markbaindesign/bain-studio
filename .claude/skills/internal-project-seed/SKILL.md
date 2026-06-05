---
name: internal-project-seed
description: Interview Mark to capture an internal project idea and produce a structured brief + ready-to-run sync.py --create command. Use when Mark has a rough idea for an internal studio project and wants to kick off the studio workflow from claude.ai.
---

# Seed — Internal Project Intake

Turn a rough idea into a structured brief and a ready-to-run scaffold command.

This skill runs as a conversational interview. Ask one question at a time. Do not front-load all questions at once. Keep the tone light — this is brainstorming, not a formal brief.

---

## Interview

Ask these questions in order, one at a time. Wait for an answer before continuing. If an answer is vague, ask one short follow-up before moving on — don't get stuck.

**Q1 — Name**
"What are you calling this project? (Even a rough working title is fine.)"

**Q2 — Purpose**
"One sentence: what does it do or solve?"

**Q3 — Why now**
"What's prompting this? Is there a trigger, a pain point, or an opportunity?"

**Q4 — First version**
"If you had to ship something useful in a weekend, what would it be? Rough scope is fine."

**Q5 — Initial tasks**
"What are the first 3–5 things that need to happen? List them however they come to mind."

**Q6 — Housekeeping**
Suggest a prefix (2–4 uppercase chars from the project name, e.g. "Studio Dashboard" → `SD`) and ask Mark to confirm or change it.

Also ask: "Where should this project live locally? Give me a path, or just the parent directory and I'll suggest a folder name."

---

## Output

Once all answers are collected, produce two blocks:

### 1. Structured brief

```markdown
## Seed Brief — {slug} — {YYYY-MM-DD}

**Name:** {name}
**Prefix:** {PREFIX}
**Path:** {path}
**Purpose:** {one-line purpose}

### Why now
{trigger / motivation}

### First version
{scope summary}

### Initial tasks
- {task 1}
- {task 2}
- {task 3}
...
```

Save slug as: project name lowercased, spaces to hyphens (e.g. `studio-dashboard`).

### 2. Launch command

```bash
python3 /media/data/dev/bain-studio/studio/sync.py --create \
  --name "{name}" \
  --prefix {PREFIX} \
  --path {path}
```

Note: `--template` is optional — `sync.py` will use `ASANA_TEMPLATE_PROJECT_GID` from `.env` if set.

---

## Saving the brief

Save the brief to `{CONTENT_DIR}/specs/drafts/{slug}.md` in the bain-studio repo.

## Handoff

After saving, tell Mark:

> Brief saved to `{CONTENT_DIR}/specs/drafts/{slug}.md`.
> Run `/nurture {slug}` to flesh it into a full spec, then `/review-spec` to approve it.
> Once approved, `/commission {slug}` will scaffold the project, create the Asana project, and seed tasks.

---

## Notes

- If Mark already has a path in mind, use it verbatim. If not, suggest `~/code/internal/{slug}` as the default.
- Keep the whole interview to under 10 exchanges. If Mark is being expansive, that's fine — capture it but don't chase every thread.
- Do NOT run `sync.py --create` — that is now handled by `/commission`.
