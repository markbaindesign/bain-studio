---
tags: [adr, infrastructure, hosting, cloudways]
god: hephaestus
description: Cloudways is the standard platform for client WordPress projects. DO Premium 4GB server, staging-linked workflow, offboarding via Clone App.
---

# ADR 006 — Cloudways is the standard platform for client WordPress projects

**Date:** 2026-06-23
**Status:** Accepted

## Decision

New WordPress client projects are hosted on Cloudways (DigitalOcean Premium). The default server tier is **4GB RAM / 2 vCPU / 80GB NVMe ($54/month)**. Multiple client apps share one server. Staging is the standard dev workflow. Offboarding uses Clone App.

## Context

The studio needed a standard hosting platform for client WordPress projects. The options evaluated were Cloudways and WP Engine.

Key constraints:
- Solo studio - no need for white-label portals or client billing systems
- 3-6 active client projects at any given time
- Technically capable operator - comfortable with SSH, CLI, API
- Already running bain.design on Cloudways (known quantity)
- Want to script provisioning and ops via API

## Reasoning

### Why Cloudways over WP Engine

WP Engine's main advantage is agency tooling: white-label dashboards, client billing, bulk site management. None of that is relevant for a solo studio where Mark manages everything directly.

Cost for 3-6 sites:
- WP Engine Growth: $109/month (10 sites, 100k visits) - limited per-site pricing
- Cloudways DO Premium 4GB: $54/month (unlimited apps on server) - roughly half the cost

Cloudways also offers more infrastructure flexibility: choose cloud provider, server size, PHP version per app. It scales up or down via API. WP Engine is more opinionated and less scriptable.

### Server sizing

| Projects | Recommended tier | Price/mo |
|----------|-----------------|----------|
| 1-3 light sites | DO Premium 2GB | $28 |
| 3-6 moderate WP sites | DO Premium 4GB | $54 |
| 6-12+ sites or WooCommerce | DO Premium 8GB | $88 |

Default is 4GB. Resize via API (`POST /v2/server/scale`) - ~5-10 min downtime. Scale down after a busy period is safe if actual usage fits the smaller tier.

### Staging workflow

Cloudways offers two cloning modes:

- **Create Staging** - linked clone. Push/pull changes between staging and live. Incremental or full overwrite, files and/or DB separately. This is the standard dev workflow.
- **Clone App** - standalone duplicate with no live connection. Used for new project bootstrapping or handing a site off to a client on their own server.

**Media library behaviour:** No shared library. Media is copied at clone time; staging and live diverge after. Mitigated by a Pull-first convention: always Pull live → staging at the start of a dev session to sync any client uploads before working.

**Standard session workflow:**
1. Pull live → staging (syncs DB + files including any client media uploads)
2. Build and test on staging
3. Push staging → live (DB + files, or DB-only for content-only changes)

### Offboarding

When a client wants to self-host: Clone App to their own Cloudways account or export files + DB dump manually. No vendor lock-in at the data layer.

### Scripting and API

Cloudways API v2 (`https://api.cloudways.com/api/v2`) covers all provisioning ops: create app, restart services, deploy, backup, SSL, disk stats, env vars, SSH keys. Auth: email + API key (generate at `platform.cloudways.com/api`). API token stored as `CLOUDWAYS_API_TOKEN` in `studio/.env`.

Full API research: `docs/utilities/cloudways-api.md`.

Provisioning runbook: `docs/utilities/cloudways-provisioning.md` (follow-on task).

## Consequences

- Client WordPress projects default to Cloudways. Non-WordPress or Astro/Node-heavy projects continue to use Vercel/Netlify as appropriate.
- SSH credentials for each server stored in `studio/.env` (`BAINDESIGN_SSH_HOST`, `BAINDESIGN_SSH_USER` pattern).
- Pull-first convention must be documented in project onboarding so it becomes habit.
- Server resizing requires brief downtime - flag to client if they're on the same server as their live site.
- One server per client is an option for higher isolation but raises cost to $28-54/client/month.

## Related

- `docs/utilities/cloudways-api.md` - API coverage, auth, scriptable operations
- `docs/utilities/cloudways-provisioning.md` - provisioning runbook (pending)
- BSTD-039 - research task
