---
command: shutter <url>
description: Captures full-page screenshots of URLs for visual review and QA
god: aphrodite
tags:
- tool
---

# Shutter — Screen Capture

Shutter is the studio's screen capture tool, used primarily for QA workflows. Each client project gets its own Shutter profile pointing to that project's `qa/qa-inbox` folder.

## Profiles

Profiles store per-project settings (save folder, filename pattern). They live at `~/.shutter/profiles/{name}.xml`.

The studio has two standing profiles:

| Profile | Folder | Use |
|---|---|---|
| `default` | `~/Dropbox/Misc/Screen Captures` | General captures |
| `QA_Beato` | `.../beato-properties/qa/qa-inbox` | Beato QA |

New project profiles are created automatically by `scaffold-dir`.

### Filename pattern

`%Y-%m-%d-%T-%NNN` — ISO date + time + session sequence. Unique across sessions.

## shutter-profile CLI

`~/code/bain-studio/studio/scripts/shutter-profile` (symlinked to `~/.local/bin`)

```bash
shutter-profile list                                      # list all profiles
shutter-profile create <name> <folder> [--filename pat]  # create/overwrite
shutter-profile delete <name>                            # delete
shutter-profile launch <name>                            # open Shutter with profile
shutter-profile set-default <name>                       # set startup profile
```

`set-default` requires Shutter to be fully quit first (see gotchas below).

## scaffold-dir integration

`scaffold-dir` runs `shutter-profile create "{name}" "{path}/qa/qa-inbox"` as step 6, creating a profile for every new project automatically. The `qa/qa-inbox` directory is also created.

Launch Shutter for a project with:

```bash
shutter --profile='Client Name'
```

## Gotchas

**Closing the window doesn't quit Shutter.** `close_at_close` is enabled, so the X button hides Shutter to the system tray. Use **tray → Quit** to fully exit. This matters for `set-default` — if Shutter is still running in the tray, it will overwrite `settings.xml` on quit and undo the change.

**Apply before editing.** In Preferences, selecting a profile in the dropdown does not load it. You must click the **Apply (✓)** button first, then make changes. Otherwise your changes save to the previously loaded profile.

**`*` profile reappearing.** If Shutter quits while the `*` profile is active (because its profile combobox defaulted to `*`), it recreates `~/.shutter/profiles/*.xml`. Delete it with `shutter-profile delete "*"`.

## bsd_glob patch

Shutter 0.99.2 has a bug where `bsd_glob()` (used to scan the profiles directory on startup) returns the literal string `*.xml` instead of expanding it on some systems. Result: Shutter shows only one profile named `*` and never sees any saved profiles.

**Patch:** line 888 of `/usr/bin/shutter`, `bsd_glob(...)` → `glob(...)`.

Patch file: `studio/scripts/shutter-bsdglob.patch`

If a Shutter update overwrites the fix:

```bash
sudo patch /usr/bin/shutter < ~/code/bain-studio/studio/scripts/shutter-bsdglob.patch
```

Upstream issue: https://github.com/shutter-project/shutter/issues/820
