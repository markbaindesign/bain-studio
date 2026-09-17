---
tags: [utility, wordpress, fse, block-theme, playbook]
description: Studio playbook for building WordPress block themes - structure, the rules that keep a theme editable, and the theme.json and caching traps that fail silently.
---

# WordPress Block Themes - playbook

How the studio builds FSE block themes. Written from the Slipstream build
(`bain-theme-factory/themes/slipstream`), which is the reference implementation
for everything here.

Every trap in this document was found by **running** the theme, not by reading
it. That is the single most important line in the playbook: block themes fail
quietly. A wrong setting does not error, it just renders the default.

## Reference theme

Twenty Twenty-Five is the house reference, not the docs. Read the copy that
ships with the WordPress version you are targeting:

```
wp-content/themes/twentytwentyfive/
```

It is a **pure block theme, not hybrid**: the only PHP at the root is
`functions.php`. No `index.php`, no `header.php`, no `single.php`. If a theme
has those, it is a classic or hybrid theme and this playbook does not apply.

## Shape

```
theme.json              Tokens. The only place a value is defined.
style.css               Theme header + components. Unlayered.
assets/css/
  foundation.css        Reset, base, layout. Layered.
assets/fonts/           Self-hosted woff2, latin subset
styles/                 Style variations (palette swaps)
parts/                  header.html, footer.html - one line each
templates/              front-page, home, index, archive, search, single,
                        page, page-no-title, 404
patterns/               Every piece of copy lives here
functions.php           Enqueues, editor styles, block styles, categories
readme.txt              WordPress-format readme
screenshot.png          1200x900
```

`home.html` is the posts index, `index.html` the fallback. `front-page.html` is
optional - TT5 ships none - but the hierarchy uses it ahead of both, so it is
the right home for a designed landing page.

## The four rules

### 1. Templates and parts carry no copy

`parts/header.html` and `parts/footer.html` are **one line each**:

```html
<!-- wp:pattern {"slug":"theme/header"} /-->
```

The pattern carries the markup, in PHP, with every string in `esc_html_e()`.
Templates are pattern references and nothing else.

This is not tidiness. A pattern referenced from a template is **flattened into
real, editable blocks** the moment someone opens that template in the Site
Editor, so the copy stays editable there while the file keeps a clean default
for a fresh install. Confirmed by inspecting a user-saved `wp_template` post:
the pattern had been expanded inline with `metadata.patternName` preserved.

Give the header and footer patterns a `Block Types` header so the editor offers
them when replacing a part:

```php
 * Block Types: core/template-part/header
```

### 2. No `wp:html` in a pattern

A `wp:html` block is opaque in the editor. You cannot click into it, you cannot
swap an image through the media library, you cannot retype the copy. A pattern
that ships its content inside one is decoration, not a pattern.

| Need | Block |
|---|---|
| An image an editor can replace | `core/cover` (or `core/image`) |
| A link with a decorative mark | `core/paragraph` + CSS pseudo element |
| A list of links | `core/list` / `core/navigation` |
| A banner with a headline | `core/group` + `core/heading` |

**Decorative SVG goes in CSS, not markup.** Use a mask image painted with
`currentColor` so it still inherits colour like an inline SVG:

```css
--tick: url("data:image/svg+xml,%3Csvg...%3E");

.thing::after {
  content: "";
  background-color: currentColor;
  mask: var(--tick) no-repeat center / contain;
}
```

Multiple mask layers on one pseudo element will place several marks (four
corner crop marks from a single `::before`).

Justify any exception in the theme README. In Slipstream the only one is the
wordmark, which needs the same word four times in one element - no core block
expresses that - and it is `Inserter: no` and driven by `get_bloginfo('name')`.

### 3. Nothing user-facing is hardcoded

Anything that lives in Settings comes from a Settings block:

| Content | Block |
|---|---|
| Tagline | `core/site-tagline` |
| Site name | `core/site-title`, or `get_bloginfo('name')` in a PHP pattern |
| Logo | `core/site-logo` |
| Dates, titles, terms, excerpts | `core/post-*` |
| Copyright year | PHP pattern with `gmdate('Y')` |

A hardcoded tagline is the classic one, and it rots: in Slipstream the literal
copy in the header was still the reference site's tagline months after Settings
had been changed, and nothing surfaced the mismatch.

Everything else goes in a PHP pattern wrapped in `esc_html_e()`. Set
`Domain Path: /languages` in the theme header and create the directory.

### 4. No hex values in block markup

Use palette slugs, or the section ignores whichever style variation is active:

```html
<!-- wp:group {"backgroundColor":"blue"} -->
<div class="wp-block-group has-blue-background-color has-background">
```

Every style variation must declare the **same slugs** as `theme.json`. A
variation is a palette swap; if it drops a slug, anything using it breaks.

## theme.json traps

### A custom spacing scale is ignored unless you disable the default one

Setting `settings.spacing.spacingSizes` is not enough, and neither is adding
`spacingScale: { steps: 0 }`. WordPress keeps its own generated scale under the
`default` origin alongside yours under `theme`, and **the default wins on the
shared slugs 20-70**. Meanwhile `WP_Theme_JSON_Resolver::get_theme_data()`
reports your values back correctly, so the resolver lies to you.

```json
"spacing": {
  "defaultSpacingSizes": false,
  "spacingScale": { "steps": 0 },
  "spacingSizes": [ ... ]
}
```

Verify against the **served page**, never the resolver:

```bash
curl -s <site> | grep -o -- "--wp--preset--spacing--40: [^;]*"
```

The same pattern applies to `defaultPalette`, `defaultGradients`,
`defaultDuotone`.

### A saved style variation replaces the theme palette wholesale

Once someone picks a variation in the editor, WordPress writes the entire
palette into a `wp_global_styles` post. **Adding a new colour slug to
`theme.json` afterwards will not reach the site** - the saved palette wins and
the new custom property is simply absent, so anything referencing it falls back
to `inherit` or nothing.

Give new tokens a fallback so an existing site degrades rather than breaks:

```css
--red-text: var(--wp--preset--color--red-text, var(--wp--preset--color--red));
```

To genuinely pick up a new slug: reset styles in Appearance > Editor > Styles,
or update the saved post.

## Caching - the one that wastes an afternoon

**Theme pattern and template files are cached, and the front end can be badly
stale.** Symptom: a template part whose only content is a reference to a
not-yet-registered pattern renders as an **empty div**, with no error anywhere.
WP-CLI reports the new pattern as registered while web requests still see the
old list, because they are different processes hitting different caches.

While developing, always:

```php
define( 'WP_DEVELOPMENT_MODE', 'theme' );
```

Without it, `wp_get_theme()->delete_pattern_cache()` clears the cache for the
process that runs it and not necessarily for the next web request, and
`wp transient delete --all` does not reliably clear pattern headers either.

**Check the front end, not WP-CLI.** A quick instrument when something renders
empty - drop this in `wp-content/mu-plugins/` and curl the page:

```php
add_action( 'wp_footer', function () {
	$r = WP_Block_Patterns_Registry::get_instance()->get_all_registered();
	echo "\n<!-- patterns=" . count( $r ) . " -->\n";
}, 999 );
```

This is the same shape of problem as the **ACF Pro Local JSON trap** in
`/media/data/dev/CLAUDE.md`: a source file that looks authoritative while a
cached or default copy is what actually renders. Assume it, and verify through
the rendered output.

## CSS

### WordPress does not enqueue `style.css` for you

There is no such hook in core's `default-filters.php`, and Twenty Twenty-Five
enqueues its own. Do it explicitly, and use the dependency argument to fix load
order rather than hoping:

```php
wp_enqueue_style( 'theme-foundation', get_parent_theme_file_uri( 'assets/css/foundation.css' ), array(), $v );
wp_enqueue_style( 'theme-style', get_parent_theme_file_uri( 'style.css' ), array( 'theme-foundation' ), $v );
```

Add `wp_style_add_data( $handle, 'path', ... )` so core can optimise delivery,
and `add_editor_style()` with both files so the editor matches the front end.

### The layer contract

**Unlayered CSS beats every `@layer` rule regardless of specificity**, and
WordPress emits its global styles and core block styles unlayered. So:

- **Layer** reset, base and layout (`foundation.css`). None of it needs to beat
  core block CSS, and layering stops the reset ambushing everything else.
- **Do not layer** components (`style.css`). Anything in a layer loses to core
  block CSS no matter how specific it is. Use single-class selectors so plugin
  CSS stays overridable without `!important`.

### Containment: use WordPress's, do not rebuild it

The studio CSS foundation spec proposes a named-line grid so children are
contained by default and opt out. In a block theme WordPress already does that
job: `useRootPaddingAwareAlignments` puts the gutter on the root and lets
`.alignfull` break out. Set `contentSize`, `wideSize` and root padding in
`theme.json` and use `alignfull`. Ship only the escape hatch:

```css
.u-bleed { width: 100vw; margin-inline: calc(50% - 50vw); max-width: 100vw; }
```

### Two specificity pairs that bite

**Palette classes vs component backgrounds.** A cell that opts into a palette
colour must win, so wrap the component's default background in `:where()` to
zero its specificity:

```css
:where(.grid) > * { background: var(--paper); }   /* palette class can win */
.grid > *        { margin-block: 0; }             /* must NOT be :where() */
```

The margin reset must stay at normal specificity, because core's flow-layout
margin rule is **also** zero-specificity and would win on source order -
pushing every cell after the first down and exposing the container beneath.

**BEM class vs child selector.** `.block__el` (0,1,0) loses to `.block > span`
(0,1,1). Renaming a child to a BEM class silently lost a `position: relative`
in Slipstream and collapsed the masthead to zero height. Write
`.block > .block__el`.

### Hairline grids

Do not use per-cell borders - they fall apart when columns drop away. Use a 1px
gap over a coloured ground:

```css
.grid { display: grid; gap: 1px; background: var(--ink); border: 1px solid var(--ink); }
```

A four-up can then become two, then one, and every rule stays where it belongs.

## Contrast

Audit the palette before shipping, not after. Two findings worth generalising:

- **A "quiet" grey is almost always too light.** Slipstream's was 2.29:1 on
  paper where 4.5:1 is needed, and it carried dates, the colophon and captions.
- **A brand colour bright enough for a fill is rarely dark enough for text.**
  Carry **two values**: one for fills, where type on it is large display and
  3:1 applies, and a darker one for small links at 4.5:1. Expose both as
  `--accent` and `--accent-text` so a section's ink switches both together.

Large-text rules apply only to genuinely large type. Do not set small copy on a
band that passes at 3:1.

## Fonts

Self-host. Latin subset, woff2 only - Slipstream's five faces total ~68 KB.
Declare them in `theme.json` under `typography.fontFamilies[].fontFace` with
`file:./assets/fonts/...` paths.

Pull the exact subset URLs from the Google Fonts CSS API rather than
downloading the full family:

```bash
curl -s -A "<browser UA>" "https://fonts.googleapis.com/css2?family=Foo:wght@400&display=swap" \
  | awk '/latin \*\//{f=1} f && /src: url/{ match($0, /https:[^)]*/); print substr($0, RSTART, RLENGTH); exit }'
```

Ship the upstream `OFL.txt` alongside the files - the licence requires the
notice to travel with them. Confirm the licence from the `google/fonts`
repository metadata, not from memory, and check whether the family has been
renamed upstream.

## Verification before handover

Run all of it. None of these findings came from reading the code.

1. **Lint** - `php -l` on `functions.php` and every pattern.
2. **Parse** - every block comment balanced, every attribute valid JSON.
3. **Round-trip** - `serialize_blocks( parse_blocks( $content ) )` matches the
   source for every pattern. Catches markup the editor would flag as invalid.
4. **References resolve** - every `wp:pattern` slug declared, every
   `wp:template-part` file present, every colour/fontSize/spacing slug in
   `theme.json`, every font file on disk.
5. **Grep for regressions** - no hex in block markup, no `wp:html` outside
   documented exceptions, no literal copy in templates or parts.
6. **Install it** - copy into a throwaway ddev site, activate, seed content,
   set `WP_DEBUG` and `WP_DEBUG_LOG`, curl every route (home, page, single,
   search, 404), and confirm `debug.log` does not exist.
7. **Check served tokens** - `curl | grep -o -- "--wp--preset--..."` for
   anything you set in `theme.json`.
8. **Look at it** - headless screenshot at desktop and phone width.

A throwaway test site:

```bash
mkdir -p ~/dev/ddev/theme-test && cd $_
ddev config --project-name=theme-test --project-type=wordpress --docroot=. --php-version=8.3
ddev start && ddev wp core download && ddev wp core install --url=https://theme-test.ddev.site \
  --title="Theme Test" --admin_user=admin --admin_password=<generated> --admin_email=test@example.com --skip-email
ddev wp config set WP_DEVELOPMENT_MODE theme --type=constant
```

Note that snap-confined Chromium cannot write screenshots to arbitrary paths;
use `google-chrome --headless=new --screenshot=...` when scripting captures.

## Notes

- Hide core patterns on a bespoke theme:
  `remove_theme_support( 'core-block-patterns' )` on `after_setup_theme`. They
  bring rounded cards, gradients and shadows a strict design does not have.
- `register_block_style()` emits `is-style-{name}`. Style both that and any
  hand-authored class, or patterns and editor selections diverge.
- Use `core/navigation` rather than a bespoke menu. Its responsive overlay,
  keyboard handling and menu management are maintained; only the appearance is
  yours.
- Wrap functions in `if ( ! function_exists() ) : ... endif;` with `@since`
  docblocks, matching core themes, so a child theme can override.

## See also

- `bain-theme-factory/themes/slipstream/README.md` - reference implementation,
  with the same traps written against that theme's specifics
- `bain-theme-factory/css-foundation-spec.md` - the studio CSS foundation this
  maps onto
- `/media/data/dev/CLAUDE.md` - the ACF Pro Local JSON trap, same failure shape
- `docs/utilities/wp-pulse.md` - WordPress dev blog digest
