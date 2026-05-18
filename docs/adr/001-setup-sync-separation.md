# ADR 001 — Setup/sync separation for Asana custom fields

**Date:** 2026-05-18  
**Status:** Accepted

## Decision

Custom field creation and project attachment are handled exclusively in `python3 sync.py --setup --project {PREFIX}`. The normal sync run (`python3 sync.py`) only reads field GIDs from `asana-ids.json` and warns if they are missing — it never creates or attaches fields.

`pm-onboard` calls `--setup` once during project onboarding.

## Context

The original `ensure_custom_field` function tried to create and attach the Local ID field on every sync run. This caused:
- 403 responses from Asana when the field was already attached (Asana returns Forbidden, not "already exists")
- Unnecessary API calls on every run
- Complex fallback logic that was hard to reason about

## Consequences

- First sync on a new project will warn about missing fields until `--setup` has been run
- `asana-ids.json` is the source of truth for field GIDs at the project level; `.env` holds workspace-level defaults
- Adding a new custom field to the sync requires updating both `--setup` and the normal sync path
