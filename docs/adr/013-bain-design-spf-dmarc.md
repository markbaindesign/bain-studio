---
tags: [adr, infrastructure, email, dns, security]
god: hephaestus
description: bain.design had no SPF or DMARC record at all; chose a Google-Workspace-only SPF include and a monitor-only DMARC policy as the studio's baseline email authentication. Decided 2026-08-06, actually published 2026-08-25.
---

# ADR 013 — bain.design gets a baseline SPF + DMARC record

**Decided:** 2026-08-06
**Published:** 2026-08-25 (see "Correction")
**Status:** Accepted, implemented
**Related:** `docs/utilities/email-dns-setup.md`, SL-129

## Decision

Publish two DNS TXT records for bain.design:

- **SPF** (`@`): `v=spf1 include:_spf.google.com ~all`
- **DMARC** (`_dmarc`): `v=DMARC1; p=none; rua=mailto:mark@bain.design; fo=1`

## Correction (2026-08-25)

**This ADR originally read "Added two DNS TXT records" in the past tense. That was false when
written.** The records were decided on 2026-08-06 and documented as done, but were never entered
at the registrar, and nothing checked the published state afterwards.

The domain therefore had no email authentication at all for the following 19 days. It surfaced
only when a client's mail filter rejected Mark's mail, prompting task SL-129, whose audit found
`bain.design` publishing zero TXT records — confirmed against Cloudflare, Google, Quad9 and the
authoritative nameserver. The MX records in the same zone were intact throughout, the
nameservers had not moved, and the domain is not hosted anywhere else, so nothing had been lost
or overwritten: the rows were simply never added.

Mark published all three records himself on 2026-08-25, verified live the same day. **DKIM** was
added at that point too (`google._domainkey`, 2048-bit, selector `google`) — this ADR never
covered DKIM, which was a second gap in the original decision, not just in its execution.

**What this ADR should have done, and what future infrastructure ADRs must do:** separate the
decision from its execution, and cite a verification. This one documented its *before* state
meticulously — two public resolvers plus Google's DNS-over-HTTPS API — and then recorded the fix
with no check at all. Every verifiable claim in it concerned the problem; the one claim about
the solution went untested. An ADR that asserts infrastructure state carries a dated
verification, or it says "decided, not yet applied".

## Context

An email from a third party claimed bain.design had "an SPF record issue" causing
their spam filter to reject mail from us, and that they'd whitelisted the address
as a workaround. Checked directly rather than taking the claim at face value:
querying TXT records for bain.design via two independent public resolvers (Google
8.8.8.8, Cloudflare 1.1.1.1) plus Google's DNS-over-HTTPS API all returned zero TXT
records — not a broken SPF record, but no SPF record published at all. `_dmarc.bain.design`
was NXDOMAIN too.

MX records show bain.design mail runs on Google Workspace (`aspmx.l.google.com` and
alternates). Checked whether any other service sends mail as `@bain.design` that would
need its own SPF include:

- **Harvest** (invoicing) — confirmed via Harvest's own help docs
  (support.getharvest.com) that invoice/estimate emails are always sent from
  `notifications@harvestapp.com`, using the sender's name as display name and their
  address only as reply-to. Never sent as `@bain.design` on the wire, so no SPF
  include needed — it's authenticated under Harvest's own domain.
- **Website contact/quote forms** — confirmed these relay through Google Workspace
  SMTP rather than sending directly from the hosting server's IP, so they're already
  covered by `include:_spf.google.com`. (If this ever changes to direct server
  sending, that server's IP would need its own SPF entry, or better, get switched
  back to relay through Workspace.)

## Reasoning

- **`~all` (softfail) rather than `-all` (hard fail) to start.** No prior SPF record
  existed, so there's no baseline evidence every legitimate sender is accounted for.
  Softfail flags unauthorized mail as suspicious without risking silently dropping
  something legitimate that wasn't anticipated.
- **`p=none` on DMARC to start**, same reasoning — monitor via aggregate reports
  before enforcing anything. Reports land at mark@bain.design (`rua=`), with
  forensic-style detail requested (`fo=1`).
- **No Harvest/PandaDoc/DocuSign includes added** — verified via Harvest's own
  documentation that they don't send as bain.design, rather than guessing a
  plausible-sounding `include:` value and risking an incorrect SPF record (a wrong
  include is arguably worse than no include, since it looks authoritative).

## Consequences

- Follow-up task created in Asana (BSTD) to review DMARC aggregate reports after a
  few weeks and tighten `p=none` → `p=quarantine` → `p=reject`, and reconsider
  `~all` → `-all` on SPF once reports look clean.
- If a new sending service is added for bain.design in future (marketing tool,
  transactional API, etc.), check whether it sends using a bain.design "from"
  address (needs an SPF include) versus its own domain with reply-to (does not),
  the same way this was resolved for Harvest.
- Documented in `docs/utilities/email-dns-setup.md` as the canonical reference for
  bain.design's email authentication setup.
- The DMARC-tightening clock starts 2026-08-25, not 2026-08-06 — no aggregate reports were
  generated before the records existed.
- The finding that the website contact/quote forms relay through Workspace SMTP was established
  by inspection in August 2026 and has not been re-tested. If they in fact send directly from the
  hosting server, they now fail SPF, and tightening `~all` → `-all` would convert that into
  dropped mail. Confirm from the DMARC reports before tightening.

## Related

- `docs/utilities/email-dns-setup.md` — SPF/DKIM/DMARC record reference, verification log, and how to verify them
- `docs/looper/sl-129-bain-design-email-dns-audit.md` — the SL-129 audit that caught the gap
- BSTD Asana task — DMARC policy tightening follow-up
