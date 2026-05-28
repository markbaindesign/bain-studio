# ADR-001: Use Asana duplication API for new project scaffolding

**Date:** 2026-05-28  
**Status:** Accepted

## Context

Spinning up a new client project requires a specific set of Asana sections (DOING, NEXT UP, TO DO, DONE, SOMEDAY/MAYBE), custom field attachments, and saved views. Creating these individually via API is brittle and incomplete — the API cannot set saved views, project icons, or filters.

## Decision

New Asana projects are created by duplicating a maintained template project (`ASANA_TEMPLATE_PROJECT_GID` in `studio/.env`), then deleting the placeholder tasks that make its sections visible. This is automated by `sync.py --create`.

The duplication endpoint (`POST /projects/{gid}/duplicate`) is async — it returns a job GID. `_wait_for_job` polls up to 300s before giving up.

The duplicate payload uses `include: ["notes"]` only — `"members"` is deliberately excluded to prevent the template's client members from being copied into the new project.

## Consequences

- New projects get correct sections, filters, and views without manual setup
- Template must be maintained: if sections or views drift, all future projects inherit the drift
- Custom project icon must still be set manually in Asana — the API cannot copy it
- The template project GID is a one-time config entry in `studio/.env`
