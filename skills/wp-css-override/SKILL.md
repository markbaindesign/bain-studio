---
name: wp-plugin-css-override
description: >
  Use this skill whenever working on CSS or Sass overrides for WordPress plugins
  inside a Divi child theme. Triggers include: styling a plugin (CF7, Estatik,
  Gravity Forms, WooCommerce, or any other), overriding Divi module styles,
  applying branded styles to third-party plugin output, fixing specificity
  conflicts, removing !important reliance, or building a scoped override
  stylesheet. Also use when the user says "style this plugin", "override plugin
  CSS", "brand this form", or "the plugin looks wrong". Always use this skill
  before writing any plugin override CSS — do not guess at selectors or file
  locations.
---

# WordPress Plugin CSS Override Skill

## Overview

This skill produces accurate, scoped, `!important`-free CSS overrides for
WordPress plugins in a Divi child theme environment. The key problem it solves:
AI cannot see the rendered DOM or computed cascade, so it must reconstruct
specificity context from source files and a captured HTML snapshot.

---

## Step 1 — Orient to the project

Before writing any CSS, read the following in order:

1. **Child theme stylesheet** — find it at `wp-content/themes/[child-theme]/style.css`
   or `assets/css/style.css` (path varies per project — check theme root first)
2. **Plugin source stylesheet** — typically at
   `wp-content/plugins/[plugin-slug]/assets/css/` or similar. Use `find` if unsure:
   ```bash
   find wp-content/plugins/[plugin-slug] -name "*.css" | head -20
   ```
3. **dev-notes/ folder in the theme root** — check for any existing snapshots or
   notes about this plugin:
   ```bash
   ls wp-content/themes/[child-theme]/dev-notes/
   ```
4. **Body class** — if not in dev-notes, ask the user to paste it, or find it in
   a PHP template:
   ```bash
   grep -r "body_class" wp-content/themes/[child-theme]/ --include="*.php"
   ```

**Brand scope class:** `bd324-branded` — all overrides must be scoped under this.

---

## Step 2 — Get the rendered HTML snapshot

Claude Code cannot see the browser DOM. A rendered HTML snapshot of the plugin
component is required for accurate selector targeting.

**Check dev-notes first:**
```bash
ls wp-content/themes/[child-theme]/dev-notes/
# Look for [plugin-slug]-rendered.html or similar
```

**If no snapshot exists**, ask the user to:
1. Load the page in a browser
2. DevTools → right-click the plugin's outermost wrapper element
3. Copy → Copy element
4. Save to `wp-content/themes/[child-theme]/dev-notes/[plugin-slug]-rendered.html`

Do not proceed to write overrides without either the snapshot or confirmation
from the user that they want a best-effort attempt from source CSS alone.

---

## Step 3 — Identify what's actually winning the cascade

With source CSS and rendered HTML in hand, identify:

- Which selectors the plugin uses (from source CSS)
- Which selectors Divi may be applying to inputs/forms (Divi normalises form
  elements heavily — check `wp-content/themes/Divi/style.css` or compiled output)
- Whether the plugin injects inline styles via PHP (grep for `style=` in rendered HTML)

```bash
# Quick check for inline styles in snapshot
grep -o 'style="[^"]*"' wp-content/themes/[child-theme]/dev-notes/[plugin-slug]-rendered.html
```

Inline styles require either a JS override or a structural workaround — flag
these to the user before writing CSS.

---

## Step 4 — Determine the output file

Ask the user or check for an existing override file structure. Common patterns:

```
# Pattern A — flat CSS
wp-content/themes/[child-theme]/css/[plugin-slug]-overrides.css

# Pattern B — Sass partials
wp-content/themes/[child-theme]/sass/overrides/_[plugin-slug].scss
wp-content/themes/[child-theme]/scss/overrides/_[plugin-slug].scss
wp-content/themes/[child-theme]/assets/css/overrides/_[plugin-slug].scss
```

Check whether a build step exists:
```bash
ls wp-content/themes/[child-theme]/
# Look for package.json, Gruntfile.js, gulpfile.js, webpack.config.js
```

If Sass is compiled, write `.scss`. If no build step, write plain `.css`.

If no override file exists yet, create it in the most logical location given the
existing structure. Always confirm path with the user before writing.

---

## Step 5 — Write the overrides

**Rules:**

- Scope everything under `body.bd324-branded .wpcf7` (or the plugin's wrapper class)
- No `!important` — use specificity only
- If `!important` is unavoidable (e.g. inline styles), add a comment:
  ```css
  /* !important required — plugin injects inline style via PHP */
  ```
- Group by element type with a comment header for each group
- Do not reset or override styles unrelated to the target design

**Specificity pattern (when Divi is fighting you):**

```css
/* One extra layer beats Divi's selectors in most cases */
body.bd324-branded .plugin-wrapper .element { }

/* For stubborn Divi form normalisation */
body.bd324-branded #page .plugin-wrapper input[type="text"] { }
```

**Output structure:**
```css
/* ==========================================================================
   [Plugin Name] Overrides
   Scoped under: body.bd324-branded
   Source snapshot: dev-notes/[plugin-slug]-rendered.html
   ========================================================================== */

/* Labels
   ========================================================================== */

/* Inputs
   ========================================================================== */

/* Textarea
   ========================================================================== */

/* Select
   ========================================================================== */

/* Submit button
   ========================================================================== */

/* Response / validation messages
   ========================================================================== */
```

---

## Step 6 — Enqueue the override file

Check how the child theme enqueues styles:
```bash
grep -n "wp_enqueue_style" wp-content/themes/[child-theme]/functions.php
```

Add enqueue using the `bd324_` prefix and include a docblock:

```php
/**
 * Enqueue [Plugin Name] override styles.
 *
 * @return void
 */
function bd324_enqueue_[plugin_slug]_overrides() {
    wp_enqueue_style(
        'bd324-[plugin-slug]-overrides',
        get_stylesheet_directory_uri() . '/[path/to/override.css]',
        array( 'bd324-main-style' ),
        wp_get_theme()->get( 'Version' )
    );
}
add_action( 'wp_enqueue_scripts', 'bd324_enqueue_[plugin_slug]_overrides' );
```

If the project uses a central enqueue function, add to it rather than creating
a new one. Check first:
```bash
grep -n "wp_enqueue_scripts" wp-content/themes/[child-theme]/functions.php
```

---

## Debugging aid

If the user reports styles still not applying after override, suggest adding this
temporarily to isolate what's winning:

```css
/* TEMP DEBUG — remove before commit */
body.bd324-branded .plugin-wrapper * {
    outline: 2px solid red !important;
}
```

Then in DevTools → Computed tab → filter by the property in question — the
winning rule and its source file will be visible.

---

## Plugin-specific notes

### Contact Form 7
- Wrapper class: `.wpcf7`
- CF7's own stylesheet is minimal — the real fight is usually Divi's form normalisation
- Submit button renders as `input[type="submit"]` not `<button>` — target accordingly
- Response messages: `.wpcf7-response-output`

### Estatik
- Check rendered HTML — Estatik class names are not always obvious from source
- Estatik uses `.estatik-wrapper` as outer scope in most versions
- Property listing grid: `.es-listings`, single listing: `.es-property`

### Gravity Forms
- Wrapper: `.gform_wrapper`
- Divi and GF both apply heavy form styles — expect specificity battles
- GF uses `ul/li` for field layout — don't assume `div` structure

---

## Notes on this skill

- **PHP version**: Do not add type hints to PHP unless the user confirms the version
- **Sass vs CSS**: Always check for a build step before choosing output format
- **No assumptions about assets path** — always check actual theme structure first
- **dev-notes/ is the handoff point** between browser inspection and Claude Code
