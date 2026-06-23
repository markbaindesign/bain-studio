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

The Cloudways API (now v2) covers almost everything needed to manage servers and applications without manual platform login. An existing open-source MCP server wraps the most useful operations and is the fastest path to giving Claude direct control. Auth is email + API key; no OAuth dance needed for scripted use.

---

## Auth

- Generate API key at: `https://platform.cloudways.com/api`
- Key is tied to the **primary account owner** only - not team members
- Exchange for a bearer token:

```bash
curl -X POST https://api.cloudways.com/api/v1/oauth/access_token \
  -d "email=you@example.com&api_key=YOUR_KEY"
```

Returns `{ "access_token": "...", "token_type": "Bearer", "expires_in": 3600 }`. Refresh before expiry or handle 401s with re-auth.

- All subsequent calls: `Authorization: Bearer {token}`

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

## Recommendation

**Install cgmorah/cloudways-mcp-server as an MCP server in Claude Code.**

This gives Claude direct access to all critical operations (deploy, restart, backup, logs, env vars) without building a custom script. The configurable base URL means it survives the v1 EOL by pointing at v2.

### Setup steps

1. Clone or install the MCP server
2. Add to `.claude/settings.json` mcpServers:

```json
"cloudways": {
  "command": "node",
  "args": ["/path/to/cloudways-mcp-server/index.js"],
  "env": {
    "CLOUDWAYS_EMAIL": "mark@bain.design",
    "CLOUDWAYS_API_TOKEN": "from platform.cloudways.com/api",
    "CLOUDWAYS_API_BASE_URL": "https://api.cloudways.com/api/v2"
  }
}
```

3. Store `CLOUDWAYS_API_TOKEN` in `studio/.env` (gitignored) alongside existing SSH creds

### What Claude could do after setup

- "What's the disk usage on baindesign server?" - calls get-server-stats
- "Deploy the latest changes to the NORE app" - calls deploy-app, then check-deployment-status
- "Restart PHP-FPM on baindesign" - calls restart-service
- "Create a backup of the MCF app before I push this change" - calls create-backup
- "Show me the error logs for baindesign" - calls get-logs
- "Set WP_DEBUG=false on the NORE app" - calls set-env-var

### Fallback: thin Python wrapper

If the MCP server approach doesn't work out (auth complexity, v2 incompatibility), a thin `studio/cloudways.py` script following the same pattern as `sync.py` is the backup. Auth token exchange + targeted endpoints for the 4-5 operations actually needed.

---

## Env variables to add

```bash
# studio/.env additions
CLOUDWAYS_EMAIL=mark@bain.design
CLOUDWAYS_API_TOKEN=  # generate at platform.cloudways.com/api
```

The SSH creds already stored (`BAINDESIGN_SSH_HOST`, `BAINDESIGN_SSH_USER`) remain separate - SSH is still the right path for operations the API doesn't cover.
