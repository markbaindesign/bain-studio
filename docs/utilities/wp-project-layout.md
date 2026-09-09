# WordPress project layout and .gitignore

The standard directory layout and ignore rules for every WordPress client
project, VVV and DDEV alike. Written up 2026-09-09 after two DDEV projects
(ebiz-global, techstyle) drifted off it.

## Layout

The WordPress install lives in `public_html/`. **This is the same for DDEV as
for VVV** - DDEV's default of serving from the repo root is not the studio
standard and should be overridden.

```
project-root/
├── .ddev/          or provision/   (DDEV / VVV)
├── .claude/
├── bin/            working folder, ignored
├── context/        project context (perf, seo, specs)
├── docs/           developer docs, findings, manifests
├── export/         working folder, ignored
├── import/         working folder, ignored
├── qa/             QA inbox and screenshots, ignored
├── scripts/        project scripts, tracked
├── public_html/    ← the docroot: WordPress core, wp-content, wp-config.php
├── CLAUDE.md
└── .gitignore
```

DDEV projects must set this explicitly in `.ddev/config.yaml`:

```yaml
docroot: public_html
```

### Why the docroot is never the repo root

On a rescue or an inherited site, the live server's docroot usually holds junk -
`info.php`, `test.html`, `index.php.old`, abandoned installs, host parking
assets. If the docroot is the repo root, all of that lands beside `CLAUDE.md`
and `docs/`, and the only way to keep the repo clean is a bespoke
deny-everything allowlist at the root. Putting the install in `public_html/`
contains the mess and lets the standard ignore rules below work unmodified.

## What is versioned

**Only code we write.** Third-party plugins, themes and WordPress core are
vendor code and are not tracked.

The pattern is three tiers, and the second is the one that gets missed:

1. Deny everything in `public_html/`, allow `wp-content/` back in.
2. Deny everything in `wp-content/`, allow `plugins/`, `themes/` and
   `mu-plugins/` back in.
3. **Deny the contents of each of those, then re-allow only our named custom
   plugin, theme or mu-plugin.**

Skip tier 3 and the entire vendor tree gets committed - on ebiz-global that was
16,133 files and 357MB, against 1 file of actual custom code.

```gitignore
# Ignore everything in the "public_html" directory except the "wp-content"
# directory.
public_html/*
!public_html/wp-content/

# Ignore everything in the "wp-content" directory, except the "plugins",
# "themes" and "mu-plugins" directories.
public_html/wp-content/*
!public_html/wp-content/plugins/
!public_html/wp-content/themes/
!public_html/wp-content/mu-plugins/

# Ignore everything in the "plugins" directory, except the plugins we maintain.
public_html/wp-content/plugins/*
!public_html/wp-content/plugins/<client>-custom/

# Ignore everything in the "mu-plugins" directory, except the mu-plugins we
# maintain.
public_html/wp-content/mu-plugins/*
!public_html/wp-content/mu-plugins/<client>-fixes.php

# Ignore everything in the "themes" directory, except the themes we maintain.
public_html/wp-content/themes/*
!public_html/wp-content/themes/<client>-theme/
```

Also never tracked:

- `wp-config.php` / `wp-config-ddev.php` - environment-specific and
  secret-bearing.
- `asana-mirror.md` / `asana-ids.json` - internal PM data, per
  [ADR 011](../adr/011-mirrors-at-project-root.md).
- Database dumps, archives and logs - `*.sql`, `*.zip`, `*.wpress`, `*.log`.

Working reference implementations: `vvv/clients/www/nore`,
`vvv/clients/www/khyentsefoundation`, `ddev/ebiz-global`.

## Replacing what ignoring vendor code loses

A WordPress site has no dependency manifest - nothing declares which plugin
versions are installed. Ignoring `plugins/` therefore loses that record unless
it is replaced. Keep a committed manifest at `docs/installed-versions.md`:

```bash
ddev wp plugin list --fields=name,status,version,update_version
ddev wp theme list  --fields=name,status,version,update_version
ddev wp core version
```

Regenerate it at each release.

On a rescue there is a second thing to preserve: some vendor code is genuinely
not reconstructable from upstream - unlicensed copies, or plugins the previous
developer edited in place. Keep the untouched as-found pull outside the repo
(ebiz-global's is `../ebiz-global-pull/htdocs`) and record its location in the
project's `CLAUDE.md`. That, not git, is the forensic baseline: hacked parent
themes are found by diffing against a clean upstream download, which needs no
version control at all.

## Known drift

- `ddev/techstyle` still uses `docroot: .` and the generic four-line
  `.gitignore`. Not yet corrected.
- `scaffold-dir` writes a generic `.gitignore` (`.env`, `node_modules/`,
  `__pycache__/`, `.DS_Store`) with no WordPress awareness, which is the root
  cause of the drift - every WP project hand-rolls its ignore rules from
  whatever was copied last. Teaching it this pattern is the durable fix.
