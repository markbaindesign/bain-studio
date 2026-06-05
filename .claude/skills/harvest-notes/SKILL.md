---
name: harvest-notes
description: Harvest tagged ideas from Obsidian daily notes. Extracts #project, #skill, #script items as spec stubs and #workflow, #biz-dev etc. into Ideas/ topic files. Run manually or check what the scheduled sweep found.
---

Run the Obsidian collector against unprocessed daily notes:

```
python3 studio/collectors/obsidian_collector.py
```

If the user passes `--all`, add that flag to reprocess all notes.
If the user passes `--dry-run`, add that flag to preview without writing.

After running, report:
- How many spec stubs were created and their names
- How many ideas were filed and to which topic files
- Any duplicates skipped

If new spec stubs were created, list them and ask if the user wants to open any for editing.
