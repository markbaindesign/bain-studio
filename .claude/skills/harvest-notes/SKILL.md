---
name: harvest-notes
description: Harvest tagged ideas from Obsidian daily notes. Extracts #project, #skill, #script items as spec stubs and #workflow, #biz-dev etc. into Ideas/ topic files. Records every tagged item (any #tag) as structured data. Archives processed daily notes into a processed/ subfolder. Run manually or check what the scheduled sweep found.
---

Run the Obsidian collector against unprocessed daily notes:

```
python3 studio/collectors/obsidian_collector.py
```

If the user passes `--all`, add that flag to reprocess all notes (including already-archived
ones in `processed/`).
If the user passes `--dry-run`, add that flag to preview without writing or moving files.

Side effects of a real (non-dry-run) run:
- Routes items to spec stubs / Ideas/ / feature backlog as before
- Records every extracted `#tag` (not just the routed ones) to
  `studio/collectors/obsidian_tagged_items.json` as structured data — one record per
  `{tag, text, date, source}`, deduplicated
- Moves each processed daily note into `processed/` inside the vault (lowercase — do not
  rename to `Processed/`, a differently-cased folder already exists from before this
  feature and collides on case-insensitive Dropbox sync)

After running, report:
- How many spec stubs were created and their names
- How many ideas were filed and to which topic files
- How many tagged items were recorded to the structured data file
- Any duplicates skipped

If new spec stubs were created, list them and ask if the user wants to open any for editing.
