---
tags: [wordpress, contribution, theme-review, open-source]
god: hephaestus
command: none
description: Research note on the WordPress Theme Review Team — how to join, communication channels, review workflow, and how Claude can assist with theme reviews.
---

# WordPress Theme Review Team

## What it is

The Themes Team reviews submitted themes for the wordpress.org theme directory. Reviewers check for quality, security, adherence to coding standards, and theme review requirements. It's a good source of open-source contribution credit and theme development knowledge.

## Is this already being done?

No. No studio skill exists for WP theme review and no current workflow is in place.

## Communication

- **Slack:** WordPress.org Slack, `#themereview` channel — join at make.wordpress.org/chat/
- **Email:** themes@wordpress.org
- **Meetings:** 2nd and 4th Tuesday of each month at 15:00 UTC in `#themereview`
- **Blog:** make.wordpress.org/themes/

## How to join (Mark must do this)

1. WordPress.org account required (if not already created)
2. Join WordPress.org Slack at make.wordpress.org/chat/
3. Say hello in `#themereview` — informal, no application needed
4. Read the review requirements: make.wordpress.org/themes/handbook/
5. Pick a theme ticket from https://themes.trac.wordpress.org/report/2 (New themes queue)
6. After consistent reviewing, get added to the "Reviewers" group (enables ticket assignment and closing)

## How Claude can help

Claude can do the substantive technical review work:

- Check theme code for security issues (escaped output, sanitised input, nonce verification)
- Validate against WP coding standards (PHP, CSS, JS)
- Confirm required template files exist (index.php, style.css with correct header, functions.php, screenshot.png)
- Check GPL licence compliance
- Review enqueue practices (no hardcoded scripts/styles)
- Check for plugin territory features (must not be in a theme)
- Test with the Theme Check plugin criteria

## Suggested workflow

1. Mark picks a ticket from themes.trac.wordpress.org/report/2
2. Download theme ZIP from the ticket
3. Run `/wp-theme-review` skill (to be built — see BSTD-046 or similar)
4. Claude produces a structured review against the official checklist
5. Mark pastes the review as a Trac comment and updates the ticket status

## Related

- [[wp-contributor]] — Gutenberg/core contribution research
- [[wp-third-party-contributors]] — third-party plugins seeking contributors
- Skill: `wp-plugin-expert` (existing, different purpose)

## Next step

No action required from BainBot — Mark must create the WordPress.org account and join `#themereview` Slack. A follow-up task could build a `/wp-theme-review` skill to automate the review checklist using Claude.
