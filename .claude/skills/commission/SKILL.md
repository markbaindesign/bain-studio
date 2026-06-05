---
name: commission
description: Commission a new project from an approved spec — scaffolds the directory, creates the Asana project, registers it in the studio, writes CLAUDE.md, and seeds initial tasks. The graduation ceremony. Args: spec name fragment, or path to spec file.
allowed-tools: [Read, Write, Edit, Bash]
---

# Commission

Turn an approved spec into a live studio project. Orchestrates all setup steps in sequence.

Arguments: $ARGUMENTS — spec name fragment or path to spec file.

---

## Step 1 — Load the spec

Find the spec:
- If args look like a path, read it directly
- Otherwise search `context/specs/candidates/` then `context/specs/drafts/` for a filename matching the fragment
- Read the spec fully

Extract these fields (ask if missing):
- **name** — project name (e.g. "Gestor Collector")
- **prefix** — 2–5 uppercase chars (e.g. `GCOL`) — suggest one from the name if not in spec
- **path** — local project path — suggest `~/code/internal/{slug}` if not in spec
- **description** — one-line purpose from the spec's Problem section

Confirm all four with the user before proceeding. Show:
```
Ready to commission:
  Name:    {name}
  Prefix:  {PREFIX}
  Path:    {path}
  Spec:    {spec filename}

Proceed? (y/n)
```

---

## Step 2 — Scaffold directory

Run `/scaffold-dir {path} "{name}"`.

---

## Step 3 — Create Asana project

Run:
```bash
cd /media/data/dev/bain-studio && python3 studio/sync.py --create \
  --name "{name}" \
  --prefix {PREFIX} \
  --path {path} \
  --yes
```

Capture the Asana project GID from the output — it will appear as `Project GID: {gid}` or similar.

---

## Step 4 — Bootstrap Claude

Change into the project directory and run `/bootstrap-claude {gid}` to link the Asana project and write `.claude/settings.json`.

---

## Step 5 — Init CLAUDE.md

Run `/init` in the project directory to generate a `CLAUDE.md` documenting the project.

---

## Step 6 — Register in studio

Run `/register-project {path} {PREFIX} "{name}"`.

---

## Step 7 — Seed tasks

Run `/seed-tasks {gid} --from-spec {spec_path}` to create the Phase tasks in Asana.

---

## Step 8 — Move spec to project

Move the spec file from its nursery location to `{path}/spec.md`.

---

## Step 9 — Commit the studio changes

In `/media/data/dev/bain-studio`, stage and commit:
```bash
git add CLAUDE.md studio/projects.json
git commit -m "commission: add {name} ({PREFIX})"
```

---

## Step 10 — Report

```
Commission complete — {name}

  Asana:    https://app.asana.com/0/{gid}
  Path:     {path}
  Prefix:   {PREFIX}
  Tasks:    {N} seeded

Next: open a Claude Code session in {path} and start building.
```

---

## Notes

- If any step fails, stop and report the failure. Do not skip ahead.
- `sync.py --create` can take up to 5 minutes (Asana duplication is async) — wait for it.
- If the spec is still in `drafts/` rather than `candidates/`, warn but proceed if the user confirms.
