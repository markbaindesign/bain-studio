---
name: blooper-check
description: Scans a piece of writing for bloopers — typos, broken URLs, wrong names, formatting slips — and reports them as a list. Does NOT edit the file or suggest rewrites. Trigger phrases: "blooper check", "check for bloopers", "proofread this", "/blooper-check".
allowed-tools: [Read]
---

# blooper-check

Scans a piece of writing for bloopers — typos, broken URLs, wrong names, formatting slips — and reports them as a list. Does NOT edit the file or suggest rewrites.

## Invoke

```
/blooper-check [file path or "paste"]
```

If no argument is given, ask the user to paste the text or provide a file path.

## What to check

Go through the text and flag any of the following:

- **Typos** — misspelled words, repeated words, wrong word (there/their, its/it's, etc.)
- **Broken or malformed URLs** — e.g. `https://mark@bain.design` instead of `https://bain.design`, missing `https://`, URLs that are clearly wrong
- **Wrong names or details** — company name, role title, person's name spelled differently within the same document
- **Punctuation errors** — missing full stops, double spaces, unclosed brackets or quotes
- **Formatting slips** — markdown that was not stripped from plain-text output, stray asterisks, leftover template placeholders like `[Insert Name]`
- **Inconsistencies** — date format switching mid-document, inconsistent capitalisation of the same term
- **Missing content** — obvious blanks or incomplete sentences

## What NOT to do

- Do not suggest alternative wording
- Do not rewrite sentences
- Do not comment on style, tone, or structure
- Do not edit the file

## Output format

Report findings as a numbered list. Each item states:

- What the blooper is
- Where it appears (quote the relevant text, or give line/paragraph reference)
- What it should likely be (for factual errors only — skip this for style judgements)

If no bloopers are found, say so clearly.

Example output:

```
1. Broken URL — "https://mark@bain.design" should be "https://bain.design"
2. Typo — "publsihed" in paragraph 3, should be "published"
3. Repeated word — "I have have worked" in paragraph 4
4. Stray placeholder — "[Insert Portfolio Link]" left in closing paragraph
```

## Notes

- Read the file if a path is given; ask for paste if no path is given
- Check the entire document, not just the first paragraph
- Flag bloopers even if minor — the point is to catch everything before sending
- Complements `/copywriter` (voice/tone editing) — run both when a document really matters, since copywriter doesn't check for this class of mechanical error
