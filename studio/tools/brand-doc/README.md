# brand-doc

Converts any Markdown file to a Bain Design branded PDF.

## Usage

```bash
brand-doc input.md [output.pdf]
```

If `output.pdf` is omitted, the file is written alongside the input with a `.pdf` extension.

The CLI wrapper lives at `/home/bain/bin/brand-doc`.

## What it produces

- **Cover page** — clay left accent strip, `Bd` mark (top right), document title, subtitle, date
- **Inner pages** — header with title + page number, footer with `bain.design`
- **Markdown support** — H1–H6, body paragraphs, unordered/ordered lists, blockquotes, fenced code blocks, tables, horizontal rules, inline bold/italic/code

## Brand mark

The `Bd` mark is drawn programmatically — it's a typographic CSS mark from the design system, not an image file. No logo asset exists as a standalone file.

## Fonts

Fonts live in `assets/fonts/`. All four are required for correct rendering:

| File | Used for |
|------|----------|
| `JetBrainsMono-Regular.ttf` | Body text |
| `JetBrainsMono-Medium.ttf` | Italic equivalent, H4/H5 |
| `JetBrainsMono-Bold.ttf` | Headings, bold inline |
| `IBMPlexMono-Regular.ttf` | Code blocks, inline code |

## Dependencies

```
pip install reportlab pillow markdown
```

## Brand tokens

Sourced from `/media/data/dev/bain/www/bain.design/design/design-system/colors_and_type.css`.

| Token | Value |
|-------|-------|
| Paper | `#E8DFCC` |
| Ink | `#141413` |
| Clay | `#C96442` |

## One-pager mode

For shorter documents that don't need a cover page:

```bash
brand-doc input.md --one-pager
brand-doc input.md output.pdf --one-pager
```

Produces a letterhead-style layout: `Bd` mark and document title in a branded header, clay rule below, no cover page. The H1 from the markdown is suppressed (it's already in the header).
