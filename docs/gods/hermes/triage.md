---
description: Classifies and routes an inbound signal — RFQ, support, referral, or
  noise
god: hermes
invoke: /triage
role: Triage clerk
tags:
- skill
- agent
---

# Triage (Autolycus)

Reads an inbound signal, classifies it, qualifies it if it's a project enquiry, and produces a routing decision. First step in the studio pipeline for any new inquiry.

## Invoke

```
/triage {paste signal text}
```

Paste the raw signal as the argument — email body, LinkedIn message, Upwork direct message, contact form, referral intro.

## Signal types

| Type | Description |
|---|---|
| **RFQ** | Request for a quote — someone wants work done |
| **Support** | Existing client asking for changes or fixes |
| **Referral intro** | Third party introducing a potential client |
| **General enquiry** | Questions about services/availability |
| **Spam** | Mass outreach, irrelevant, or low-signal |

## Qualification criteria (for RFQs)

Each is scored and noted — not just summarised:

- **Stack fit** — does the brief mention WordPress, WooCommerce, PHP, React, Next.js, Astro, headless, or web design/dev?
- **Budget signal** — any indication of budget: explicit figure, reference range, or implicit (enterprise client vs solo founder)
- **Timeline signal** — urgency, runway, whether it's greenfield or ongoing
- **Client quality** — professionalism of the brief, clarity, prior project history in `project-database.csv`

## Output

```
Signal: {type}
Client: {name/company}
Channel: {Upwork | Direct | LinkedIn | Email | Referral}

Verdict: {Pursue | Pass | Investigate | Support → route to project}

Qualification notes:
  Stack fit: {In wheelhouse / Outside / Partial}
  Budget: {explicit / inferred / unknown}
  Timeline: {details}
  Client quality: {score / notes}

Recommended next step:
  {Brief Athena / Pass with note / Follow up with question / Route to existing project}
```

## Routing

- **Pursue** → save brief to `{CONTENT_DIR}/pipeline/briefs/{slug}.md` and invoke `/athena`
- **Investigate** → log to `{CONTENT_DIR}/pipeline/triage-log.md` and flag for Abderus follow-up
- **Pass** → log to triage log with reason
- **Support** → route to the relevant active project

## Notes

- Triage does not open Athena automatically — Mark makes the call to pursue after seeing the verdict
- Abderus tracks `Investigate` verdicts and flags them if no follow-up is recorded within a reasonable window
- For automated Upwork pipeline signals, use the PIPE project pipeline instead of Triage

## See also

- [athena.md](athena.md) — next step after a Pursue verdict
- [abderus.md](abderus.md) — catches stale Investigate entries
