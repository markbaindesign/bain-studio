---
description: Post-project harvest — drafts blog post, case study, and testimonial
  request
god: hermes
invoke: /harvest
tags:
- skill
---

# Harvest

Generates the three harvest outputs for a completed project: a case study, a blog post, and a testimonial request email. Enforces Law V.

## Invoke

```
/harvest
/harvest {project name}
```

If no project name is given, reads `project-database.csv` and shows the last 5 entries to choose from.

## Law V

> Every completed project yields a blog post, a case study, and a testimonial request. These are not optional.

Abderus tracks compliance and flags gaps after 14 days. After 60 days, flags escalate.

## What it produces

### Case study

Saved to `{CONTENT_DIR}/portfolio/harvest/{slug}/case-study.md`:
- Client, industry, year
- Problem summary
- Approach (what was built and how)
- Outcome (metrics, client response, lessons)

### Blog post

Saved to `{CONTENT_DIR}/portfolio/harvest/{slug}/blog-post.md`:
- Angle: the most shareable/interesting aspect of the project
- Technical depth calibrated to the audience
- 400–700 words; punchy, specific, honest

### Testimonial request

Saved to `{CONTENT_DIR}/portfolio/harvest/{slug}/testimonial-request.md`:
- A short, warm email to the client
- Includes a specific prompt based on the project outcome
- Mark sends this himself; Harvest drafts it

## Harvest status tracking

Each project in `project-database.csv` has three harvest columns:
- `Case Study` — `none` / `draft` / `published`
- `Blog Post` — `none` / `draft` / `published`
- `Testimonial Status` — `none` / `requested` / `received` / `published`

Harvest updates these after generating each output. Abderus reads them.

## Notes

- Harvest skips any output already marked `published` unless Mark explicitly asks to regenerate it
- Harvest reads the project directory's `CLAUDE.md` and `TODO.md` for context — the richer those files, the better the outputs
- Do not invent details not present in the project record or files

## See also

- [abderus.md](abderus.md) — surfaces harvest gaps and testimonial follow-ups
- [iris.md](iris.md) — social media broadcasting triggered at project close
