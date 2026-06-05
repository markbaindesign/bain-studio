# staging-create — Spec

Studio script to automate spinning up a staging environment on Cloudways from an existing production app.

**Status:** Scoped — not yet built  
**Target location:** `~/code/bain-studio/studio/scripts/`  
**Filename:** `staging-create.sh`

---

## Inputs

Prompted interactively, or passed as flags. API key and server ID fall back to `~/.bain/config` if set.

| Input | Flag | Config fallback |
|---|---|---|
| Cloudways API key | `--api-key` | `CLOUDWAYS_API_KEY` |
| Cloudways account email | `--email` | `CLOUDWAYS_EMAIL` |
| Server ID | `--server-id` | `DEFAULT_SERVER_ID` |
| Source (prod) app ID | `--app-id` | — |
| Staging subdomain | `--subdomain` | — |
| App label | `--label` | — |
| Basic Auth username | `--ba-user` | auto-generated if omitted |
| Basic Auth password | `--ba-pass` | auto-generated if omitted |

---

## Config file

`~/.bain/config`

```
CLOUDWAYS_EMAIL=mark@bain.design
CLOUDWAYS_API_KEY=xxxxx
DEFAULT_SERVER_ID=xxxxx
```

---

## Steps

1. **Authenticate** — `POST /oauth/access_token` → bearer token
2. **Create app** — `POST /app` (wordpress, same server) → `app_id`
3. **Clone prod** — `POST /app/clone` (files + DB) into new app
4. **Attach subdomain** — `POST /app/cname`
5. **Search-replace domain** — SSH → `wp search-replace <prod-url> <staging-url>`
6. **Patch wp-config.php** — SSH → set:
   - `WP_DEBUG true`
   - `WP_DEBUG_LOG true`
   - `FS_METHOD direct`
7. **Swap admin email** — SSH → `wp option update admin_email mark@bain.design`
8. **Create staging admin user** — SSH → `wp user create staging-admin staging@bain.design --role=administrator --user_pass=<generated>` (skip if user already exists)
9. **Password protect** — `POST /app/manage/basicAuth` → enable Basic Auth with generated (or supplied) credentials
10. **Print summary** — staging URL, app ID, WP admin login link, Basic Auth credentials, staging-admin username + password

---

## Out of scope (manual after)

- SSL cert — Cloudways one-click, ~30 seconds
- Per-project secrets — FluentBooking tokens, OAuth keys, etc. are project-specific
- Cache settings — Breeze/Varnish config is awkward via API; disable manually in Cloudways dashboard

---

## Dependencies

- `curl`
- `jq`
- SSH access to the Cloudways server
