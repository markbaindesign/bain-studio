# WordPress Plugin Repository Requirements

## Overview

Requirements for submitting and maintaining a theme or plugin in the official WordPress.org repositories.

## Plugin Repository (wordpress.org/plugins)

### Submission Process

- Submission via ZIP file upload at wordpress.org/plugins
- Manual human review by WordPress Plugin Team
- Review queue typically takes days to several weeks
- Upon approval, you receive SVN access for ongoing updates
- Version management via SVN for subsequent releases

### Code Quality & Security

- **License:** GPLv2 or GPLv2+ compatible license required for all code and assets
- **Code Obfuscation:** Prohibited - code must be human-readable
- **Complete Functionality:** Plugin must be fully working at submission (no trialware, no placeholders)
- **Input/Output Handling:** All user input must be sanitized, escaped, or use nonces (WordPress security best practices)
- **Dependencies:** Must use WordPress bundled libraries (jQuery, etc.) - do not include your own copies

### User Privacy & Tracking

- **User Tracking:** Only permitted with explicit opt-in consent from users
- **Permissions:** No unauthorized external links or credits injected into public site
- **Admin Interface:** Cannot hijack admin dashboard with spam, nags, or unwanted modifications

### Branding & Slugs

- **Slug:** Must be unique and respect WordPress trademarks
- **Branding:** Cannot infringe on existing WordPress or third-party trademarks

### Code Organization

- **Repository Slug:** The plugin folder name; must be lowercase, unique, and descriptive
- **README.txt:** Required with proper formatting, including stable tag
- **Version Increments:** Required with each release
- **File Structure:** Follow WordPress plugin directory conventions

### Important Note: Theme vs. Plugin Repository

A **theme cannot** be submitted to the WordPress **plugin** repository. Themes and plugins are separate directories with separate review teams and requirements:

- **Themes:** Submit to wordpress.org/themes
- **Plugins:** Submit to wordpress.org/plugins

If your goal is to ship theme-like presentation functionality via the plugin repository, the standard approach is to split responsibility:
- Presentation layer stays in a **Theme Directory** theme (can depend on your plugin)
- Functionality is shipped as a **Plugin** in the **Plugin Directory**

Both repositories enforce this "plugin territory" split from both sides - reviewers will not approve cross-category submissions.

---

## Theme Repository (wordpress.org/themes)

See separate document: `wordpress-theme-repository-requirements.md`
