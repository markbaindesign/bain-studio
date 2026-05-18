---
name: wp-plugin-expert
description: >
  Use this skill when the user explicitly calls it by name ("use the wp-plugin-expert skill",
  "run wp-plugin-expert", "build a plugin expert for X"). This skill documents a WordPress
  plugin from scratch by: (1) fetching and consolidating all available public documentation
  into a single offline markdown file, (2) exploring the local codebase, and (3) generating
  both a README.md and a CLAUDE.md context file tuned for Claude Code. The output makes
  Claude a product expert on that plugin — able to answer dev questions, guide configuration,
  and support extension work without needing to re-read the source each time.
---

# WP Plugin Expert

Turns a poorly-documented WordPress plugin into a fully-documented, Claude-ready codebase.

## Outputs

All output goes into `plugin-docs/<plugin-slug>/` at the **project root** (the current working directory where the skill is invoked — not inside the plugin folder itself).

| File | Purpose |
|------|---------|
| `plugin-docs/<slug>/plugin-docs-offline.md` | Consolidated public docs (token-efficient, offline) |
| `plugin-docs/<slug>/README.md` | Human-readable plugin documentation |
| `plugin-docs/<slug>/CLAUDE.md` | Claude Code context file — the "product expert" |

Create the directory before writing: `mkdir -p plugin-docs/<slug>`

---

## Phase 1 — Gather Public Documentation

### 1.1 Identify sources

Ask the user for the plugin slug (e.g. `wp-all-import`) if not already provided.

Then fetch from all available sources in this order:

1. **wordpress.org** — `https://wordpress.org/plugins/<slug>/`
2. **wordpress.org FAQ** — `https://wordpress.org/plugins/<slug>/faq/`
3. **wordpress.org changelog** — `https://wordpress.org/plugins/<slug>/changelog/`
4. **GitHub** — search for `<slug> wordpress plugin` on GitHub; if found, fetch:
   - `README.md` / `README.txt`
   - `/wiki` pages if present
   - `/docs` folder if present
5. **Official website/docs** — check plugin header or wordpress.org sidebar for homepage URL; fetch key pages

### 1.2 Consolidate into offline file

Combine everything into a single `plugin-docs/<slug>/plugin-docs-offline.md` with clear section headers per source. Strip navigation chrome, ads, and boilerplate. Preserve:
- Feature descriptions
- Configuration options and their meanings
- Hook/filter documentation
- FAQ entries
- Changelog (last 5 versions only)
- Any code examples

Goal: one file, no network needed, minimal tokens.

---

## Phase 2 — Explore the Codebase

Ask user for the local plugin path if not already provided.

### 2.1 Map the structure

```bash
find /path/to/plugin -type f -name "*.php" | sort
```

Also check for: `package.json`, `composer.json`, `webpack.config.js`, `.env.example`

### 2.2 Read the plugin header

The main plugin file (same name as the folder, or contains `Plugin Name:`) reveals:
- Version, author, license
- Requires WP/PHP versions
- Text domain

### 2.3 Extract key patterns

Read through the codebase and identify:

**Hooks & Filters**
```bash
grep -rn "add_action\|add_filter\|do_action\|apply_filters" /path/to/plugin --include="*.php"
```

**Classes and structure**
```bash
grep -rn "^class " /path/to/plugin --include="*.php"
```

**Options / settings stored**
```bash
grep -rn "get_option\|update_option\|register_setting" /path/to/plugin --include="*.php"
```

**Database usage**
```bash
grep -rn "\$wpdb" /path/to/plugin --include="*.php"
```

**REST API endpoints**
```bash
grep -rn "register_rest_route" /path/to/plugin --include="*.php"
```

**Shortcodes**
```bash
grep -rn "add_shortcode" /path/to/plugin --include="*.php"
```

**Admin pages**
```bash
grep -rn "add_menu_page\|add_submenu_page" /path/to/plugin --include="*.php"
```

### 2.4 Identify extension points

Note anywhere the plugin is designed to be extended:
- Public hooks with clear naming
- Documented filter arguments
- Abstract classes or interfaces
- Template overrides

---

## Phase 3 — Generate README.md

Write `plugin-docs/<slug>/README.md` covering:

```markdown
# Plugin Name

> One-line description

## Requirements
## Installation
## Configuration
## Features
## Hooks & Filters (with arguments and examples)
## Shortcodes (if any)
## REST API (if any)
## Extending the Plugin
## Changelog (last 5 versions)
## License
```

Be specific. Include actual option names, hook names, and argument types found in the code — not generic placeholders.

---

## Phase 4 — Generate CLAUDE.md

This is the most important output. It turns Claude into a product expert for this plugin.

Write `plugin-docs/<slug>/CLAUDE.md` covering all of the following sections. Pull everything from the code and docs — no vague generalisations.

```markdown
# CLAUDE.md — [Plugin Name]

## What this plugin does
[2–3 sentence summary]

## Architecture overview
[How the plugin is structured: main class, loaders, admin/public split, etc.]

## File map
[Key files and what each one does — not every file, just the important ones]

## Key classes and their responsibilities

## Hooks & Filters reference
[Every add_action / add_filter found, with: hook name, callback, priority, accepted args]

## Filters available for extension
[Filters where external code can modify behaviour — include argument types]

## Configuration
[All get_option / register_setting calls — option names, default values, what they control]

## Database
[Any custom tables, $wpdb usage patterns]

## Admin UI
[Menu pages, settings pages, what lives where]

## REST API endpoints (if any)

## Shortcodes (if any)

## How to extend this plugin safely
[Recommended patterns: child theme overrides, hook priority, avoiding direct file edits]

## Common development tasks
[E.g. "To add a new setting: ...", "To hook into the import process: ..."]

## Known gotchas
[Anything non-obvious found in the code: version checks, conditionals, deprecated functions]

## Testing
[Any test suite found; if none, note it]
```

---

## Phase 5 — Deliver

Present all three files to the user:
1. `plugin-docs/<slug>/plugin-docs-offline.md`
2. `plugin-docs/<slug>/README.md`
3. `plugin-docs/<slug>/CLAUDE.md`

Confirm: "You can now load `plugin-docs/<slug>/CLAUDE.md` into any Claude Code session for this plugin and Claude will act as a product expert — able to answer config questions, guide extension work, and suggest safe patterns."

---

## Notes

- If the plugin has no public docs and no GitHub repo, skip Phase 1 and note it in the CLAUDE.md front matter.
- If the local codebase is not yet available, complete Phase 1 only and ask for the path.
- Prioritise accuracy over completeness — if a section has nothing to say, omit it rather than pad it.
- All generated WordPress function examples should use the project's prefix convention if known.
