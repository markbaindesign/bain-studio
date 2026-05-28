# Seed Brief — wordpress-repo-pipeline — 2026-05-28

**Name:** WordPress Repository Pipeline
**Prefix:** WRP
**Path:** ~/dev/wordpress-repo-pipeline
**Purpose:** A shared SVN submission pipeline for deploying themes and plugins to the WordPress dot org repository — handling versioning, tagging, packaging, and submission in a reproducible, Claude-assisted workflow.

## Why now

Two existing plugins in the WordPress dot org repository need updating for WordPress 7.0 compatibility. This is the immediate trigger. The pipeline will also serve as the downstream destination for output from the Theme Factory and Plugin Factory projects.

## First version

Get the two existing plugins updated and resubmitted: bump "Tested up to" version, verify compatibility, add basic tests, and ship via SVN. Establishes the tooling and workflow for all future submissions.

## Initial tasks

- Identify the two existing plugins and audit their current state
- Set up SVN working copies locally for both plugins
- Bump "Tested up to" to WordPress 7.0 and verify nothing is broken
- Add basic tests where missing
- Define the standard SVN commit and tagging workflow for Claude-assisted submissions
- Document the pipeline so it can receive packaged output from Theme Factory and Plugin Factory

## Launch command

```bash
python3 /media/data/dev/bain-studio/studio/sync.py --create \
  --name "WordPress Repository Pipeline" \
  --prefix WRP \
  --path ~/dev/wordpress-repo-pipeline
```

## Next steps

Once the command runs, open a Claude Code session in `~/dev/wordpress-repo-pipeline` and run `/pm-todos` — paste the initial tasks above to seed them into Asana.

---

*Part of a broader factory architecture: Theme Factory → Plugin Factory → WordPress Repository Pipeline.*
