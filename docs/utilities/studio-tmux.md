---
tags: [utility, terminal, tmux]
command: studio/scripts/studio-tmux
invoke: /open
description: Opens (or reattaches to) the studio tmux session, one window per studio area, each opening in that area's directory
---

# studio-tmux

One tmux session, `studio`, with a window per area of the studio: tooling, finance, biz dev, HR,
and whatever else is added later. Each window opens a shell in that area's directory. A window can
run a command instead, such as `claude`, and drops to a shell when it exits, so the window stays open.

```bash
studio-tmux                     # create the session if missing, add any configured windows it lacks, attach
studio-tmux --no-attach         # same, without attaching
studio-tmux open NORE ~/code/vvv/clients/www/nore claude   # add one window running claude, select it
studio-tmux open logs ~/logs                                # no command: a plain shell
```

Running `studio-tmux` again is safe: it reattaches, and adds back any configured window that has
been closed. Inside tmux it switches the current client rather than nesting a second attach.

`open` reuses a window that already has that name. When the session does not exist yet, `open`
creates it with the configured windows first; in a running session it never revives windows that
were closed on purpose. The [/open](../../.claude/skills/open/SKILL.md) skill calls `open` with a
project's prefix and path, and `claude` as the command.

## Config

The window list is local config, not code, so client paths stay out of this public repo:
`~/.config/bain-studio/tmux.json` (override with `--config` or `STUDIO_TMUX_CONFIG`).

```json
{
  "session": "studio",
  "windows": [
    {"name": "tooling", "dir": "/media/data/dev/bain-studio"},
    {"name": "finance", "dir": "/media/data/dev/bain-studio", "cmd": "claude"}
  ]
}
```

- `session` defaults to `studio`.
- `cmd` is optional. Without it the window is a plain shell.
- `dir` accepts `~`. A window whose directory does not exist is skipped with a warning.

To add an area, add a line to `windows` and run `studio-tmux` again. A starting point is
`studio/scripts/studio-tmux.example.json`.

## Notes

- Session and window targets use tmux's `=` exact-match prefix. Without it, a session called
  `studio` would also match `studio-old`.
- Tested on tmux 3.0a.
