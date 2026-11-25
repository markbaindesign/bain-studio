# theme-sweep

Mechanical sweep for a WordPress.org theme review. Does the deterministic half of a
review so the reviewer spends their time on judgement instead of greps.

It reports **facts and candidates**. It never decides what is a finding.

## What it does

- Downloads the submitted zip from wordpress.org and installs it into the test site
- Restores a known-good content baseline between reviews, via a DDEV snapshot
- Activates the theme and crawls seven templates with `WP_DEBUG` on, then reports
  whatever landed in `debug.log`
- Runs Theme Check
- Parses the `style.css` header and checks every declared tag against something real
  in the theme (classic `add_theme_support` / `register_nav_menus`, or block
  `templates/`, `styles/`, `patterns/`, `theme.json`)
- Flags functions in the public namespace with no prefix, or a prefix that does not
  match the theme slug
- Checks text domain consistency across PHP and HTML
- Lists every remote host the theme references, flagging anything that is not the
  Google Fonts exception
- Pairs every `.min.css` / `.min.js` with its unminified original, and flags a file
  that is minified without saying so in its name. The required items ask for the
  original alongside the minified one, and a licence credit in the readme is not
  the same thing - a bundled Bootstrap can be credited correctly and still be
  missing its source
- Greps for destructive deletes, admin menus, onboarding notices, remote fetches and
  unguarded superglobals
- Reads `readme.txt` for stock-image sources, and reports the screenshot's dimensions
  against the 1200x900 / 4:3 limits
- Uploads a logo, sets it as the `custom_logo` theme mod and looks for it in the
  front-page markup. `add_theme_support( 'custom-logo' )` and the `custom-logo` tag
  only prove the Site Identity control exists; a theme can declare both, pass Theme
  Check, carry the tag and still print a hardcoded image from its own folder on every
  install. The report also says whether the site's own name reaches visible text, or
  only an `alt` attribute

It writes `reviews/<slug>-<version>-sweep.md` in the project.

## What it does not do

Rendering, beyond the two things above. Every review still needs a person to open the
site and look at it. The
report ends with the list of what only a human catches: long titles at narrow widths,
keyboard focus order and modal focus traps, the screenshot against the real render,
and each bundled image's licence.

A sweep that finds nothing is not a pass.

## The review template

`review-template.md` is the house format the reports feed into: what a full and a
partial review are, the rules that decide which Trac status a review closes at,
the shape of the internal notes, the Trac comment skeletons and the handover page
as the last step. The review install reads it through a symlink, so edit it here
and the review follows once it is deployed.

The symlink and the sweep command point into the **ops worktree**
(`/home/bain/ops/bain-studio`, ADR 014), never this dev checkout: a review must not
read whatever branch happens to be checked out here. A template change therefore
reaches reviews when it is released and deployed with `studio/scripts/ops-deploy.sh`.

The sweep is the mechanical half; the template is the judgement half. Neither is
much use without the other.

## Rendering and keyboard - `cdp/cdp_check.py`

```bash
python3 -I cdp/cdp_check.py https://<site> <slug> / /sample-page/ --long-title \
  --json <reports>/evidence/<slug>-<version>-cdp.json
```

Headless Chromium over the DevTools protocol, at 390 and 1440 by default. For every
page: overflow, a whole-page keyboard pass (Tab to the end, Shift+Tab back) and the
open-menu keyboard pass. `--long-title` repeats the lot with a long site title and
restores the real one, through `ddev wp` in `--project` (default the current
directory). `--json` is the input for the review gate. It needs `chromium-browser`
and the `websocket` package (`python3-websocket`).

## Requirements

A DDEV WordPress project with the theme unit test data imported, and the `theme-check`
plugin active. `WP_DEBUG` and `WP_DEBUG_LOG` need to be on - DDEV sets `WP_DEBUG` for
you, so only `WP_DEBUG_LOG` has to go in `wp-config.php`.

## Usage

Run from the project root, or pass `--project`.

```bash
# one-time, with the unit test data imported and a default theme active
theme-sweep.py baseline

# review a theme end to end
theme-sweep.py run example-theme 1.0.1

# or step by step
theme-sweep.py fetch example-theme 1.0.1
theme-sweep.py reset
theme-sweep.py check example-theme

# put the content back after a theme has chewed on it
theme-sweep.py reset

# a theme that is not on wordpress.org yet (the studio's own, before submission)
theme-sweep.py run-local ~/builds/example-theme.zip
theme-sweep.py install-zip ~/builds/example-theme.zip --version 1.0.0   # install only
```

`install-zip` copies a local zip into `review-zips/` as `<slug>.<version>.zip` and installs it
exactly as `fetch` installs a download. The slug is the zip's one top-level folder; the
version comes from that folder's `style.css` unless `--version` is given. `run-local` is
`install-zip`, `reset`, then `check`, as `run` is for a submitted version. Review it with
`review-gate.py --pre-submission` (see the review template): there is no Trac ticket yet, so
the gate marks the sign-off and posting row, and the comment row when there is no comment
file, n/a and says "ready to submit".

`reset` matters more than it looks. Some themes ship an importer that force-deletes
every post and attachment on the site, so one click can cost you the unit test data.

`check` now writes to the site as well as reading it: the custom-logo test imports an
attachment and sets a theme mod. It removes both afterwards, including on failure, but
`reset` is there if a run is interrupted partway.

## Licence checks

The handbook's Pexels entry was corrected on or before 2026-11-10 and now matches what
the site does, so the report and the handbook agree. It reads: only photos under the
CC0 licence, not the Pexels License; on the photo page follow the "Free" link next to
"License". The destination is what decides - `/creative-commons-images/` is CC0 and
usable, `/license/` (headline "Legal Simplicity") is the Pexels License and is not.
Only CC0, CC BY 4.0 and CC-BY-SA 4.0 are accepted for images.

Until then the handbook told you to click a "free to use" link that Pexels had renamed,
which a review turned up and reported to the Themes team.
