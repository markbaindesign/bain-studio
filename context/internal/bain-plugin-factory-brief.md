# Seed Brief — bain-plugin-factory — 2026-05-28

**Name:** Bain Plugin Factory
**Prefix:** BPF
**Path:** ~/dev/bain-plugin-factory
**Purpose:** A reproducible, standardized production line for WordPress plugins. Takes plugin specs as input, outputs tested, documented, submission-ready plugins with consistent structure and quality.

## Why now

Claude's agentic tooling enables orchestrated spec-to-code workflows that were previously too time-consuming. Mirrors the Bain Theme Factory approach and feeds into the shared WordPress Repository Pipeline for SVN submission.

## First version

Take one of the existing simple plugins and run it through the factory pipeline as a proof of concept: audit, refactor, add tests, document, and package it ready for the Repository Pipeline.

## Initial tasks

- Set up project infrastructure: folders, Asana board, Claude integration, studio onboarding
- Define plugin production pipeline: spec intake, scaffolding, code generation, testing, packaging
- Audit the existing simple plugin as the first factory run
- Define coding standards, prefix conventions, and docblock requirements
- Build Claude workflow for plugin scaffolding and code generation

## Launch command

```bash
python3 /media/data/dev/bain-studio/studio/sync.py --create \
  --name "Bain Plugin Factory" \
  --prefix BPF \
  --path ~/dev/bain-plugin-factory
```

## Next steps

Once the command runs, open a Claude Code session in `~/dev/bain-plugin-factory` and run `/pm-todos` — paste the initial tasks above to seed them into Asana.

---

*Part of a broader factory architecture: Theme Factory → Plugin Factory → WordPress Repository Pipeline.*
