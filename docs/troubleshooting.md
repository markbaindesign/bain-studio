---
tags: [troubleshooting, studio]
description: Common studio tooling issues and their fixes
---

# Studio Troubleshooting

## Tasks missing from Asana after project setup

**Symptom:** You set up a new project and tasks you expected are not visible in Asana.

**Cause:** `sync.py` is pull-only — it reads from Asana into the local mirror. It does not create new Asana tasks from mirror edits. If tasks were written directly into the mirror file, they will never appear in Asana.

**Fix:** Create tasks via the Asana API first. Once they exist in Asana, the next sync will pull them into the mirror.

```bash
# Trigger a sync to confirm what's actually in Asana
python3 studio/sync.py
```

If tasks need to be seeded into a new project, use `/seed-tasks` or create them manually in Asana, then sync.
