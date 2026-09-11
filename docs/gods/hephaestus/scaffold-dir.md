---
description: Creates and initialises a new project directory as a git repo. Supports WordPress-aware structure with DDEV configuration.
god: hephaestus
invoke: /scaffold-dir
tags:
- skill
---

# scaffold-dir

Creates a new project directory, initialises git, and generates appropriate `.gitignore` and directory structure. For WordPress projects, creates the standard three-tier .gitignore pattern and public_html docroot structure.

It's a standalone step but is also called by `/commission` as part of the full project setup flow.

## Usage

```
/scaffold-dir <path> [name] [options]
```

### Arguments

- `path` — absolute path for the new project directory (required)
- `name` — optional display name, used in the initial commit message. Defaults to the directory basename.
- `--wordpress` — enable WordPress-aware structure with three-tier .gitignore and public_html docroot
- `--ddev` — set up DDEV configuration (sets docroot to public_html in .ddev/config.yaml)
- `--plugin NAME` — custom plugin name to allowlist (can be repeated, e.g. `--plugin acme-custom`)
- `--theme NAME` — custom theme name to allowlist (can be repeated)
- `--mu-plugin NAME` — custom mu-plugin to allowlist (can be repeated)

### Examples

**Non-WordPress project:**

```
/scaffold-dir /home/bain/code/projects/acme-site acme-site
```

**WordPress project with custom code:**

```
/scaffold-dir /home/bain/vvv/clients/www/acme acme --wordpress --plugin acme-custom --theme acme-theme
```

**WordPress DDEV project:**

```
/scaffold-dir /home/bain/ddev/acme acme --wordpress --ddev
```

## What it does

### All projects

1. **Validates** — aborts if the path is non-empty, or if the parent directory doesn't exist
2. **Creates** `{path}/`, `.claude/`, and `qa/` directories
3. **Git init**
4. **Writes** `.gitignore` tailored to the project type
5. **Initial commit** — `init: scaffold {name}`
6. **Creates a Shutter profile** — for the `{path}/qa/qa-inbox` directory

### WordPress projects (`--wordpress`)

Additionally:

- **Creates standard directories**: `bin/`, `export/`, `import/`, `scripts/`, `public_html/`
- **Writes WordPress-aware .gitignore** with three-tier deny/allow pattern:
  - **Tier 1**: Deny `public_html/*`, allow `wp-content/`
  - **Tier 2**: Deny `wp-content/*`, allow `plugins/`, `themes/`, `mu-plugins/`
  - **Tier 3**: Deny contents of each, re-allow only your named custom code
- **Creates allowlists** for custom plugins/themes/mu-plugins (uncommented if specified, commented placeholders otherwise)

### DDEV projects (`--ddev`)

Additionally:

- **Sets docroot** in `.ddev/config.yaml` to `public_html` (studio standard, not DDEV's repo-root default)

## The three-tier .gitignore pattern

The WordPress .gitignore prevents the entire vendor tree from being committed. Without the third tier, you risk committing hundreds of MB of third-party plugin/theme code.

**Example allowlist for Acme Corp:**

```gitignore
# Ignore everything in the "plugins" directory, except the plugins we maintain.
public_html/wp-content/plugins/*
!public_html/wp-content/plugins/acme-custom/

# Ignore everything in the "mu-plugins" directory, except the mu-plugins we maintain.
public_html/wp-content/mu-plugins/*
# !public_html/wp-content/mu-plugins/<client>-fixes.php

# Ignore everything in the "themes" directory, except the themes we maintain.
public_html/wp-content/themes/*
!public_html/wp-content/themes/acme-theme/
```

If you don't specify custom names, the script leaves commented placeholders for you to edit later.

## Output

**Non-WordPress:**

```
scaffold-dir: /home/bain/code/projects/acme-site
  ✓ directory created
  ✓ git init
  ✓ .gitignore written
  ✓ initial commit
  ✓ shutter profile 'acme-site' created
```

**WordPress:**

```
scaffold-dir: /home/bain/vvv/clients/www/acme
  ✓ directory created
  ✓ git init
  ✓ directories created (standard + WordPress)
  ✓ .gitignore written (WordPress-aware)
  ✓ DDEV config: created with docroot set to public_html
  ✓ initial commit
  ✓ shutter profile 'acme' created
```

## Shutter profile

The created profile points Shutter's save folder to `{path}/qa/qa-inbox` — screenshots land directly in the project's QA inbox. Launch Shutter for the project with:

```bash
shutter --profile='acme'
```

See [shutter.md](shutter.md) for full Shutter documentation.

## In the commission flow

`scaffold-dir` is step 2 of `/commission`, which also handles Asana project creation, studio registration, CLAUDE.md generation, and task seeding. Run `scaffold-dir` directly only when you need the directory without the full commission ceremony — e.g. internal tools, experiments, or projects not tracked in Asana.

When used with `/commission`, pass WordPress flags in the commission arguments and they will be forwarded to scaffold-dir.

## Reference

- **WordPress project layout standard**: `/media/data/dev/bain-studio/docs/utilities/wp-project-layout.md`
- **Example WordPress VVV project**: `/media/data/dev/vvv/clients/www/nore`
- **Example WordPress DDEV project**: `/media/data/dev/ddev/ebiz-global`

## Related

- [`/commission`](commission.md) — full project setup including Asana and studio registration
- [`/register-project`](register-project.md) — add an existing directory to the studio registry
- [shutter.md](shutter.md) — Shutter profile management

## Revision, 2026-09-11 — review fixes

BSTD-790's first pass was reviewed before merge and four defects were fixed:

1. **Nothing but `.gitignore` and `.ddev/config.yaml` was actually committed.** Every
   directory the script created was either empty or ignored, and git tracks neither - so a
   clone arrived with none of the layout. Fixed by writing a `.gitkeep` into every created
   directory and ignoring working folders by content (`bin/*` plus `!bin/.gitkeep`) rather
   than wholesale (`bin/`), which would have swallowed the marker too.
2. **`--ddev` without `--wordpress` produced a project DDEV could not start** - the config
   set `docroot: public_html` while the directory loop was gated on `--wordpress`, so the
   docroot did not exist. `public_html/` is now created whenever a DDEV config is written.
3. **Projects landed on `master` with no `develop`**, against studio git flow. HEAD is now
   repointed to `main` immediately after `git init` (git 2.25 has no `init -b`), and
   `develop` is branched after the initial commit.
4. **The DDEV config was a two-line stub.** It now spells out `name`, `type: wordpress`,
   `php_version` (new `--php` flag, default 8.2), `webserver_type` and the database block,
   rather than leaving them to DDEV's defaults to drift.

Also added per ADR 016: `context/`, `docs/`, `backups/`, `wp-cli.yml` and `README.md`, making
the skeleton the union of `wp-project-layout.md` and `wp-scaffold/PLAN.md`.

One environment finding surfaced during review: `wp-cli.yml` is listed in
`~/.gitignore_global` under a VVV heading, so it has never been tracked in any studio project
(`nore` and `buddhist-film-foundation` both have it on disk, untracked). Under DDEV it is a
project file that should be versioned. The script now warns when a file it wrote is ignored,
naming the gitignore and line, rather than force-adding over a deliberate user setting.
Removing that line from the global gitignore is a separate decision for Mark.

### Client stacks, 2026-09-11

Client projects inherit whatever their host runs, so PHP and database are now both flags:
`--php` (default 8.2) and `--db TYPE:VERSION` (default `mariadb:11.8`). DDEV does not
validate either at config time - it writes what it is given and the container fails later -
so `scaffold.py` checks their shape before creating anything.

The previous hardcoded `mariadb 10.11` came from `wp-scaffold/PLAN.md` and was already stale:
DDEV 1.25's own default is `mariadb:11.8`, which is what existing studio projects run.

WordPress's own version is not settable here - this script does not install WordPress. It is
recorded in `docs/installed-versions.md`, which the scaffold now seeds, pre-filled with the
target PHP and database. That manifest is required by `wp-project-layout.md` because the
.gitignore excludes `plugins/` and `themes/`, leaving no other record of what is installed.
