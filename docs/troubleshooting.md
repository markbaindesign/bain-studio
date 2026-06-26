---
tags: [troubleshooting, studio]
description: Common studio tooling issues and their fixes
---

# Studio Troubleshooting

## Tasks exist in Asana but have no Local ID

**Symptom:** Tasks are visible in Asana but the Local ID custom field (e.g. `WTF-001`) is blank.

**Cause:** `--setup` was never run for the project, so `asana-ids.json` has `custom_field_gid: null` and sync can't write Local IDs back to Asana.

**Fix:** Run setup for the project, then sync:

```bash
python3 studio/sync.py --setup --project WTF
python3 studio/sync.py
```

Setup wires up the custom field GIDs; the following sync backfills Local IDs on all existing tasks.

## Tasks missing from Asana after project setup

**Symptom:** You set up a new project and tasks you expected are not visible in Asana.

**Cause:** `sync.py` is pull-only — it reads from Asana into the local mirror. It does not create new Asana tasks from mirror edits. If tasks were written directly into the mirror file, they will never appear in Asana.

**Fix:** Create tasks via the Asana API first. Once they exist in Asana, the next sync will pull them into the mirror.

```bash
python3 studio/sync.py
```

If tasks need to be seeded into a new project, use `/seed-tasks` or create them manually in Asana, then sync.
