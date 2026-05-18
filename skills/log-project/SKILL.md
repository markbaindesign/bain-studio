---
name: log-project
description: Elicit completed project data and append a new row to context/portfolio/project-database.csv. Use when Mark finishes a project or wants to backfill a missing project. Ask one section at a time, then write the CSV row and offer to run cv_updater.py.
---

# Log Project

Collect data for a completed project and append it to `context/portfolio/project-database.csv`.

## CSV columns to populate

| Column | Notes |
|--------|-------|
| Project Name | Short descriptive name (not the client name) |
| Client Name | Company or person |
| Year | Year completed (YYYY) |
| Client Industry | Comma-separated industry tags, e.g. "E-commerce, Fashion" |
| Project Description | 1–2 sentence summary of what was built and why |
| Excerpt | Short portfolio-facing description, e.g. "Build WordPress website from mockups" |
| Profile | One of: Unicorn / Coder/Builder / Consultant / Designer |
| Tech Stack | Comma-separated core technologies, e.g. "WordPress, PHP, JS, React" |
| Key Services | Comma-separated service types, e.g. "Custom Theme, Custom Plugin, UX/UI Design" |
| Key WP Plugins | Comma-separated WP plugins used (not core WP itself), e.g. "WooCommerce, ACF, Divi" |
| Upwork? | TRUE or FALSE |
| Key APIs | Comma-separated APIs, e.g. "Google Analytics, Algolia" |
| Tools & Libraries | Non-plugin tools, e.g. "Figma, GSAP, Grunt, Bitbucket" |
| Project URL | Live URL if public, else leave blank |
| Testimonials | Paste testimonial text if available, else leave blank |

## Interview steps

Work through these sections **one at a time**. Ask the questions, wait for the answers, then move to the next section. Do not ask all questions at once.

### Section 1 — Project basics
- What's the project called, and who was the client?
- What year did it complete?
- What industry is the client in?
- Was this an Upwork job?

### Section 2 — What was built
- Describe the project in a sentence or two — what was the brief, what did you deliver?
- How would you describe it for a portfolio excerpt? (e.g. "Build WordPress site from mockups", "UX/UI design + custom theme")
- What profile fits best? Unicorn (design + dev), Coder/Builder (dev only), Consultant, or Designer?

### Section 3 — Tech used
- What was the core tech stack? (WordPress, PHP, JS, React, Next.js, Astro, etc.)
- Which WordPress plugins were central to the project? (WooCommerce, ACF, Divi, LearnDash, etc.)
- Any key APIs or third-party services? (Algolia, Google Analytics, Auth0, etc.)
- Any tools or libraries worth noting? (Figma, GSAP, Bitbucket, Jira, Grunt, etc.)
- What were the key service types? (Custom Theme, Custom Plugin, UX/UI Design, LMS, etc.)

### Section 4 — Evidence
- Is there a live URL?
- Did the client leave a testimonial? (Paste it if so.)

## After collecting answers

1. **Show a preview** of the CSV row before writing — one field per line, clearly labelled. Ask Mark to confirm or correct anything.

2. **Write the row** — append to `context/portfolio/project-database.csv`. Match the column order exactly. Wrap any field containing a comma in double quotes. Do not quote fields that don't need it.

3. **Offer next steps:**
   - "Run `python pipeline/cv_updater.py --section all` to sync CV.md?" (recommended if this is a significant project)
   - "Generate a case study? Run `python pipeline/case_study_generator.py`"

## Rules

- Never invent or infer tech. Only log what Mark explicitly confirms.
- If a field is unknown or not applicable, leave it blank (empty cell, not "N/A").
- Profile values are fixed: Unicorn / Coder/Builder / Consultant / Designer — do not create new values.
- The CSV has no archive — append only, never edit existing rows.
- Keep excerpts short (under 10 words if possible) — they appear on the portfolio.
