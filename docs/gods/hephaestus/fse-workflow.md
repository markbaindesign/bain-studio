---
description: WordPress FSE (Full Site Editing) development and deploy workflow — template sync, build, and SCP deploy pattern for block themes
god: hephaestus
tags:
- reference
- wordpress
- fse
- deploy
---

# WordPress FSE Development and Deploy Workflow

Applies to all studio projects using a WordPress block theme (FSE). Current projects: NORE, Alex Wright.

---

## The Core Problem

FSE sites have two sources of truth for templates and template parts:

1. **File-based** - `templates/*.html` and `parts/*.html` in the theme. Tracked in git.
2. **Database-based** - `wp_template` and `wp_template_part` posts saved by the Site Editor. These silently shadow the file-based templates without changing any files.

When you or a client edits a template in Appearance > Editor, WordPress saves the change to the DB. The file on disk is unchanged. The next time you deploy the file-based version, the DB override is overwritten and the editor change is lost.

**Rule: always capture DB overrides to files before committing or deploying.**

---

## Required Plugin: Create Block Theme

Install [Create Block Theme](https://wordpress.org/plugins/create-block-theme/) on every FSE project, both local and production. It provides an Export function that merges all DB template overrides back into the theme files and packages them as a ZIP.

Install via WP admin > Plugins > Add New. Official WordPress.org plugin, maintained by the Gutenberg team.

---

## Development Workflow

### Starting a session (local)

Before touching any code, capture any Site Editor changes made locally since the last commit:

```
/fse-sync
```

This skill exports DB template overrides to files, strips local domain URLs, and shows the diff. Review and commit if anything changed.

### After pulling production DB to local

When you pull a production DB snapshot, it may contain template overrides made on production. Run:

```
/fse-sync
```

Review the diff - anything intentional, commit. The skill handles domain stripping.

### Deploying

```
1. Pull production DB and capture any template overrides via /fse-sync
2. Make code changes, commit
3. ./build.sh         <- compiles Sass + JS + creates release ZIPs
4. SCP the release ZIP to production
5. SSH in, unzip into wp-content/themes/ (overwrites existing)
6. Repeat for plugin ZIP if plugin changed
```

The release ZIP always includes compiled CSS and JS (build.sh generates them before zipping). Do not deploy via git pull on the server - compiled outputs are gitignored.

### When the client edits the Site Editor on production

1. Pull production DB to local
2. Run /fse-sync to export DB overrides to theme files
3. Review diff, confirm changes are intentional
4. Commit, then proceed with your own work

---

## Two Export Methods

### Method 1: Create Block Theme plugin (recommended for full sync)

1. WP admin > Appearance > Create Block Theme
2. Click Export
3. Extract the downloaded ZIP
4. Copy templates/ and parts/ into your local theme, overwriting
5. Run domain-stripping sed (or use /fse-sync which handles this)
6. Review diff, commit

Best for: capturing a complete snapshot including patterns or theme.json changes.

### Method 2: WP-CLI (used by /fse-sync skill)

```bash
# List DB overrides (run from VVV root for @alias, or via vagrant ssh)
wp post list --post_type=wp_template,wp_template_part \
  --fields=ID,post_name,post_type,post_modified \
  --orderby=modified --order=DESC

# Export a specific override
wp post get {ID} --field=post_content > templates/{post_name}.html
```

Best for: automation, spot-checks, projects where Create Block Theme is not installed.

---

## Domain Stripping

The Site Editor writes absolute URLs when saving on production. After exporting:

```bash
find templates/ parts/ -name "*.html" | xargs sed -i \
  's|https://yourdomain.com||g; s|http://yoursite.test||g'
```

External URLs (Mailchimp, third-party services) are not affected.

---

## FSE Template Status in WP Admin

Appearance > Editor > Templates (list view):

| Status | Meaning |
|---|---|
| Active | File-based template in use. No DB override. |
| Customised | DB override exists and shadows the file. Needs export. |

---

## What Stays in DB (Never Exported to Files)

Posts, pages, CPT content, ACF field values, site settings, user accounts, memberships. These flow down from production to local only. Never push DB content up.

---

## Skill Reference

| Skill | What it does |
|---|---|
| `/fse-sync` | Exports DB template overrides to files, strips domains, shows diff |

---

## Project Notes

### NORE

- WP-CLI: `cd /media/data/dev/vvv/clients && wp @nore ...`
- Production SSH: `ssh -p 65002 u597309227@82.29.158.75`
- Theme dir: `public_html/wp-content/themes/nore-theme/`
- Build: `./build.sh` from theme root
- Domains: `https://thenatureofrealestate.com` and `http://nore.test`

### Alex Wright

- WP-CLI: `cd /media/data/dev/vvv/clients && wp @alex-wright ...`
- Build: `grunt build` from project root
