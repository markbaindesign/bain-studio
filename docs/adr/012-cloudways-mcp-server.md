---
tags: [adr, infrastructure, hosting, cloudways, mcp]
god: hephaestus
description: cgmorah/cloudways-mcp-server installed as the studio's Cloudways automation path; access-token auth patched in since the upstream package assumed an obsolete OAuth exchange.
---

# ADR 012 — Cloudways MCP server is the studio's hosting automation path

**Date:** 2026-08-03
**Status:** Accepted
**Related:** ADR 006 (Cloudways is the standard client hosting platform)

## Decision

`cgmorah/cloudways-mcp-server` is vendored into `studio/tools/cloudways-mcp-server/`
(source committed, `node_modules`/`dist`/`.env` gitignored) and wired into Claude Code
via a project-root `.mcp.json`. This is now the default way Claude performs Cloudways
operations (list servers/apps, deploy, restart services, backups, SSL, env vars, logs)
instead of the manual curl commands in `docs/utilities/cloudways-provisioning.md`.

## Context

ADR 006 picked Cloudways as the hosting platform and flagged the MCP server as the
fastest path to giving Claude direct control, pending the actual API token. Setting it
up surfaced a factual error in the original research (`docs/utilities/cloudways-api.md`):
the credential generated at `platform.cloudways.com/api` was assumed to be an API key
requiring an OAuth exchange (`POST /oauth/{token,access_token}` with `email` + `api_key`
→ short-lived bearer token, 1hr expiry). In practice:

- Both `/oauth/token` and `/oauth/access_token`, on both v1 and v2, rejected the
  credential with `invalid_credentials` - regenerating the key made no difference.
- Calling `GET /api/v2/server` directly with `Authorization: Bearer {token}` worked
  immediately. The credential Cloudways issues (`cw_...`) is already a usable access
  token, not an API key to exchange.

The upstream `cloudways-mcp-server` package's `src/api/auth.ts` implemented the v1-era
OAuth exchange model and would never authenticate with this account.

## Reasoning

- **Patch, don't fork or replace.** The rest of the package (tool definitions, API
  clients for servers/apps/backups/SSL/logs/env vars) is sound and matches the endpoint
  map in `docs/utilities/cloudways-api.md`. Only `CloudwaysAuth.getAccessToken()` needed
  to change - it now returns `CLOUDWAYS_API_TOKEN` directly instead of exchanging it.
- **Vendor the source in-repo rather than depend on the GitHub repo at runtime.** The
  nested `.git` from the clone was stripped so the code is tracked as plain files in
  `bain-studio` - a two-person open-source package with an auth model that's already
  proven wrong once is not something to depend on unpinned. Any future upstream changes
  get pulled in deliberately, not silently.
- **No secrets in `.mcp.json` or in `.claude/settings.json`.** Both are tracked in git.
  Credentials live only in gitignored `.env` files: `studio/.env` (studio-wide,
  `CLOUDWAYS_EMAIL` + `CLOUDWAYS_API_TOKEN`, mirrors the existing pattern for
  `HARVEST_TOKEN` etc.) and `studio/tools/cloudways-mcp-server/.env` (loaded by the
  server itself via `dotenv/config`, since MCP server processes don't inherit
  `studio/.env` automatically).
- **Base URL pinned to v2** (`CLOUDWAYS_API_BASE_URL`) per ADR 006's v1-EOL note.

## Consequences

- `docs/utilities/cloudways-api.md` corrected in place (auth section, status section)
  rather than left describing a flow that doesn't work.
- Any other tooling that needs to call the Cloudways API directly (e.g. a future
  `studio/cloudways.py`) must use the token as a direct bearer credential, not attempt
  the OAuth exchange - this ADR is the canonical note against reintroducing that bug.
- The vendored package needs manual re-sync if the upstream project fixes its own auth
  or adds tools - no automatic update path.

## Related

- ADR 006 - Cloudways as standard hosting platform
- `docs/utilities/cloudways-api.md` - endpoint map, corrected auth section, implementation status
- `docs/utilities/cloudways-provisioning.md` - manual/curl runbook, still valid for one-off ops the MCP tools don't cover
- `studio/tools/cloudways-mcp-server/src/api/auth.ts` - the patched auth module
