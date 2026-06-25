---
tags: [utility, cloudways, hosting, provisioning, devops]
god: hephaestus
description: Step-by-step runbook for provisioning a new client WordPress app on Cloudways. Covers API auth, app creation, staging, SSL, SSH, and first deploy.
---

# Cloudways Provisioning Runbook

Runbook for provisioning a new client WordPress application on Cloudways using the API and CLI. No manual platform login required for the core setup. Uses `studio/.env` credentials.

**Related:** `docs/utilities/cloudways-api.md` (API coverage), `docs/adr/006-cloudways-client-hosting.md` (decision)

---

## Prerequisites

Credentials in `studio/.env`:

```bash
CLOUDWAYS_EMAIL=mark@bain.design
CLOUDWAYS_API_TOKEN=   # generate at platform.cloudways.com/api
BAINDESIGN_SERVER_ID=  # from: GET /v2/server (list servers)
```

API base: `https://api.cloudways.com/api/v2`

---

## Step 1 — Get an API bearer token

```bash
source studio/.env

TOKEN=$(curl -s -X POST https://api.cloudways.com/api/v2/oauth/access_token \
  -d "email=$CLOUDWAYS_EMAIL&api_key=$CLOUDWAYS_API_TOKEN" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

echo "Token: $TOKEN"
```

Token expires in 3600s. Re-run if you get 401s.

---

## Step 2 — Identify the target server

```bash
curl -s -H "Authorization: Bearer $TOKEN" \
  https://api.cloudways.com/api/v2/server \
  | python3 -c "
import sys, json
servers = json.load(sys.stdin)['servers']
for s in servers:
    print(s['id'], s['label'], s['status'], s['public_ip'])
"
```

Note the server `id` — this is `BAINDESIGN_SERVER_ID`. If the server is at capacity (memory or disk), provision a new one before continuing (see Step 2b).

### Step 2b — Create a new server (if needed)

```bash
curl -s -X POST https://api.cloudways.com/api/v2/server \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "cloud": "do",
    "region": "lon1",
    "instance_type": "premium-4gb",
    "server_label": "baindesign-2"
  }' | python3 -c "import sys,json; d=json.load(sys.stdin); print(d)"
```

Server creation takes ~5 min. Poll `GET /v2/server/{id}` until `status` is `running`.

---

## Step 3 — Create the WordPress application

```bash
SERVER_ID=$BAINDESIGN_SERVER_ID
CLIENT_SLUG="client-name"   # lowercase, hyphens, no spaces

curl -s -X POST https://api.cloudways.com/api/v2/app \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"server_id\": \"$SERVER_ID\",
    \"application\": \"wordpress\",
    \"app_label\": \"$CLIENT_SLUG\",
    \"project_name\": \"$CLIENT_SLUG\"
  }" | python3 -c "import sys,json; d=json.load(sys.stdin); print(json.dumps(d, indent=2))"
```

Note the returned `app_id`. Add to project's `studio/.env`:

```bash
{CLIENT_PREFIX}_APP_ID=
{CLIENT_PREFIX}_SERVER_ID=
```

---

## Step 4 — Get app credentials

```bash
APP_ID="{from step 3}"

curl -s -H "Authorization: Bearer $TOKEN" \
  "https://api.cloudways.com/api/v2/app/creds?server_id=$SERVER_ID&app_id=$APP_ID" \
  | python3 -c "
import sys, json
c = json.load(sys.stdin)['credentials']
print('WP URL:', c.get('app_url'))
print('DB name:', c.get('mysql_db'))
print('DB user:', c.get('mysql_user'))
print('SFTP host:', c.get('sftp_host'))
print('SFTP user:', c.get('sftp_username'))
print('WP admin:', c.get('wp_admin_email'))
"
```

Store credentials in 1Password under `[Client] Cloudways`. Add SSH/SFTP details to project's `dev-ops.md`.

---

## Step 5 — Add the domain

```bash
DOMAIN="clientdomain.com"

curl -s -X POST https://api.cloudways.com/api/v2/domain \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"server_id\": \"$SERVER_ID\",
    \"app_id\": \"$APP_ID\",
    \"domain\": \"$DOMAIN\"
  }"
```

Point DNS A record at server IP before proceeding to SSL.

---

## Step 6 — Install SSL (Let's Encrypt)

```bash
curl -s -X POST https://api.cloudways.com/api/v2/ssl \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"server_id\": \"$SERVER_ID\",
    \"app_id\": \"$APP_ID\",
    \"ssl_email\": \"mark@bain.design\",
    \"ssl_domains\": [\"$DOMAIN\", \"www.$DOMAIN\"]
  }"
```

Let's Encrypt requires DNS to already be propagated. Check with `dig $DOMAIN` first.

---

## Step 7 — Create staging environment

```bash
curl -s -X POST https://api.cloudways.com/api/v2/staging/app \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"server_id\": \"$SERVER_ID\",
    \"app_id\": \"$APP_ID\"
  }" | python3 -c "import sys,json; print(json.dumps(json.load(sys.stdin), indent=2))"
```

Staging is a linked clone. Pull live → staging at the start of every dev session:

```bash
# Pull live → staging (sync DB + files)
curl -s -X POST https://api.cloudways.com/api/v2/staging/pull \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"server_id\": \"$SERVER_ID\",
    \"app_id\": \"$APP_ID\",
    \"pull_type\": \"full\"
  }"
```

Push staging → live after testing:

```bash
curl -s -X POST https://api.cloudways.com/api/v2/staging/push \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"server_id\": \"$SERVER_ID\",
    \"app_id\": \"$APP_ID\",
    \"push_type\": \"full\"
  }"
```

---

## Step 8 — Set environment variables

```bash
curl -s -X POST https://api.cloudways.com/api/v2/app/manage/envvar \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"server_id\": \"$SERVER_ID\",
    \"app_id\": \"$APP_ID\",
    \"data\": {
      \"WP_DEBUG\": \"false\",
      \"WP_DEBUG_LOG\": \"false\"
    }
  }"
```

---

## Common ops

### Restart a service

```bash
SERVICE="php-fpm"  # nginx, apache2, mysql, php-fpm, memcached, redis, varnish

curl -s -X POST https://api.cloudways.com/api/v2/service/restart \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"server_id\": \"$SERVER_ID\", \"service\": \"$SERVICE\"}"
```

### Create a backup

```bash
curl -s -X POST https://api.cloudways.com/api/v2/backup \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"server_id\": \"$SERVER_ID\", \"app_id\": \"$APP_ID\"}"
```

### Check disk usage

```bash
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://api.cloudways.com/api/v2/app/manage/disk?server_id=$SERVER_ID&app_id=$APP_ID" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(json.dumps(d, indent=2))"
```

### Get application logs

```bash
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://api.cloudways.com/api/v2/app/logs?server_id=$SERVER_ID&app_id=$APP_ID&log_type=error" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('log',''))"
```

### SSH directly

```bash
# Add your public key via API first
curl -s -X POST https://api.cloudways.com/api/v2/ssh_key \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"server_id\": \"$SERVER_ID\", \"ssh_key_name\": \"mark-bain\", \"ssh_key\": \"$(cat ~/.ssh/id_ed25519.pub)\"}"

# Then SSH
ssh {SFTP_USER}@{SERVER_IP}
```

---

## Offboarding a client

1. Export DB: `wp db export /tmp/{slug}-export.sql --path={WP_ROOT}`
2. Download files via SFTP or rsync
3. If client wants Cloudways: Clone App → their own Cloudways account
4. If client wants another host: zip `wp-content/`, export DB, hand over
5. Delete the app: `DELETE /v2/app` (irreversible — confirm first)

```bash
# DELETE is irreversible. Confirm slug before running.
curl -s -X DELETE https://api.cloudways.com/api/v2/app \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"server_id\": \"$SERVER_ID\", \"app_id\": \"$APP_ID\"}"
```
