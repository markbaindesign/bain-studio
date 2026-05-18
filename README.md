# bain-studio

Mark Bain's Claude Code tooling — studio sync scripts and skills.

## Structure

- `studio/` — Asana sync scripts, project registry (`projects.md`), credentials (`.env`, gitignored)
- `skills/` — Claude Code skills loaded via `~/.claude/skills` symlink

## Setup

```bash
ln -s ~/dev/bain-studio/studio ~/.claude/studio
ln -s ~/dev/bain-studio/skills ~/.claude/skills
```

## Sync

```bash
python3 ~/.claude/studio/sync.py --project {PREFIX}
```
