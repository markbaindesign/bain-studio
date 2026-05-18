# bain-studio

Claude Code skills and studio sync tooling for freelance project management with Asana.

## Structure

- `studio/` — Asana sync script, project registry (`projects.md`, gitignored), credentials (`.env`, gitignored)
- `skills/` — Claude Code skills, loaded via `~/.claude/skills` symlink

## Setup

### 1. Clone and symlink skills

```bash
git clone https://github.com/YOUR_USERNAME/bain-studio ~/dev/bain-studio
ln -s ~/dev/bain-studio/skills ~/.claude/skills
```

### 2. Configure credentials

```bash
cp ~/dev/bain-studio/studio/.env.example ~/dev/bain-studio/studio/.env
# Edit .env and fill in your values
```

### 3. Install dependencies

```bash
cd ~/dev/bain-studio/studio
pip3 install -r requirements.txt
```

## Sync

Sync all projects discovered under `STUDIO_SCAN_ROOTS`:

```bash
python3 ~/dev/bain-studio/studio/sync.py
```

Sync a single project by prefix:

```bash
python3 ~/dev/bain-studio/studio/sync.py --project MCF
```

Preview without writing:

```bash
python3 ~/dev/bain-studio/studio/sync.py --dry-run
```

## How it works

The sync script scans directories for `CLAUDE.md` files containing `ASANA_PROJECT_GID`. For each project found, it fetches open tasks assigned to your Asana user and writes a mirror to `.claude/asana-mirror.md`. Tasks get a sequential local ID (e.g. `MCF-001`) stored in a custom Asana field.

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
| `default-perms` | Write default Claude Code permissions |
| `bootstrap-claude` | Bootstrap a new project |
| `log-project` | Log a completed project to portfolio CSV |
| `company-brief` | Research a company for interview/pitch prep |
| `grill-me` | Stress-test a plan through adversarial questioning |
| `wp-plugin-expert` | Document a WordPress plugin for Claude context |
| `wp-css-override` | Guide CSS overrides for WP plugins |
