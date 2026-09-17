# ADR 018 — Uptime monitoring via Better Stack, alerts by email and Slack (no out-of-hours alerts)

Date: 2026-09-16
Status: Accepted (2026-09-17)
Related: [ADR 005](005-slack-notifications-via-notifier.md) (Slack notifications go through notifier.py)

## Context

Ebiz Global (EBIZG) was down for at least four hours on 2026-09-15 before Mark happened to
check the project and noticed. There is no uptime monitoring on any studio-maintained site —
the studio's own monitoring table is empty (noted in `ddev/ebiz-global/docs`'s dev-ops notes).
An outage is currently caught by chance, not by an alert, and there is no way to say how long
a site was actually down for.

This is not specific to Ebiz Global. None of the ~17 active projects in
`studio/projects.json` have uptime monitoring, and several are live client sites the studio is
contractually maintaining.

Two options were researched: a DIY cron-based pinger, and third-party monitoring platforms
(Better Stack, UptimeRobot, StatusCake, Freshping, self-hosted Uptime Kuma).

### Why not DIY

A scheduled HTTP check is cheap to build, but a single-location checker produces false
positives from the studio's own network blips — exactly the wrong failure mode for a signal
that is meant to say "this might be an emergency, check your phone now." Multi-region checks,
historical uptime %, SSL-expiry checks, and reliable push delivery would all have to be built
and maintained from scratch, and the monitor itself becomes a single point of failure if its
host goes down. At the price of the recommended third-party option, this is not worth
building.

### Platform comparison

| Platform | Free tier | Paid tier for full portfolio (~20-30 sites) | Check interval | Notifications | Commercial use |
|---|---|---|---|---|---|
| **Better Stack** | 10 monitors, 30s checks, email/Slack/SMS/push/phone call all included | +$25/mo (or ~$21/mo annual) for 50 more monitors, covering up to 60 total | 30s | Email, Slack, Teams, SMS, native mobile push (bypasses Do Not Disturb), unlimited phone calls, all included | Yes |
| UptimeRobot | 50 monitors, 5-min checks | ~€9-10/mo Solo plan, 60s checks, native app | 60s (paid) | Native app push, Slack, email; SMS/voice metered separately | Free tier framed as hobby/non-profit — grey area for paid client work |
| StatusCake | 10 monitors, 5-min checks | ~$20/mo+ | 5 min | Email + limited integrations | Yes |
| Freshping | — | — | — | — | Discontinued March 2026 |
| Uptime Kuma (self-hosted) | Free, unlimited | VPS cost only | Configurable | Everything, but wired manually (Apprise) | Yes, but the studio owns the ops burden |

## Decision

Adopt **Better Stack** as the studio's uptime monitoring platform, one account covering every
active client site.

Reasoning:
- Its free tier alone (full alerting) beats UptimeRobot's paid tier. The research said 30s checks;
  the monitors actually run every 3 minutes (Better Stack's default on this account, not re-verified
  against the plan limits), which is enough for a studio that does not offer 24/7 response.
- No commercial-use ambiguity, unlike UptimeRobot's free tier.
- A single $25/mo tier covers the whole portfolio — simpler and cheaper than UptimeRobot's
  credit-metered SMS/voice model, and there is no per-project billing to untangle.

### Alerting

The studio does not offer 24/7 support, so nothing may wake Mark.

- **Email** on every monitor (Better Stack default).
- **Slack `#uptime`**, via Better Stack's own Slack integration (connected in the Better Stack
  dashboard, since it needs a Slack sign-in). Slack notifications respect the phone's Do Not
  Disturb, so outages are visible overnight without waking anyone. Better Stack is the origin
  of the alert, so this does not go through `notifier.py` (ADR 005).
- **Off:** mobile push, SMS and phone calls. Better Stack's push is built to bypass Do Not
  Disturb; that was the original recommendation and was rejected on 2026-09-17 for that reason.

## Rollout (done 2026-09-17)

Account created by Mark; API token in `studio/.env` as `BETTERSTACK_API_TOKEN`. Monitors were
created through the API with the same settings: HTTP status check every 3 minutes, from EU, US,
Asia and Australia regions, 30 s timeout, SSL verified, email alerts only.

| Site | Project |
|---|---|
| https://bain.design | BD (existed before the rollout) |
| https://ebiz-global.com/ | EBIZG |
| https://khyentsefoundation.org/ | KF-WEB |
| https://techstyle-accessories.com/ | TSTY |
| https://thenatureofrealestate.com/ | NORE |
| https://mhairimcfarlane.com/ | MCF |
| https://beatoproperties.com/ | Beato |

7 of the 10 free monitors are used. **To add:** tara.khyentsefoundation.org after its production
cutover (TARA-019, due 2026-09-21; it sits behind HTTP Basic Auth until then).

**Deliberately not monitored:** foobot.bain.design (being retired, FOOB-001), the KF archive
site, and WPLSCM.

Stay on the free tier until it is full, then move to the paid tier deliberately.

### Note: false "down" reports from Spain

khyentsefoundation.org is behind Cloudflare. On 2026-09-17 it was unreachable from the studio's
Telefónica connection while up everywhere else: Spanish ISPs block shared Cloudflare IPs under
LaLiga's anti-piracy court order (Barcelona Commercial Court No. 6, December 2024), mostly
during match broadcasts. Better Stack checks from outside Spain, so its monitors are unaffected,
but a manual check from the studio can wrongly suggest a Cloudflare-hosted site is down. Confirm
against Better Stack, or check via a VPN, before treating it as an outage.

## Consequences

- New recurring cost once the portfolio exceeds 10 monitored sites (~$25/mo, price as researched 2026-09-16; recheck before upgrading). Small relative
  to the cost of an undetected outage, but a real, ongoing line item that should be logged
  in the studio's own finances once it starts.
- The studio now has a single place to point at for "was this site actually down, and for how
  long" — closing the gap that made the EBIZG incident report unable to state a precise outage
  duration.
