---
tags: [utility, email, dns, security, devops]
god: hephaestus
description: How bain.design's email authentication (SPF, DMARC) is configured, why, and how to verify or extend it when a new sending service is added.
---

# Email DNS setup - SPF & DMARC

**Set up:** 2026-08-06
**Related:** ADR 013

> [!WARNING]
> **Not true as of 2026-08-25.** Live DNS shows `bain.design` publishing **zero TXT records** -
> neither record below is present. Verified against Cloudflare, Google, Quad9 and the domain's
> own authoritative nameserver. The MX records in the same zone are intact, so this is not a zone
> reset; the TXT rows specifically are gone or were never saved. This surfaced only when a
> client's filter rejected Mark's mail (SL-129).
>
> Treat the section below as **the intended configuration, not the live one**, until re-verified
> with the `dig` commands in "How to verify the records". Full analysis, including DKIM (also
> absent, and never covered by this doc or ADR 013):
> `/media/data/dev/bain-studio/docs/looper/sl-129-bain-design-email-dns-audit.md`

---

## Current records

**SPF** — TXT at `bain.design` (`@`):
```
v=spf1 include:_spf.google.com ~all
```

**DMARC** — TXT at `_dmarc.bain.design`:
```
v=DMARC1; p=none; rua=mailto:mark@bain.design; fo=1
```

## Why these values

- `include:_spf.google.com` — Google Workspace is the only service that sends mail
  as `@bain.design` on the wire. Confirmed:
  - Harvest invoices send from `notifications@harvestapp.com` (your name as display
    name, your address as reply-to only) — never as bain.design, so it needs no
    SPF entry.
  - Website contact/quote forms relay through Google Workspace SMTP rather than
    sending directly from the hosting server, so they're already covered.
- `~all` / `p=none` — deliberately soft to start, since no SPF/DMARC record existed
  before this and there was no baseline confidence every legitimate sender was
  accounted for. Softfail/monitor-only surfaces problems via reports without
  risking a false-positive block of real mail.

## How to verify the records

```bash
dig @8.8.8.8 TXT bain.design +short
dig @8.8.8.8 TXT _dmarc.bain.design +short
```
Use a public resolver (8.8.8.8 or 1.1.1.1), not the local one — local/ISP resolvers
can cache or return stale/empty answers. `host -t TXT bain.design` works too.

## When a new sending service is added

Before assuming it needs an SPF include, check **what domain it actually sends
from**, not what "From" name/address is displayed:

- If it sends as `something@theirdomain.com` with your name as display name and/or
  your address as reply-to (like Harvest does) → no SPF change needed, it's
  authenticated under their domain.
- If it sends as `you@bain.design` directly (custom domain sending — common with
  marketing tools like Mailchimp/HubSpot when you connect your own domain, or
  transactional APIs like SendGrid/SES/Postmark configured with a custom domain)
  → it needs an `include:` (or a dedicated CNAME-based DKIM setup, per that
  service's own docs) added to the SPF record.
- Don't guess the `include:` hostname — pull it from the service's own
  documentation. A wrong include is worse than a missing one since it can look
  authoritative while doing nothing.

## Tightening the policy (planned follow-up)

Once a few weeks of DMARC aggregate reports (sent to mark@bain.design) show no
unexpected/unauthorized senders:

1. SPF: `~all` → `-all` (soft fail → hard fail)
2. DMARC: `p=none` → `p=quarantine` → `p=reject`

Tracked as a follow-up task in Asana (BSTD project).
