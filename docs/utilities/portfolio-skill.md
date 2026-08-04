---
tags: [skill]
invoke: /portfolio
description: "Portfolio asset skill — screenshot, mockup, and capture sub-commands via CLI tools"
---

# /portfolio

Slash skill for capturing website screenshots and generating styled portfolio mockups. Wraps three CLI tools on PATH.

## Invoke

```
/portfolio screenshot URL [output.png] [--wait N] [--dismiss-cookies] [--full-page]
/portfolio mockup FILE [output.jpg]
/portfolio capture URL [output.png] [--dismiss-cookies] [--wait N]
/portfolio chrome [URL]
/portfolio from-browser FILE [--full-page]
```

## Sub-commands

| Sub-command | What it does |
|---|---|
| `screenshot` | Headless Playwright capture at 1320x857px |
| `mockup` | Frame an existing PNG in the portfolio mockup style |
| `capture` | Screenshot + mockup in one step (headless) |
| `chrome` | Open portfolio-chrome for sites with video/popups |
| `from-browser` | Capture from running portfolio-chrome + apply mockup |

## Workflows

**Simple sites:**
```bash
/portfolio capture https://example.com
```

**Video backgrounds or stubborn popups:**
```bash
/portfolio chrome https://example.com   # opens real Chrome
# dismiss overlays manually
/portfolio from-browser ~/Desktop/output.png
```

## Notes

- Skill lives at `~/.claude/skills/portfolio/SKILL.md`
- All tools are on PATH: `portfolio-screenshot`, `portfolio-mockup`, `portfolio-chrome`
- Requires Playwright (`pip install playwright && playwright install chromium`) for headless capture
- CDP mode (`from-browser`) requires portfolio-chrome to already be running on port 9222

## See also

- [[portfolio-mockup]] — KB doc covering the CLI tools in detail
