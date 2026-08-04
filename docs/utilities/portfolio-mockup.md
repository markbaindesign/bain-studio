---
tags: [tool]
command: "portfolio-mockup <input.png> [output.jpg]"
description: Frames a raw website screenshot in a styled mockup — rounded corners, neutral background, consistent proportions
---

# portfolio-mockup

Wraps a raw PNG screenshot in a styled portfolio mockup: rounded corners, neutral dark background, and proportions matching Mark's existing portfolio template.

## Invoke

```bash
portfolio-mockup input.png                    # saves as input-mockup.jpg alongside source
portfolio-mockup input.png output.jpg         # explicit output path
```

`--mockup` flag on `portfolio-screenshot` runs this automatically after capture.

## What it does

- Auto-detects and crops browser chrome artefacts from any edge (brightness > 195, saturation < 8, variance < 6)
- Applies rounded corners using a paint-over mask (Pillow 7 compatible — no `rounded_rectangle`)
- Centers the screenshot on a fixed neutral background (RGB 65, 70, 74)
- Canvas proportions: width x 1.317, height x 1.364 — measured from the iSolarWorkx template
- Outputs JPEG at quality 95

## Related tools

### `portfolio-screenshot`

Captures a site at 1320x857px via Playwright (headless). Supports cookie/modal dismissal.

```bash
portfolio-screenshot https://example.com [output.png]
portfolio-screenshot https://example.com --dismiss-cookies --wait 3 --mockup
```

### `portfolio-chrome`

Launches a dedicated Chrome instance with `--remote-debugging-port=9222` (separate profile). Use for sites with video heroes or popups that headless can't dismiss.

```bash
portfolio-chrome https://example.com
# dismiss overlays manually in the browser
portfolio-screenshot --from-browser output.png --mockup
```

## Workflows

**Headless (most sites):**
```bash
portfolio-screenshot https://example.com --mockup
```

**CDP / real Chrome (video backgrounds, stubborn popups):**
```bash
portfolio-chrome https://example.com       # terminal 1
# wait for load, dismiss popups manually
portfolio-screenshot --from-browser ~/Desktop/output.png --mockup   # terminal 2
```

## Source

- `/media/data/dev/bain-studio/studio/tools/portfolio-mockup/portfolio_mockup.py`
- `/media/data/dev/bain-studio/studio/tools/portfolio-screenshot/portfolio_screenshot.py`
- `/home/bain/bin/portfolio-mockup`, `/home/bain/bin/portfolio-screenshot`, `/home/bain/bin/portfolio-chrome`
