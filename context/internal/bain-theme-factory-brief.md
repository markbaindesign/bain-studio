# Seed Brief — bain-theme-factory — 2026-05-28

**Name:** Bain Theme Factory
**Prefix:** BTF
**Path:** ~/dev/bain-theme-factory
**Purpose:** Build a reproducible, standardized production line for WordPress themes. Takes design briefs as input, outputs submission-ready themes with consistent structure, quality, and documentation.

## Why now

Claude's agentic tooling enables orchestrated design-to-code workflows that were previously manual. This is the foundation for a larger studio automation architecture (Theme Factory → Plugin Factory → Repository Pipeline).

## First version

Two reference themes shipping as proof of concept: a Classic Theme (classic editor) and a Full Site Editing theme (FSE), both typography-forward and funky. Establishes the pipeline, tooling, and quality gates for future theme production.

## Initial tasks

- Set up project infrastructure: folders, Asana board, Claude integration, studio onboarding
- Define theme production pipeline: brief intake, design phase, code generation, testing, packaging
- Gather and curate design inspiration (revisit existing mood boards, source recent references)
- Sketch initial design direction for both theme variants
- Define typography system, component library, and submission checklist (WordPress dot org requirements)
- Build Claude workflow for theme scaffolding and code generation

## Launch command

```bash
python3 /media/data/dev/bain-studio/studio/sync.py --create \
  --name "Bain Theme Factory" \
  --prefix BTF \
  --path ~/dev/bain-theme-factory
```

## Next steps

Once the command runs, open a Claude Code session in `~/dev/bain-theme-factory` and run `/pm-todos` — paste the initial tasks above to seed them into Asana.

---

*Related projects to seed separately: Plugin Factory, WordPress Repository Pipeline.*
