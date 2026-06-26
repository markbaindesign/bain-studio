---
tags: [tool, skill]
god: aphrodite
command: brand-doc <file.md>
invoke: /brand-doc
description: Converts a Markdown file to a Bain Design branded PDF — cover page or one-pager mode
---

# brand-doc

Converts any Markdown file to a Bain Design branded PDF. Available as both a CLI tool and a `/brand-doc` skill.

## Usage

```bash
brand-doc input.md                        # output alongside input
brand-doc input.md output.pdf             # explicit output path
brand-doc input.md --one-pager            # letterhead layout, no cover
brand-doc input.md output.pdf --one-pager
```

## Modes

### Default — cover page
Full-document layout. Clay left accent strip, `Bd` mark top-right, title and subtitle centred, date footer. Inner pages get a header (title + page number) and a footer (`bain.design`).

### `--one-pager`
Letterhead layout. Branded header on every page: title left, `Bd` mark right, clay rule below. No cover page. The H1 is suppressed — it's already in the header.

## Markdown support

H1–H6, paragraphs, unordered/ordered lists, blockquotes (clay left bar), fenced code blocks (dark background, clay strip), tables, horizontal rules, inline bold/italic/code.

## Brand mark

The `Bd` mark is drawn programmatically from the design system spec — ink square, JetBrains Mono Bold, paper text. No standalone image file exists.

## Source

`studio/tools/brand-doc/brand_doc.py` — symlinked to `/home/bain/bin/brand-doc` and `~/.claude/skills/brand-doc/`.

## Dependencies

```bash
pip install reportlab pillow markdown
```
