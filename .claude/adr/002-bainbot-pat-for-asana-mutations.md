# ADR-002: Use bainbot PAT for all Asana mutations

**Date:** 2026-05-28  
**Status:** Accepted

## Context

Asana changes made via the human OAuth token (used by the Asana MCP) appear in Asana attributed to Mark Bain, conflate human and automated actions in the audit trail, and carry OAuth expiry risk. The Asana MCP plugin uses the human account by default and cannot be trusted not to make changes under Mark's identity.

## Decision

All Asana API mutations (task create/update, project create, member management, section management) go through `sync.py`, which loads `ASANA_PAT` from `studio/.env`. This token belongs to the `bainbot` service account.

The Asana MCP plugin is disabled for this project via `disabledMcpjsonServers` in `.claude/settings.json` to prevent accidental human-token mutations.

The PM workflow is:
1. Read task state from local mirror (`.claude/asana-mirror.md`)
2. Edit the mirror as needed
3. Run `python3 studio/sync.py` to push changes via bainbot

Skills that push to Asana (e.g. `pm-todos`) must load `ASANA_PAT` from `studio/.env` via python-dotenv and use it in all curl calls. Never use `$ASANA_TOKEN`.

## Consequences

- Automated changes are clearly attributed to bainbot in Asana's activity log
- PAT does not expire on the same OAuth cycle as Mark's personal token
- Any script that bypasses `sync.py` and calls the Asana API directly must still use `ASANA_PAT`
