---
tags: [skill, utility]
invoke: /blooper-check
description: Scans a piece of writing for bloopers (typos, broken URLs, wrong names, stray placeholders) and reports them as a list — does not edit or rewrite.
---

# blooper-check

Reads a file or pasted text and reports any bloopers found. Covers typos, malformed URLs, wrong names, repeated words, unclosed punctuation, stray markdown, and leftover template placeholders.

## Invoke

```
/blooper-check [file path]
```

No argument — prompts for a paste or path.

## What it does

- Reads the full document
- Flags bloopers as a numbered list with a quote and suggested correction where applicable
- Does NOT edit the file or suggest rewrites — report only

## Notes

- Use before sending any externally-facing document (cover letters, proposals, emails)
- Catches broken URLs of the form `https://mark@bain.design` (email mixed into URL) — the type that slips through spellcheck
- Will not comment on style, tone, or structure
