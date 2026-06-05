---
name: harvest
description: Generate the three harvest outputs for a completed project — case study, blog post, and testimonial request email. Run after delivery. Updates Mnemosyne harvest status. Enforces Law V.
---

# Harvest

Generate the three harvest outputs for a completed project and update Mnemosyne.

**Law V:** Every completed project yields a blog post, a case study, and a testimonial request. These are not optional.

## Steps

### 1. Identify the project

If invoked with a project name argument, use it. Otherwise read `{CONTENT_DIR}/portfolio/project-database.csv` and show the last 5 entries — ask which project to harvest.

### 2. Read the project record

Read the row from `/media/data/dev/misc/upwork-proposals/context/portfolio/project-database.csv` for the named project. Extract all fields.

Check current harvest status:
- If all three harvest fields (Case Study, Blog Post, Testimonial Status) are already `published`, report harvest is complete and ask if the user wants to regenerate anything.
- If some fields are done and some are not, note which are outstanding and continue with only those.

### 3. Gather context

Read the following if they exist:
- The project directory's `CLAUDE.md` — check CLAUDE.md's active projects table for the path
- The project directory's `TODO.md`

Do not invent details not present in the data or these files.

### 4. Generate the case study

Create `{CONTENT_DIR}/portfolio/harvest/{slug}/case-study.md`:

```
# {Project Name}
**Client:** {Client Name} · **Industry:** {Client Industry} · **Year:** {Year}
**Stack:** {Tech Stack}

## The Brief
{Project Description — expanded if context allows, otherwise verbatim}

## What We Delivered
{Key Services rendered as prose — not a bullet list}

## How We Worked
{One interesting technical or process decision from the project}

## The Outcome
{Outcome Grade framed as prose — what the result meant for the client}
{Testimonial excerpt if the Testimonials field is populated}

## What We Learned
{Lessons field, framed as insight for future projects}
```

Keep it under 500 words. Studio voice: specific, honest, no marketing language.

### 5. Generate the blog post

Create `{CONTENT_DIR}/portfolio/harvest/{slug}/blog-post.md`:

Rules:
- Pick **one** interesting thing: a technique used, a constraint overcome, a decision that worked. Not a summary.
- ~400 words.
- First person, direct, specific.
- Lead with what was interesting, not with background.
- End with a practical takeaway or an open question it raised.
- Title must be specific — not "How we built a website" but something like "Why we dropped Divi mid-project and what we used instead".

### 6. Draft the testimonial request email

If Testimonial Status is already `received` or `published`, skip this step and note it in the report.

Otherwise create `{CONTENT_DIR}/portfolio/harvest/{slug}/testimonial-request.md`:

```
Subject: {Project Name} — quick favour?

{First name},

{One sentence referencing what you built and when.}

{One sentence explaining what you're asking for — portfolio, Upwork profile, future clients.}

If you're happy to, a short paragraph (or even a few sentences) about what it was like to work together and what the project delivered would be brilliant. You can reply directly to this email.

Thanks,
Mark
```

Keep the body under 100 words. Specific to this project, not a template.

### 7. Update Mnemosyne

Edit `/media/data/dev/misc/upwork-proposals/context/portfolio/project-database.csv` — find the row by Project Name and update:
- **Case Study** → `draft` (if it was `none`)
- **Blog Post** → `draft` (if it was `none`)
- **Testimonial Status** → `requested` (if it was `none`) — never downgrade an existing status

Do not change any other fields.

### 8. Report

Output a summary:
- Files generated (with paths)
- Updated harvest status
- What to do next: review drafts, publish when ready, send the email

## Notes

- Never invent facts not present in the project record or context files.
- The blog post focuses on one thing — it is not a case study in narrative form.
- The testimonial request references this specific project — it is not a generic template.
- Slug: Project Name lowercased, spaces to hyphens, non-alphanumeric stripped.
- If the project row cannot be found in the CSV, stop and ask the user to run `/log-project` first.
