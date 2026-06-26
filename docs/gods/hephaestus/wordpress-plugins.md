---
description: Studio WordPress plugin knowledge base — common plugins, use cases, gotchas, and studio patterns
god: hephaestus
tags:
- reference
- wordpress
- plugins
---

# WordPress Plugin Knowledge Base

Plugins the studio regularly installs, configures, or extends. Each entry covers: what it does, when to use it, key config, and known gotchas.

For deep per-plugin, per-project docs, run `/wp-plugin-expert <slug>` to generate a full offline reference.

---

## Page Builders & Design

### Divi Builder (Elegant Themes)
- **What:** Visual drag-and-drop builder + opinionated theme. Two modes: Divi theme (standalone) or Divi plugin (use with any theme).
- **When to use:** Legacy client sites; never start new projects with it.
- **Gotcha:** Stores content as shortcodes in post_content — migrating away is painful. Child themes are required for any customisation. Updates can break custom CSS.
- **Studio pattern:** Use child theme only. Override via `et_pb_*` filters for programmatic changes. Avoid touching core Divi files.

### Elementor
- **What:** Visual builder with widget system and theme builder (Pro).
- **When to use:** Client explicitly requests it, or site already on it.
- **Gotcha:** Performance hit without optimisation. Dynamic CSS injected inline. JSON stored in postmeta — hard to version-control.
- **Studio pattern:** Keep custom CSS in `custom.css` not inline widgets. Use Elementor's custom code feature (Pro) for JS.

---

## Multilingual

### WPML (WP Multilingual Plugin)
- **What:** Full multilingual site management — string translation, page/post translation, media translation, Polylang alternative.
- **When to use:** KF, any site needing 3+ languages or complex RTL + LTR combos.
- **Key config:** Set default language first. Enable string translation for theme strings. Use `ICL_LANGUAGE_CODE` in PHP for conditional logic.
- **Key filters:** `wpml_translate_single_string`, `wpml_object_id` (translate post IDs), `wpml_current_language`.
- **Gotcha:** Queries must use `suppress_filters => false` to get translated results. WP_Query language filtering is automatic but can be bypassed accidentally. Menu translations need manual setup per language.
- **Studio pattern:** Always test queries in non-default languages. Use `wpml_object_id()` to translate post IDs before using them.

---

## E-Commerce

### WooCommerce
- **What:** Full e-commerce platform. Products, cart, checkout, orders, coupons, shipping.
- **When to use:** When client needs to sell physical or digital products online.
- **Key hooks:** `woocommerce_before_add_to_cart_button`, `woocommerce_checkout_fields`, `woocommerce_thankyou`, `woocommerce_payment_complete`.
- **Template overrides:** Copy template from `woocommerce/templates/` into `your-theme/woocommerce/`. WooCommerce respects child theme overrides.
- **Gotcha:** Blocks-based checkout (WooCommerce Blocks) is different from classic checkout — hooks don't work the same way. Ask client which they want before building customisations.
- **Studio pattern:** All customisations via hooks + template overrides in a child theme or custom plugin. Never edit WooCommerce core files.

---

## Membership & LMS

### MemberPress
- **What:** Membership plugin — access rules, subscription plans, payment gateways, content restriction.
- **When to use:** NORE, any site needing paid access control.
- **Key config:** Rules (what content to restrict), Memberships (plans + pricing), Groups (tiered access).
- **Key hooks:** `mepr-user-registered`, `mepr-event-transaction-completed`, `mepr_validate_form`.
- **Gotcha:** Access rules are evaluated top-to-bottom, first match wins. Rule order matters. Free memberships still require a "transaction" — use the offline payment gateway for testing.
- **Studio pattern:** Never restrict the login page or password reset page. Always test all access scenarios in an incognito window.

### LearnDash
- **What:** LMS — courses, lessons, quizzes, certificates, enrolment.
- **When to use:** GGSA, any site needing structured learning delivery.
- **Key config:** Course Access Mode (free, buy now, recurring, closed). Group Management for cohorts.
- **Key hooks:** `learndash_course_completed`, `learndash_quiz_completed`, `ld_before_lesson_quiz_info`.
- **WPGraphQL integration:** LearnDash has a WPGraphQL extension — needed for headless setups.
- **Gotcha:** LearnDash queries bypass standard WP_Query — use LD-specific functions (`ld_get_course_list()`, `learndash_user_get_course_progress()`). Course progress is stored in custom user meta, not post meta.
- **Studio pattern:** Use LearnDash Groups for multi-cohort sites. Set up a dedicated staging with sample users at each access level before client UAT.

---

## SEO

### Yoast SEO
- **What:** Meta titles, descriptions, XML sitemap, structured data (Schema.org), breadcrumbs.
- **When to use:** Almost every WP project by default.
- **Key config:** General > Features (enable/disable breadcrumbs, REST API). Search Appearance > Content Types (set per-type defaults).
- **Key filters:** `wpseo_title`, `wpseo_metadesc`, `wpseo_schema_graph_pieces` (add custom schema).
- **Gotcha:** Yoast doesn't output `Course` schema — use custom JSON-LD for LearnDash/MemberPress course pages. Breadcrumb function is `yoast_breadcrumb()`, not auto-injected unless theme supports it.
- **Studio pattern:** Disable Yoast on post types that shouldn't be indexed (e.g. `mepr-transaction`). Set redirect slugs carefully — Yoast's premium redirect manager conflicts with other redirect plugins.

---

## Search

### Algolia (WP Search with Algolia)
- **What:** Replace WP search with Algolia's hosted search-as-you-type.
- **When to use:** KF, MCF, Film English — sites where WP native search is inadequate.
- **Key config:** Settings > Algolia — App ID, Search API Key (public), Admin API Key (server-side only). Configure which post types to index.
- **Key filter:** `algolia_searchable_post_types`, `algolia_searchable_post_statuses`, `algolia_post_shared_attributes` (customise indexed fields).
- **Gotcha:** Algolia index IDs encode the environment — prod and staging indices must be kept separate. Re-indexing on large sites is slow; trigger via WP-CLI not the admin UI.
- **Studio pattern:** Keep the Admin API Key server-side only (never expose in JS). Use the Search-Only API Key in the frontend.

---

## Forms

### Gravity Forms
- **What:** Form builder with conditional logic, notifications, confirmations, payment integrations.
- **When to use:** Oxford TEFL, any site needing multi-step or conditional forms.
- **Key hooks:** `gform_pre_submission`, `gform_after_submission`, `gform_notification`.
- **Gotcha:** Form IDs are environment-specific — use `gform_get_form_id_by_title()` rather than hardcoding IDs in templates. Export/import forms when migrating.
- **Studio pattern:** Always use `gravity_form()` PHP function in templates rather than the `[gravityforms id="N"]` shortcode. Allows conditional rendering without shortcode parsing overhead.

---

## Developer / Infrastructure

### WPGraphQL
- **What:** Exposes WP data via GraphQL API. Foundation for headless WP setups.
- **When to use:** GGSA (headless React/Next.js). Any decoupled frontend.
- **Key extension points:** `register_graphql_field`, `register_graphql_object_type`. Each post type, taxonomy, and custom field needs explicit registration.
- **Gotcha:** WPGraphQL does not automatically expose ACF fields — requires WPGraphQL for ACF plugin. Same for LearnDash, MemberPress, WooCommerce.
- **Studio pattern:** Write custom resolvers in a `mu-plugins/` file so they survive plugin updates. Test queries in the GraphiQL IDE before wiring into the frontend.

### WP All Import / WP All Export
- **What:** Bulk import/export content from CSV, XML, Excel. Map columns to post fields, meta, taxonomies.
- **When to use:** Content migrations, bulk data loads.
- **Key config:** Use the XPath mapping UI for complex source formats. Enable the "Run Automatically" option for recurring imports via cron.
- **Gotcha:** On large imports (10k+ rows), increase `max_execution_time` and `memory_limit`. Use the WP-CLI command `wp wpallimport run` for background imports.

---

## Utility

### Advanced Custom Fields (ACF)
- **What:** Custom fields UI — repeaters, flexible content, relationship fields, option pages.
- **When to use:** Almost any custom theme that needs structured content beyond default post fields.
- **Key patterns:** Define field groups in PHP via `acf_add_local_field_group()` — keeps fields in version control. Or export JSON to `/acf-json/` directory for auto-sync.
- **Gotcha:** ACF Free vs ACF Pro — repeaters and flexible content require Pro. ACF Blocks (for Gutenberg) require Pro.
- **Studio pattern:** Always use `acf-json/` sync. Never rely on the database-stored field groups alone.

### WP Migrate DB / WP Migrate DB Pro
- **What:** Push/pull database between environments. Rewrites URLs in the process.
- **When to use:** Local ↔ staging ↔ production syncs.
- **Gotcha:** Pro required for media file sync. Serialised data is correctly handled but always verify after migration. Never push production over a client-accessible staging without clearing the "allow push" option immediately after.
- **Studio pattern:** Always pull (staging → local) rather than push in the first instance. Keep the Pro licence key in `studio/.env` not hardcoded.

### WPML String Translation
- **What:** Extension to WPML for translating strings that aren't in post content — theme strings, plugin strings, widget text.
- **When to use:** Whenever WPML is active and there are non-content strings to translate.
- **Gotcha:** Strings must be registered via `icl_register_string()` to appear in the translation UI. New strings from updated themes/plugins don't auto-appear — must scan for strings.

---

## Cookie Consent

### Real Cookie Banner / Borlabs Cookie / CookieYes
- **What:** GDPR/ePrivacy cookie consent management. Blocks scripts until consent given.
- **When to use:** Any site with tracking, analytics, or third-party scripts (EU audience).
- **Gotcha:** Cookie banner JS must load before any blocked scripts. On KF: changing the cookie settings menu item title breaks the modal trigger (data attribute set via `nav_menu_link_attributes` filter from the title). See KF-WEB-029.
- **Studio pattern:** Always test cookie banner with tracking scripts disabled in browser to confirm blocked scripts are actually blocked.

---

## Hosting-Specific

### WP Offload Media (Delicious Brains)
- **What:** Offload media uploads to S3/GCS/DO Spaces. Rewrites attachment URLs.
- **When to use:** High-traffic sites or when media library is too large for shared hosting.
- **Gotcha:** Once offloaded, disabling the plugin breaks all media URLs. Keep a local backup. Use the "Copy Files" option rather than "Remove Local Files" until fully confirmed.

---

## Studio Notes

- **Always install via WP-CLI** when possible: `wp plugin install slug --activate`
- **Update cadence:** Check for plugin updates before starting any session on a client site
- **Security:** Premium plugins should have valid licences — never use nulled versions
- **Testing pattern:** Always test on staging with a full production database clone before activating on production
- **Version pinning:** For critical plugins (WPML, MemberPress), note the exact version in the project CLAUDE.md so regressions are caught
