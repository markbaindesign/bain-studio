---
tags: [utility, email, dns, security, devops]
god: hephaestus
description: How bain.design's email authentication (SPF, DKIM, DMARC) is configured, why, and how to verify or extend it when a new sending service is added.
---

# Email DNS setup - SPF, DKIM & DMARC

**Actually published:** 2026-08-25, by Mark, verified live the same day
**Related:** ADR 013, SL-129

> [!NOTE]
> **History worth knowing.** This document and ADR 013 previously stated these records were set
> up on 2026-08-06. They were not. The values were decided that day and written up as done, but
> never entered at the registrar, and nothing verified the published state afterwards. The gap
> surfaced 19 days later only because a client's mail filter rejected Mark's mail (SL-129) — the
> domain had no email authentication of any kind for that whole period, while this file asserted
> it did. The records below were entered by Mark on 2026-08-25 and confirmed live against four
> resolvers. See "Verification log".

---

## Current records

All three verified live 2026-08-25 against Cloudflare (1.1.1.1), Google (8.8.8.8), Quad9
(9.9.9.9) and the authoritative nameserver (`dns1.registrar-servers.com`).

**SPF** — TXT at `bain.design` (`@`):
```
v=spf1 include:_spf.google.com ~all
```

**DKIM** — TXT at `google._domainkey.bain.design`:
```
v=DKIM1; k=rsa; p=MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCA...
```
2048-bit RSA key, selector `google`, generated in the Google Admin console
(Apps → Google Workspace → Gmail → Authenticate email). Namecheap stores the value as two
quoted chunks because it exceeds 255 characters — this is correct and expected; resolvers
concatenate them. Verified by decoding the published base64 (392 chars) and parsing it with
OpenSSL as a genuine 2048-bit RSA public key, rather than trusting that a record merely exists.

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
dig @8.8.8.8 TXT google._domainkey.bain.design +short
```
Use a public resolver (8.8.8.8 or 1.1.1.1), not the local one — local/ISP resolvers
can cache or return stale/empty answers. `host -t TXT bain.design` works too.

Also query the **authoritative** nameserver (`dig ... @dns1.registrar-servers.com`). It is the
one answer that cannot be a cache artefact: if it returns nothing, the record is genuinely not
in the zone, and no amount of waiting will change that. Public resolvers can equally lag *behind*
a change — during the 2026-08-25 work Quad9 served a stale empty answer for DMARC for several
minutes after the authoritative server had it.

Never treat a registrar UI's confirmation, or a "records added" line in a document, as evidence
that a record is published. That assumption is exactly what caused this file to be wrong for 19
days. Only a resolver answer counts.

## Verification log

| Date | Checked by | Result |
|---|---|---|
| 2026-08-06 | — | **No verification performed.** Records written up as added; never published. |
| 2026-08-25 | SL-129 audit | Zero TXT records live — SPF, DKIM, DMARC all absent. MX intact. |
| 2026-08-25 | SL-129, after Mark added them | SPF, DKIM, DMARC all live on four resolvers. DKIM key decoded and parsed as a valid 2048-bit RSA key. |

Add a row whenever these records are next checked. A doc that asserts DNS state without a dated
check is the failure mode this table exists to prevent.

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

The clock on this starts **2026-08-25**, not 2026-08-06 — no reports were generated before the
records existed. One item to re-test rather than carry forward on trust: ADR 013 recorded that
the website contact/quote forms relay through Workspace SMTP and so are already covered by
`include:_spf.google.com`. That was established by inspection in August 2026 and has not been
re-tested since. If the forms in fact send directly from the hosting server
(`178.62.31.106`), they now fail SPF, and tightening to `-all` would turn that failure into
dropped mail. Confirm from the DMARC reports before tightening.
