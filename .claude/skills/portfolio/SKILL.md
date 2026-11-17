---
name: portfolio
description: "Portfolio asset tools: capture screenshots, generate styled mockups, or both."
allowed-tools: [Bash, Read]
---

# portfolio

Portfolio screenshot and mockup tools. All three CLI tools are on PATH.

## Sub-skills

| Invocation | What it does |
|---|---|
| `/portfolio screenshot URL` | Capture a headless screenshot at 1320x857px |
| `/portfolio mockup FILE` | Frame an existing PNG in the portfolio mockup style |
| `/portfolio capture URL` | Screenshot + mockup in one step (headless) |
| `/portfolio chrome URL` | Open portfolio-chrome for sites with video/popups |
| `/portfolio from-browser FILE` | Capture from running portfolio-chrome + mockup |

---

## /portfolio screenshot

Capture a website screenshot using headless Playwright.

```bash
portfolio-screenshot <URL> [output.png] [--wait N] [--dismiss-cookies] [--full-page]
```

- Default output: auto-named from the domain in the current directory
- `--wait N` — extra seconds to wait after load (default 2); increase for slow sites
- `--dismiss-cookies` — attempt to click cookie consent banners before capture
- `--full-page` — capture full scrollable height instead of viewport

**Steps:**
1. Parse the URL and optional output path from args
2. Run `portfolio-screenshot <URL> [output] [flags]`
3. Report the output path

---

## /portfolio mockup

Frame an existing PNG screenshot in the portfolio mockup style.

```bash
portfolio-mockup <input.png> [output.jpg]
```

- Output defaults to `{input-stem}-mockup.jpg` alongside the source file
- Automatically crops browser chrome artefacts from any edge
- Rounded corners, neutral dark background (RGB 65,70,74), consistent proportions

**Steps:**
1. Resolve the input path
2. Run `portfolio-mockup <input.png> [output.jpg]`
3. Report the output path

---

## /portfolio capture

Screenshot + mockup in one step (headless Playwright).

```bash
portfolio-screenshot <URL> [output.png] --mockup [--dismiss-cookies] [--wait N]
```

**Steps:**
1. Parse URL and optional output path from args
2. Run `portfolio-screenshot <URL> [output] --mockup [flags]`
3. Report both the PNG and the `-mockup.jpg` output paths

---

## /portfolio chrome

Launch the portfolio Chrome instance for sites that need a real browser (video hero, stubborn popups, login-gated pages).

```bash
portfolio-chrome [URL]
```

- Opens Chrome at 1320x900 with `--remote-debugging-port=9222`
- Uses a dedicated profile (`~/.config/portfolio-chrome-profile`) — does not reuse the user's main Chrome
- If a URL is given, it opens directly; otherwise Chrome opens to the new-tab page

**Steps:**
1. Run `portfolio-chrome [URL]`
2. Tell the user: "Chrome is open. Navigate to your page, dismiss any overlays, then run `/portfolio from-browser output.png`."
3. Do not wait — Chrome runs in background

---

## /portfolio from-browser

Capture whatever is showing in the running portfolio-chrome window, then apply the mockup.

Requires `portfolio-chrome` to already be running.

```bash
portfolio-screenshot --from-browser <output.png> [--mockup] [--full-page]
```

**Steps:**
1. Parse the output path from args (required — no auto-naming in CDP mode)
2. Run `portfolio-screenshot --from-browser <output.png> --mockup`
3. Report the `-mockup.jpg` output path

If Chrome is not running, the tool will print an error — tell the user to run `/portfolio chrome` first.

---

## Notes

- Source: `bain-studio/studio/tools/portfolio-mockup/` and `studio/tools/portfolio-screenshot/`
- Bins: `/home/bain/bin/portfolio-mockup`, `/home/bain/bin/portfolio-screenshot`, `/home/bain/bin/portfolio-chrome`
- KB doc: `docs/utilities/portfolio-mockup.md` in bain-studio
- Finished mockups for iSolarWorkx live in `/media/data/Dropbox/Work/Portfolio/isolarxworks/final/`
