# ADR 002 — Bainbot account for all Asana API writes

**Date:** 2026-05-18  
**Status:** Accepted (token swap pending — see TODO.md)

## Decision

`ASANA_PAT` in `studio/.env` must be the personal access token for the **bainbot** Asana service account, never a personal/human team member token.

## Context

Studio sync writes data back to Asana on every run — Local ID field values, Last Synced timestamps, and progress comments. Using a personal token attributes all of this activity to the human account in Asana's activity feeds and audit logs, mixing bot noise with human actions.

## Consequences

- All Asana activity from the sync script appears under the bainbot account
- Human team members' activity feeds remain clean
- To rotate the token: log into Asana as bainbot → My Settings → Apps → Personal Access Tokens → generate new token → update `studio/.env`
