---
tags: [utility, cloudways, devops, hosting, wordpress, provisioning]
god: hephaestus
description: Step-by-step runbook for provisioning a new WordPress client project on Cloudways — server setup, app creation, SSL, staging, SSH access, and studio integration.
---

# Cloudways Provisioning Runbook

**Platform:** Cloudways (DigitalOcean Premium)
**Last updated:** 2026-06-25
**Related:** ADR 006, `docs/utilities/cloudways-api.md`

---

## Decision summary

See ADR 006. Default: one `baindesign` server (DO Premium 4GB, $54/mo) hosting multiple client apps. Use this runbook when adding a new client app to the server, or when spinning up a fresh server.

---

## Prerequisites

- Cloudways account at platform.cloudways.com (mark@bain.design)
- API token in `studio/.env` as `CLOUDWAYS_API_TOKEN`
- `baindesign` server already exists on the platform (check Platform → Servers)

---

## 1. Add a new application to existing server

### Via Cloudways Platform UI (fastest for one-off)

1. Platform → Servers → `baindesign` → Add Application
2. Application: **WordPress** (latest stable)
3. Application Name: `{client-slug}` (e.g. `nore`, `mcf`, `kf21`)
4. Application Label: `{Client Full Name}` (display only)
5. Project: assign to existing project or create new
6. Click **Add Application** — takes ~2 minutes

### Via API

```bash
# Exchange for bearer token first (expires in 1 hour)
TOKEN=$(curl -s -X POST https://api.cloudways.com/api/v2/oauth/access_token \
  -d "email=mark@bain.design&api_key=${CLOUDWAYS_API_TOKEN}" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Get server ID
SERVER_ID=$(curl -s -H "Authorization: Bearer $TOKEN" \
  https://api.cloudways.com/api/v2/server \
  | python3 -c "import sys,json; servers=json.load(sys.stdin)['servers']; print(next(s['id'] for s in servers if s['label']=='baindesign'))")

# Create application
curl -X POST https://api.cloudways.com/api/v2/app \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"server_id\": \"$SERVER_ID\",
    \"application\": \"wordpress\",
    \"app_label\": \"{client-slug}\",
    \"project_name\": \"\"
  }"
```

---

## 2. Configure the application

After app creation:

### PHP version

Set to PHP 8.2+ (or whatever the project requires):
Platform → Application → Application Settings → PHP Version

### Application credentials

Platform → Application → Application Credentials — note:
- **MySQL DB name** and **DB user** (needed for wp-config, DB pulls)
- **SFTP/SSH credentials** (host, port, user)

Store in project `.env`:

```bash
CLOUDWAYS_APP_NAME={client-slug}
CLOUDWAYS_SERVER_ID={server_id}
CLOUDWAYS_APP_ID={app_id}
SSH_HOST={app_ssh_host}
SSH_PORT={app_ssh_port}
SSH_USER={app_ssh_user}
DB_NAME={db_name}
```

### SSH shortcut

Add to `~/.ssh/config`:

```
Host {client-slug}
  HostName {SSH_HOST}
  Port {SSH_PORT}
  User {SSH_USER}
  IdentityFile ~/.ssh/id_ed25519
```

Test: `ssh {client-slug} "echo ok"`

---

## 3. Add your SSH public key

Platform → SSH Keys → Add SSH Key → paste `~/.ssh/id_ed25519.pub`

Or via API:

```bash
PUB_KEY=$(cat ~/.ssh/id_ed25519.pub)
curl -X POST "https://api.cloudways.com/api/v2/server/sshkey?server_id=${SERVER_ID}" \
  -H "Authorization: Bearer $TOKEN" \
  -d "label=bain-studio&ssh_key_contents=${PUB_KEY}"
```

---

## 4. Set up domain and SSL

### Add domain

Platform → Application → Domain Management → Add Domain → enter the live domain.

For staging: add `staging.{domain.com}` or use the Cloudways staging URL.

### SSL (Let's Encrypt)

Platform → Application → SSL Certificate → Let's Encrypt → enter domain → Install.

Requires DNS pointing at server IP first. Get server IP:
```bash
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://api.cloudways.com/api/v2/server/$SERVER_ID" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['server']['public_ip'])"
```

---

## 5. WordPress setup

### Option A: Fresh install (no existing content)

WordPress is already installed when the Cloudways app was created. Access wp-admin at:
`https://{cloudways-staging-url}/wp-admin`

Default creds are in Application Credentials → WordPress credentials.

Change wp-admin user/pass immediately. Set:
- Blog name, tagline
- Email settings
- Permalink structure (`/%postname%/`)

### Option B: Import from existing site (migration)

```bash
# 1. Export DB from source
wp --path=/path/to/source db export /tmp/source-YYYYMMDD.sql

# 2. Upload to Cloudways app
scp -P {PORT} /tmp/source-YYYYMMDD.sql {client-slug}:/tmp/

# 3. Import on Cloudways
ssh {client-slug} "wp --path=/home/{user}/htdocs/{domain}/  db import /tmp/source-YYYYMMDD.sql"

# 4. Search-replace domain
ssh {client-slug} "wp --path=/home/{user}/htdocs/{domain}/ search-replace 'https://source.domain.com' 'https://{new-domain.com}' --skip-columns=guid"

# 5. Sync uploads
rsync -avz /source/wp-content/uploads/ {client-slug}:/home/{user}/htdocs/{domain}/wp-content/uploads/

# 6. Clean up
ssh {client-slug} "rm /tmp/source-YYYYMMDD.sql"
```

**WP path on Cloudways:** `/home/{SSH_USER}/htdocs/{domain}/`

---

## 6. Set up staging

Platform → Application → Staging Management → Create Staging

This creates a linked clone. After creation:

- Staging URL: shown in Application → Staging Management
- Push live → staging: syncs DB and/or files from live to staging
- Push staging → live: deploys staging work to live

**Pull-first convention:** At the start of every dev session, Pull live → staging to sync any client uploads or content edits before working.

---

## 7. WordPress configuration

Essential plugins to install on every project:

| Plugin | Purpose |
|--------|---------|
| WP Mail SMTP / FluentSMTP | SMTP email delivery |
| Wordfence or Solid Security | Security hardening |
| WP Rocket / LiteSpeed Cache | Performance caching |
| UpdraftPlus or hosting backup | Backup (in addition to Cloudways) |
| Yoast SEO | SEO |

Environment variable for WP_DEBUG (set in wp-config.php or Cloudways env vars):
```php
define('WP_DEBUG', filter_var(getenv('WP_DEBUG'), FILTER_VALIDATE_BOOLEAN));
```

---

## 8. Studio integration

### Add to projects.json

```bash
python3 /media/data/dev/bain-studio/studio/sync.py --create \
  --name "{Client Name}" \
  --prefix "{CLN}" \
  --path /path/to/local/project
```

### Add dev-ops.md to project

```bash
cp /media/data/dev/bain-studio/docs/utilities/dev-ops.md /path/to/project/dev-ops.md
# Fill in all placeholders with project-specific values
```

### Add to studio/.env

```bash
# {CLIENT}-specific
{CLIENT}_SSH_HOST={SSH_HOST}
{CLIENT}_SSH_PORT={SSH_PORT}
{CLIENT}_SSH_USER={SSH_USER}
{CLIENT}_CLOUDWAYS_APP_ID={APP_ID}
```

---

## 9. Routine operations

### Check disk usage

```bash
# Via SSH
ssh {client-slug} "du -sh ~/htdocs/{domain}/wp-content/uploads/ && df -h"

# Via API
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://api.cloudways.com/api/v2/app/diskusage?server_id=${SERVER_ID}&app_id=${APP_ID}"
```

### Clear Varnish cache

Platform → Application → Cache Management → Purge Varnish

Or from SSH (restart service via API):
```bash
curl -X POST "https://api.cloudways.com/api/v2/service/restart" \
  -H "Authorization: Bearer $TOKEN" \
  -d "server_id=${SERVER_ID}&service=varnish"
```

### Restart PHP-FPM

Platform → Application → Services → Restart PHP-FPM

Or via API:
```bash
curl -X POST "https://api.cloudways.com/api/v2/service/restart" \
  -H "Authorization: Bearer $TOKEN" \
  -d "server_id=${SERVER_ID}&service=php8.2-fpm"
```

### Create backup

```bash
curl -X POST "https://api.cloudways.com/api/v2/backup" \
  -H "Authorization: Bearer $TOKEN" \
  -d "server_id=${SERVER_ID}&app_id=${APP_ID}"
```

### View error logs

```bash
ssh {client-slug} "tail -100 ~/logs/apache2/{domain}-error.log"
ssh {client-slug} "tail -100 ~/logs/php/error.log"
```

---

## 10. Server scaling

When the server consistently runs >70% RAM:

1. Check actual usage: Platform → Server → Monitoring → Memory
2. Scale up: Platform → Server → Scale → select new size
3. Downtime: ~5-10 min
4. Confirm DNS still pointing to same IP after scale (IP doesn't change)

Via API:
```bash
curl -X PUT "https://api.cloudways.com/api/v2/server/scale" \
  -H "Authorization: Bearer $TOKEN" \
  -d "server_id=${SERVER_ID}&plan={DO_4GB_PLAN_ID}"
```

---

## Credentials location

- API token: `studio/.env` as `CLOUDWAYS_API_TOKEN`
- Platform password: 1Password → Bain Design vault → Cloudways
- SSH keys: `~/.ssh/id_ed25519` (same key for all Cloudways servers)
- App credentials (DB user/pass, SFTP): Cloudways Platform → Application → Credentials
