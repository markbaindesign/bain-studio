---
tags: [utility, devops, hosting, template]
description: Template for project dev-ops documentation. Copy to the project root as dev-ops.md and fill in the blanks. No passwords or keys.
---

# Dev Ops — [Project Name]

**Hosting platform:** <!-- Cloudways / WP Engine / Vercel / cPanel / VPS -->  
**Server/account created:** <!-- YYYY-MM-DD -->  
**Last reviewed:** <!-- YYYY-MM-DD -->

---

## Hosting

| Field | Value |
|-------|-------|
| Platform | |
| Plan / tier | |
| Data centre / region | |
| Account owner | |
| Account email | |
| Control panel URL | |
| Server label | |
| Server IP | |
| PHP version | |
| Web server | <!-- Apache / Nginx --> |
| Database | <!-- MySQL 8.x / MariaDB --> |

---

## Domains & DNS

| Domain | Role | DNS managed at | Notes |
|--------|------|---------------|-------|
| example.com | Production | Cloudflare | |
| staging.example.com | Staging | Cloudflare | |
| www.example.com | Redirect → apex | | |

**Registrar:** <!-- Namecheap / Cloudflare / GoDaddy -->  
**DNS propagation tool:** `dig example.com` or https://dnschecker.org

---

## SSH

```bash
# Production
ssh -p {PORT} {USER}@{HOST}

# Staging (if separate)
ssh -p {PORT} {USER}@{HOST}
```

**WP root (production):** `/path/to/public_html`  
**WP root (staging):** `/path/to/staging/public_html`

Alias (add to `~/.ssh/config` or shell aliases):
```bash
alias ssh-{project}='ssh -p {PORT} {USER}@{HOST}'
```

---

## Repository & Deploy

| Field | Value |
|-------|-------|
| Repo host | <!-- GitHub / Bitbucket / GitLab --> |
| Repo URL | |
| Default branch | |
| Staging branch | |
| Deploy method | <!-- git push / script / Bitbucket Pipelines / WP Engine git / Vercel --> |

**Deploy command:**
```bash
# e.g. git push wpengine staging
```

**Deploy log / URL:**

---

## Local Development

| Field | Value |
|-------|-------|
| Local environment | <!-- VVV / Lando / DDEV / Docker --> |
| Local URL | |
| Config file | |

**Start local env:**
```bash
# e.g. cd /media/data/dev/vvv && vagrant up
```

---

## Database

**Engine:** MySQL {version}  
**DB name (prod):** `{dbname}`  
**DB name (staging):** `{dbname_staging}`  
**DB host:** `localhost`  

### Prod → Local sync
```bash
# 1. Dump on production
wp --path={WP_ROOT} db export /tmp/{project}-prod-$(date +%Y%m%d).sql

# 2. Download
scp -P {PORT} {USER}@{HOST}:/tmp/{project}-prod-YYYYMMDD.sql /tmp/

# 3. Import to local
# (adjust path for your local env)

# 4. Search-replace URLs
wp search-replace 'https://example.com' 'http://example.test' --skip-columns=guid

# 5. Clean up dump from server
ssh -p {PORT} {USER}@{HOST} "rm /tmp/{project}-prod-YYYYMMDD.sql"
```

### Staging sync (prod → staging)
```bash
# platform-specific — document here
```

---

## Uploads / Media

**Production uploads path:** `{WP_ROOT}/wp-content/uploads/`

**Rsync prod → local:**
```bash
rsync -avz --progress \
  -e "ssh -p {PORT}" \
  {USER}@{HOST}:{WP_ROOT}/wp-content/uploads/ \
  /local/path/wp-content/uploads/
```

---

## SSL / HTTPS

| Field | Value |
|-------|-------|
| Certificate provider | <!-- Let's Encrypt / Cloudflare / custom --> |
| Auto-renew | <!-- Yes / No --> |
| Expiry check command | `echo | openssl s_client -connect example.com:443 2>/dev/null | openssl x509 -noout -dates` |

---

## Backups

| Type | Frequency | Location | Retention |
|------|-----------|----------|-----------|
| Server / full | | | |
| DB only | | | |
| Files only | | | |
| Off-platform copy | | | |

**Restore test last performed:** <!-- YYYY-MM-DD or Never -->

---

## Cron Jobs

| Schedule | Command | Notes |
|----------|---------|-------|
| | | |

**View crontab:**
```bash
ssh -p {PORT} {USER}@{HOST} "crontab -l"
```

---

## Environment Variables / Config

All secrets live in the server environment or `.env` (gitignored). No keys or passwords in this file.

| Variable | Used for | Where set |
|----------|---------|-----------|
| `WP_DEBUG` | Debug mode | wp-config.php |
| | | |

---

## Common Commands

```bash
# Flush rewrite rules
wp rewrite flush --path={WP_ROOT}

# Check WP version on prod
wp core version --path={WP_ROOT}

# Clear object cache
wp cache flush --path={WP_ROOT}

# Restart PHP-FPM (Cloudways)
# Use Cloudways API or platform console

# Check disk usage
ssh -p {PORT} {USER}@{HOST} "df -h && du -sh {WP_ROOT}/wp-content/uploads/"
```

---

## Monitoring & Alerts

| Service | What it monitors | URL / notes |
|---------|-----------------|-------------|
| | | |

---

## Contacts

| Role | Name | Contact |
|------|------|---------|
| Hosting support | | |
| Domain registrar support | | |
| Client IT contact | | |

---

## Incident Log

| Date | Issue | Resolution |
|------|-------|------------|
| | | |
