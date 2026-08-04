# ADR 011 — Asana mirrors live at project root, not .claude/

Date: 2026-07-22
Status: Accepted

## Context

Claude Code hard-prompts on any Edit/Write to a `.claude/` directory ("sensitive file"),
and permission allowlists cannot bypass it. The studio-looper must edit the target mirror
on every task it works (Looper Status, Progress, Assignee), so a mirror inside `.claude/`
guaranteed at least one blocking permission dialog per task - fatal for unattended runs.
The looper's state file was already moved to `/tmp/studio-looper/` for the same reason;
the mirrors were the remaining `.claude/` write.

## Decision

`asana-mirror.md` and `asana-ids.json` live at the **project root** of every registered
project (and the looper queue dirs `studio/looper/`, `studio/looper-test/`). The mirror is
just a data file - nothing sensitive lives in it.

- `sync.py` `ProjectConfig.mirror_file` / `ids_file` now resolve to `{root}/asana-mirror.md`
  and `{root}/asana-ids.json`.
- All existing mirrors were migrated 2026-07-22; a symlink was left at each old
  `.claude/asana-mirror.md` / `.claude/asana-ids.json` path for backwards compatibility.
  New projects get no symlink - the root path is canonical.
- `.claude/attachments/` (written only by sync.py via Python, read-only for agents) stays
  where it is.

## Consequences

- Unattended looper runs no longer hit sensitive-path prompts when advancing tasks.
- Any skill or doc referencing the old path was updated in the same change; third-party
  or forgotten readers still work through the symlinks.
- Mirrors at repo root are more visible in client repos; add `asana-mirror.md` and
  `asana-ids.json` to a client repo's `.gitignore` if they should not be committed there.
