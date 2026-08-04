# WordPress Theme Repository Requirements

## Overview

Requirements for submitting and maintaining a theme in the official WordPress.org Theme Directory (wordpress.org/themes).

## Theme Repository (wordpress.org/themes)

### Submission Process

- Submission via ZIP file upload at wordpress.org/themes
- Automatic and manual review by WordPress Theme Review Team
- Themes are tested for functionality, security, code quality, and accessibility
- Upon approval, theme is listed in Theme Directory and receives automatic updates
- Ongoing updates via uploading new versions to WordPress.org

### License & Copyright

- **License:** GPLv2 or GPLv2+ compatible license required for all theme code
- **Assets:** Images, fonts, and other assets must be GPL-compatible or have clear attribution/licensing
- **Bundled Resources:** Third-party libraries must have compatible licenses and be properly attributed

### Code Quality & Security

- **Code Obfuscation:** Prohibited - all code must be human-readable
- **Security Prefixes:** All function and class names must use a theme-specific prefix (e.g., `mytheme_`) to avoid namespace collisions
- **Input/Output Handling:** All user input must be properly sanitized; all output must be escaped
- **Nonces:** Use WordPress nonces for form submissions
- **Dependencies:** Should use WordPress bundled libraries; external dependencies must be justified and properly managed

### Functionality Restrictions

- **Plugin Territory:** Themes should not include plugin-like functionality
- **No Admin Customization:** Cannot hijack the WordPress admin interface
- **No Database Modifications:** Should not make unauthorized changes to the database
- **No External Requests:** Avoid external HTTP requests; if necessary, they must be clearly disclosed and user-initiated

### Accessibility

- **Accessibility Ready Tag:** Themes can declare "Accessibility Ready" status with proper WCAG 2.1 compliance
- **Standards Compliance:** Must follow web accessibility standards
- **Screen Reader Support:** Proper semantic HTML and ARIA labels where needed
- **Keyboard Navigation:** All functionality must be keyboard accessible

### File Structure & Organization

- **Proper Structure:** Must follow WordPress theme directory structure conventions
  - `style.css` with proper header comment
  - `functions.php` for theme functions
  - `index.php` as fallback template
  - Proper template hierarchy (page.php, single.php, etc.)
- **CSS Organization:** CSS must be properly structured and valid
- **JavaScript:** Must be enqueued properly, not hard-coded in templates

### Customization

- **Customizer Support:** Should provide Customizer controls for theme settings
- **Theme Mods:** Use `get_theme_mod()` for user customizable options
- **No Database Bloat:** Avoid storing excessive data in options table

### Version Management

- **Version Increments:** Each update must increment the version number
- **Changelog:** Maintain clear changelog of updates
- **Compatibility:** Declare compatibility with current WordPress versions

### Coding Standards

- **WordPress Coding Standards:** Follow official WordPress coding standards
- **Comment Documentation:** Properly document code with inline comments and docblocks
- **Performance:** Optimize database queries, script loading, and rendering performance

---

## Important Notes

### Theme vs. Plugin Repository

- Themes go to **wordpress.org/themes**
- Plugins go to **wordpress.org/plugins**
- Do not confuse the two or submit to the wrong repository

### Theme + Plugin Architecture

If you need both theme-like presentation and plugin-like functionality:
- Create a **theme** in the Theme Directory for presentation
- Create a **plugin** in the Plugin Directory for functionality
- Your theme can declare the plugin as a dependency or recommendation
- This separation allows for independent updates and clearer responsibility

### Updates & Support

- Themes receive automatic updates from WordPress.org
- Themes are typically maintained longer than plugins
- Users expect stability and backward compatibility

---

## Related Documents

See also: `wordpress-plugin-repository-requirements.md` for plugin-specific requirements.
