---
name: scaffold-dir
description: Create a new project directory and initialise it as a git repo on main with a develop branch. Supports WordPress-aware structure with DDEV configuration. Args: path [name] [--wordpress] [--ddev] [--php VERSION] [--db TYPE:VERSION] [--wp-version X.Y.Z] [--admin-user NAME] [--plugin NAME] [--theme NAME] [--mu-plugin NAME]
allowed-tools: [Bash, Write]
---

# Scaffold Dir

Create a project directory and git repo at the given path. Optional WordPress support with DDEV configuration.

## Usage

```bash
/scaffold-dir <path> [name] [options]
```

## Arguments

- **path** (required): Absolute path for the new project directory
- **name** (optional): Project name, used in the initial commit message. Defaults to the directory basename.
- **--wordpress**: Enable WordPress-aware .gitignore with public_html structure and standard directories
- **--ddev**: Set up DDEV configuration (sets docroot to public_html, and creates it)
- **--php VERSION**: PHP version for the DDEV config. Defaults to `8.2`.
- **--db TYPE:VERSION**: Database for the DDEV config. Defaults to `mariadb:11.8`
  (DDEV's own default, and what existing studio projects run).

**Match the client's host on both.** A client project inherits whatever their host runs, and
scaffolding to studio defaults is how you get "works locally, breaks live". Legacy sites are
routinely on MySQL rather than MariaDB, and on older PHP:

```bash
/scaffold-dir /media/data/dev/ddev/oldclient oldclient \
    --wordpress --ddev --php 7.4 --db mysql:5.7
```

DDEV does **not** validate these at config time - it writes whatever it is given and the
container fails later - so the script checks their shape up front, before anything is
created. `--db mysql8.0` and `--php 8` are both rejected with a usable message.

- **--wp-version X.Y[.Z] | latest**: Pin WordPress core. Downloads it into `public_html/`
  with `--skip-content`, so the bundled themes and plugins do not arrive. Omit it and nothing
  is downloaded - which is right for a migration, where the client's own files are imported.

```bash
# a legacy site stuck on an old core
/scaffold-dir /media/data/dev/ddev/oldclient oldclient \
    --wordpress --ddev --php 7.4 --db mysql:5.7 --wp-version 6.4.3
```

Core is downloaded with local wp-cli, which needs no database and no running container. If
wp-cli is absent the step is skipped with a note rather than failing the scaffold. The pinned
version is also written into `docs/installed-versions.md`.

- **--admin-user NAME**: WordPress admin username written into `scripts/install-wp.sh`.
  Defaults to `bain_324`.

**No Akismet, no Hello Dolly, no default themes.** `--skip-content` means they are never
downloaded in the first place, so there is nothing to delete on the normal path. A sweep runs
anyway after download, so the guarantee is enforced rather than incidental - if the download
flags ever change, or core arrives by some other route, the result is still clean. The
generated install script repeats the removal after `wp core install`, which can bring them
back.

**A scaffolded site has no theme, and so renders nothing.** Core is downloaded with
`--skip-content` and `--theme NAME` only creates an empty allowlisted directory, so the front
end serves an empty page until a real theme is added and activated. This is expected until
the `--type` templates land (ADR 016); the install script warns about it explicitly.

**WordPress is not installed at scaffold time** - `wp core install` needs a running database,
so the containers have to be up first. The scaffold writes `scripts/install-wp.sh` instead,
with the admin user baked in, to be run once after `ddev start`:

```bash
ddev start          # or just run the script, it starts DDEV itself
./scripts/install-wp.sh
```

**No password is written into that script.** `wp core install` generates one and prints it
when `--admin_password` is omitted, which is the correct behaviour for a file that is
committed to git. Site title, admin email and URL are all overridable by environment variable.

Note that core is **not** committed - the `.gitignore` excludes everything under
`public_html/` except `wp-content/`, which is correct: core is vendor code. The pin lives in
the manifest, which is why that file matters.
- **--plugin NAME**: Custom plugin name to allowlist (e.g., `--plugin acme-custom`). Can be repeated.
- **--theme NAME**: Custom theme name to allowlist (e.g., `--theme acme-theme`). Can be repeated.
- **--mu-plugin NAME**: Custom mu-plugin to allowlist (e.g., `--mu-plugin acme-fixes.php`). Can be repeated.

## Examples

**Non-WordPress project:**

```bash
/scaffold-dir /home/user/new-site site-name
```

**WordPress project with custom plugin and theme:**

```bash
/scaffold-dir /home/user/projects/acme acme --wordpress --plugin acme-custom --theme acme-theme
```

**WordPress DDEV project:**

```bash
/scaffold-dir /home/user/ddev/acme acme --wordpress --ddev
```

## What gets created

### For all projects:

- `.claude/` directory (for project-specific Claude configuration)
- `qa/` directory (for QA inbox)
- `.gitignore` file tailored to the project type
- Initial git commit **on `main`**, then a `develop` branch checked out - the studio's
  git flow layout, so it never has to be fixed by hand afterwards
- A `.gitkeep` in every directory created. Git does not track empty directories, so without
  these a clone arrives with none of the layout.

### For WordPress projects (with `--wordpress`):

**Directory structure:**

```
project-root/
├── .ddev/          DDEV configuration (or provision/ for VVV)
├── .claude/        Claude Code configuration
├── backups/        local safety copies (contents ignored)
├── bin/            working folder (contents ignored)
├── context/        project context: perf, seo, specs (tracked)
├── docs/           developer docs and ADRs (tracked)
├── export/         working folder (contents ignored)
├── import/         working folder (contents ignored)
├── qa/             QA inbox (contents ignored)
├── scripts/        project scripts (tracked)
├── public_html/    docroot: WordPress core, wp-content, wp-config.php
├── README.md
├── wp-cli.yml      path: public_html
├── docs/installed-versions.md   seeded manifest, see below
└── .gitignore
```

The working folders are ignored **by content** (`bin/*`) rather than wholesale (`bin/`), with
`!bin/.gitkeep` re-allowing the marker. Ignoring the directory outright would swallow the
.gitkeep too and the layout would not survive a clone.

This layout follows `docs/utilities/wp-project-layout.md`, which is authoritative where it
and any other source disagree. See ADR 016.

**`docs/installed-versions.md`:** the .gitignore deliberately excludes `plugins/` and
`themes/`, which loses the record of what is actually installed. `wp-project-layout.md`
requires a committed manifest in its place, so the scaffold seeds one - pre-filled with the
target PHP and database, and with the commands to regenerate it. Left uncreated it is simply
forgotten, and the repo ends up with no record of its own stack.

**A note on `wp-cli.yml`:** many setups carry a VVV-era `wp-cli.yml` entry in the global
gitignore, which silently prevents it being tracked. The script checks for this after writing
and reports a warning naming the offending gitignore and line - it does not force-add, since
that would override a deliberate user setting.

**.gitignore — three-tier pattern:**

The WordPress .gitignore uses a three-tier allow/deny pattern to ignore vendor code while tracking only custom code:

1. **Tier 1**: Deny `public_html/*`, allow only `wp-content/`
2. **Tier 2**: Deny `wp-content/*`, allow only `plugins/`, `themes/`, `mu-plugins/`
3. **Tier 3**: Deny contents of each, re-allow only your named custom code

This pattern prevents the entire vendor directory from being committed. Without it, you can accidentally commit 300,000+ files and hundreds of MB of vendor code.

**Allowlisted custom code:**

If you pass `--plugin acme-custom --theme acme-theme`, the .gitignore will have:

```gitignore
!public_html/wp-content/plugins/acme-custom/
!public_html/wp-content/themes/acme-theme/
```

Without arguments, commented placeholders are left for you to uncomment and customize:

```gitignore
# !public_html/wp-content/plugins/<client>-custom/
# !public_html/wp-content/themes/<client>-theme/
# !public_html/wp-content/mu-plugins/<client>-fixes.php
```

### For DDEV projects (with `--ddev`):

Sets `docroot: public_html` in `.ddev/config.yaml`. If the file doesn't exist, creates a minimal one.

This ensures the docroot matches the studio standard (public_html) rather than DDEV's default (repo root).

## What gets ignored

All WordPress projects ignore:

- **Secrets**: `.env`, `wp-config.php` (environment-specific)
- **Archives & backups**: `*.sql`, `*.zip`, `*.wpress` (database dumps, exports)
- **Logs**: `*.log` (runtime logs)
- **Dependencies**: `vendor/`, `node_modules/` (installed packages)
- **Project-internal**: `asana-mirror.md`, `asana-ids.json` (Asana task mirrors)
- **Working folders**: `bin/`, `export/`, `import/`, `qa/` (temporary working space)
- **Third-party code**: All of `public_html/wp-content/plugins/`, `themes/`, `mu-plugins/` except your named custom code

Generic projects ignore:

- Environment files: `.env`, `.env.local`
- Dependencies: `node_modules/`, `__pycache__/`, `*.pyc`
- OS junk: `.DS_Store`

## Reference

Studio WordPress project layout standard: `/media/data/dev/bain-studio/docs/utilities/wp-project-layout.md`

Example projects:
- VVV: `/media/data/dev/vvv/clients/www/nore`
- DDEV: `/media/data/dev/ddev/ebiz-global`

## Execution

This skill runs the `scaffold.py` Python script in the same directory, passing all arguments through. The script:

1. Validates paths and parent directory existence
2. Creates the directory structure (with or without WordPress tiers)
3. Generates the appropriate `.gitignore`
4. Initializes git with an initial commit
5. Sets up DDEV config if needed
6. Creates a Shutter profile (if available)
