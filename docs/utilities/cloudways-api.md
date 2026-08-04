---
tags: [utility, cloudways, api, devops, automation]
god: hephaestus
description: Research report on Cloudways API coverage for scripting server and application management. Includes auth, endpoint map, gaps, and tooling recommendation.
---

# Cloudways API - Research Report

**Researched:** 2026-06-23  
**Task:** BSTD-039

---

## TL;DR

The Cloudways API (now v2) covers almost everything needed to manage servers and applications without manual platform login. `cgmorah/cloudways-mcp-server` wraps the most useful operations and is installed and working (see Status below). Auth is a direct bearer access token - no OAuth exchange.

---

## Auth

- Generate at: `https://platform.cloudways.com/api`
- Tied to the **primary account owner** only - not team members
- **Correction (2026-08-03):** the string Cloudways issues on that page is a ready-to-use **access token** (`cw_...`), not an API key requiring an OAuth exchange. The `/oauth/access_token` and `/oauth/token` endpoints reject it with `invalid_credentials` - there is no exchange step.
- Use it directly: `Authorization: Bearer {token}` on every call. Confirmed working against `GET /api/v2/server`.
- No documented expiry - treat it like a long-lived credential; rotate manually if compromised.

---

## Base URLs

| Version | URL | Status |
|---------|-----|--------|
| v1 | `https://api.cloudways.com/api/v1` | Deprecated (EOL March 2026) |
| v2 | `https://api.cloudways.com/api/v2` | Current |

v2 migration: replace `v1` with `v2` in paths. Response structures are similar but more consistent.

---

## What the API can do

### Servers
- List all servers
- Get server details (IP, provider, region, size, status)
- Start / stop / restart server
- Scale server (vertical scaling)
- Get server stats / monitoring graphs
- SSH key management
- Disk cleanup settings

### Applications
- List apps on a server
- Create / clone / delete application
- Get app details, credentials, settings
- Get app monitoring summary
- Deploy application (trigger deploy)
- Check deployment status
- Get application logs
- Get disk usage breakdown (webroot + database)

### Services
- Restart specific services: Apache, Nginx, PHP-FPM, MySQL, Varnish, Redis, Memcached, Elasticsearch

### SSL
- Install Let's Encrypt certificate
- Install custom certificate (CSR flow)
- DNS verification

### Backups
- Create backup
- List backups
- Restore from backup
- Rollback

### Environment Variables
- List env vars for an app (sensitive values redacted)
- Set / update env vars

### Git Deployment
- Link repository
- Pull changes
- Deployment history

### Monitoring & Alerts
- Server bandwidth usage
- Application performance metrics
- Alert retrieval

### Discovery (read-only)
- Available providers (DO, Vultr, AWS, GCP, etc.)
- Available regions per provider
- Available server sizes
- Available application stacks/packages

### v2-only additions
- Copilot subscription lifecycle
- Security suite: firewall config, IP allowlists/blocklists, malware scanning, quarantine/restore
- Password protection (htpasswd) per app
- WordPress Multisite configuration
- Stack version switching (Apache v1 vs Nginx v2)
- Client billing and reporting
- Cloudflare analytics and security logs
- Object cache enable/disable

---

## Gaps

| Operation | Available? | Notes |
|-----------|-----------|-------|
| Create new server | v1 yes, v2 unclear | v1 had POST /server |
| Check disk usage | Yes | App-level via disk usage endpoint |
| Server-level disk | Yes | Via monitoring/stats |
| Manage cron jobs | Yes | Under Application Management |
| Domain management | Yes | Add/remove domains per app |
| Database credentials | Yes | Get via app credentials |
| SSH to server | Not via API | Use stored creds: `ssh_bd` alias |
| Clone server | Not documented | App clone yes, server clone no |

---

## Existing MCP server

Two community MCP servers already exist:

### cgmorah/cloudways-mcp-server
**Tools exposed:** list-servers, list-apps, get-server-stats, deploy-app, check-deployment-status, get-logs, set-env-var, list-env-vars, manage-ssl, create-backup, list-backups, restart-service  
**Auth:** `CLOUDWAYS_EMAIL` + `CLOUDWAYS_API_TOKEN` env vars  
**Base URL:** configurable via `CLOUDWAYS_API_BASE_URL` (default v1, change to v2 path)  
**Source:** https://github.com/cgmorah/cloudways-mcp-server

### ayaz/cw-mcp-fork
**Focus:** Read-only - monitoring, discovery, SSH keys, app metrics  
**Source:** https://glama.ai/mcp/servers/ayaz/cw-mcp-fork

---

## Status: implemented (2026-08-03)

`cgmorah/cloudways-mcp-server` is cloned into `studio/tools/cloudways-mcp-server/` (own repo, not a studio-authored tool - kept out of `.gitignore`'d secrets but the source itself is committed) and built (`npm install && npm run build`). Wired into Claude Code via project-root `.mcp.json`:

```json
{
  "mcpServers": {
    "cloudways": {
      "command": "node",
      "args": ["/media/data/dev/bain-studio/studio/tools/cloudways-mcp-server/dist/index.js"]
    }
  }
}
```

No secrets in `.mcp.json` - the server loads its own gitignored `.env` (`studio/tools/cloudways-mcp-server/.env`) via `dotenv/config`. Credentials also mirrored into `studio/.env` (`CLOUDWAYS_EMAIL`, `CLOUDWAYS_API_TOKEN`) for any future script use.

**Patched `src/api/auth.ts`:** the upstream package assumed an email+api_key OAuth exchange (v1-era model). Since Cloudways now issues a direct bearer access token (see Auth section above), the OAuth exchange call always failed with `invalid_credentials`. `getAccessToken()` now just returns `CLOUDWAYS_API_TOKEN` directly - no exchange, no expiry tracking. Verified working via `list-cloudways-servers` tool call (returns the `baindesign` server, id 68015).

Base URL set to v2 (`CLOUDWAYS_API_BASE_URL=https://api.cloudways.com/api/v2` in the server's `.env`).

Tools available: `list-cloudways-servers`, `list-cloudways-apps`, `get-server-stats`, `deploy-cloudways-app`, `check-deployment-status`, `get-cloudways-logs`, `set-environment-variable`, `list-environment-variables`, `manage-ssl-certificate`, `create-cloudways-backup`, `list-cloudways-backups`, `restart-cloudways-service`.

### What Claude could do after setup

- "What's the disk usage on baindesign server?" - calls get-server-stats
- "Deploy the latest changes to the NORE app" - calls deploy-app, then check-deployment-status
- "Restart PHP-FPM on baindesign" - calls restart-service
- "Create a backup of the MCF app before I push this change" - calls create-backup
- "Show me the error logs for baindesign" - calls get-logs
- "Set WP_DEBUG=false on the NORE app" - calls set-env-var

The SSH creds already stored (`BAINDESIGN_SSH_HOST`, `BAINDESIGN_SSH_USER`) remain separate - SSH is still the right path for operations the API doesn't cover.
