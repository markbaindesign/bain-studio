---
description: Full commission workflow — kicks off a new project from brief to Asana
  setup
god: hermes
invoke: /commission
tags:
- skill
---

# commission

The full project setup ceremony — turns an approved spec into a live studio project. Orchestrates `scaffold-dir`, Asana, Claude bootstrap, studio registration, and task seeding in one flow.

## Usage

```
/commission <spec-name-fragment>
/commission <path/to/spec.md>
```

Pass a fragment of the spec filename or a direct path. The skill searches `specs/candidates/` then `specs/drafts/`.

## What it does

1. **Loads the spec** — extracts name, prefix, path, and description. Confirms all four with you before proceeding:
   ```
   Ready to commission:
     Name:    Acme Corp
     Prefix:  ACME
     Path:    /home/bain/code/internal/acme-corp
     Spec:    acme-corp.md
   Proceed? (y/n)
   ```

2. **Scaffolds the directory** — runs `/scaffold-dir`, creating the git repo, `.gitignore`, initial commit, and Shutter QA profile

3. **Creates the Asana project** — duplicates the studio template project via `sync.py --create` (can take up to 5 minutes)

4. **Bootstraps Claude** — runs `/bootstrap-claude {gid}` to link the Asana project and write `.claude/settings.json`

5. **Inits CLAUDE.md** — runs `/init` to generate project documentation

6. **Registers in studio** — runs `/register-project` to add to `projects.json` and the CLAUDE.md active projects table

7. **Seeds tasks** — runs `/seed-tasks` to create Phase tasks in Asana from the spec

8. **Moves the spec** — relocates `spec.md` to the project root

9. **Commits studio changes** — commits `CLAUDE.md` and `projects.json` to the bain-studio repo

## Output

```
Commission complete — Acme Corp

  Asana:    https://app.asana.com/0/{gid}
  Path:     /home/bain/code/internal/acme-corp
  Prefix:   ACME
  Tasks:    8 seeded

Next: open a Claude Code session in {path} and start building.
```

## Notes

- If any step fails, it stops and reports — it does not skip ahead
- Specs in `drafts/` rather than `candidates/` trigger a warning but proceed if confirmed
- After commission, open a Claude Code session in the project directory to start work

## Related

- [`scaffold-dir`](scaffold-dir.md) — directory setup step, can be run standalone
- [`register-project`](register-project.md) — studio registration step, can be run standalone
- [sync.md](sync.md) — the Asana sync engine used to create the project
