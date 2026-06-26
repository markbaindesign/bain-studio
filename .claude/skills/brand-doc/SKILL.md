---
name: brand-doc
description: Convert a Markdown file to a Bain Design branded PDF using the brand-doc tool.
allowed-tools: [Bash]
---

# brand-doc

Runs the `brand-doc` CLI to generate a Bain Design branded PDF from a Markdown file.

## Input

The user provides a path to a `.md` file. They may also provide an output path. If not, the PDF is written alongside the input.

## Steps

1. Resolve the input path. If it is relative, resolve it from the user's current working directory.

2. Run the tool:

```bash
brand-doc /path/to/input.md [/path/to/output.pdf]
```

3. If the command succeeds, report the output path and open the PDF:

```bash
xdg-open /path/to/output.pdf
```

4. If the command fails, show the error output.

## Notes

- The tool lives at `/home/bain/bin/brand-doc` (on PATH).
- Source is at `studio/tools/brand-doc/brand_doc.py` in the bain-studio repo.
- See `studio/tools/brand-doc/README.md` for full documentation.
