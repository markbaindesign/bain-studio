# bain-studio

Claude Code skills and sync tooling for Asana-based studio project management.

## Structure

- `studio/` — Asana sync script, project registry (`projects.md`, gitignored), credentials (`.env`, gitignored)
- `skills/` — PM-specific Claude Code skills

## Setup

### 1. Clone

```bash
git clone https://github.com/markbain/bain-studio ~/dev/bain-studio
```

### 2. Symlink skills individually

```bash
mkdir -p ~/.claude/skills
for skill in ~/dev/bain-studio/skills/*/; do
  ln -s "$skill" ~/.claude/skills/"$(basename $skill)"
done
```

### 3. Configure credentials

```bash
cp ~/dev/bain-studio/studio/.env.example ~/dev/bain-studio/studio/.env
# Edit .env and fill in your values
```

### 4. Install dependencies

```bash
cd ~/dev/bain-studio/studio
pip3 install -r requirements.txt
```

## Sync

```bash
python3 ~/dev/bain-studio/studio/sync.py              # all projects
python3 ~/dev/bain-studio/studio/sync.py --project MCF  # one project
python3 ~/dev/bain-studio/studio/sync.py --dry-run      # preview
```

## How it works

Scans `STUDIO_SCAN_ROOTS` for `CLAUDE.md` files containing `ASANA_PROJECT_GID`. For each project, fetches open tasks assigned to your Asana user and writes a mirror to `.claude/asana-mirror.md`. Tasks get sequential local IDs (e.g. `MCF-001`) stored in a custom Asana field.

Add to a project's `CLAUDE.md`:

```
ASANA_PROJECT_GID: 1234567890
ASANA_TASK_PREFIX: MCF
ASANA_PROJECT_NAME: My Client Project
```

## Skills

| Skill | Description |
|-------|-------------|
| `asana-sync` | Sync current project's Asana tasks to local mirror |
| `pm-onboard` | Wire up a new project to the PM system |
| `project-todos` | Manage TODO.md and push tasks to Asana |
| `retro` | Run a session retrospective |

## Related

- [bain-skills](https://github.com/markbain/bain-skills) — generic Claude Code skills
