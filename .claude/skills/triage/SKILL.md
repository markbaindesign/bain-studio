---
name: triage
description: Triage an inbound signal — classify it, qualify it if it's an RFQ, and route it. Paste the signal text as the argument. Handles email, LinkedIn, referral, contact form, and direct outreach. For automated Upwork pipeline signals, use the PIPE project pipeline instead.
---

# Triage (Autolycus)

Read an inbound signal, classify it, qualify it if it's an RFQ, and produce a routing decision.

The signal text is whatever Mark pastes — an email body, a LinkedIn message, a Upwork direct message, a contact form submission, a referral intro. Treat it as raw input.

## Steps

### 1. Classify the signal

Determine which type the signal is:

| Type | Description |
|---|---|
| **RFQ** | A request for a quote, brief, or proposal — someone wants work done |
| **Support** | An existing client asking for help, changes, or fixes |
| **Referral intro** | A third party introducing a potential client |
| **General enquiry** | Questions about the studio, services, or availability — not a specific brief |
| **Spam** | Mass outreach, irrelevant, or low-signal noise |

If the signal is ambiguous, note the ambiguity and classify as the most likely type.

### 2. Check for known client

Scan `{CONTENT_DIR}/portfolio/project-database.csv` for the client name or company. If found, note the project history: year, outcome grade, would-repeat flag. This is relevant context for qualification.

### 3. Qualify (RFQs and general enquiries only)

Score the signal against the studio's criteria. Note each point — do not just output a verdict.

**Stack fit** — does the brief mention technologies in the studio's wheelhouse?
- In wheelhouse: WordPress, WooCommerce, PHP, custom theme/plugin, web design/dev, Divi, ACF, Elementor, React, Next.js, Astro, headless, frontend
- Outside wheelhouse: mobile apps, native apps, game dev, data science, non-web software

**Budget signal** — what does the brief reveal about budget?
- Good: rate or budget mentioned and is reasonable (fixed >€1000, hourly >€50/hr, or clearly a substantial project)
- Neutral: budget not mentioned but scope suggests reasonable scale
- Concern: "quick job", "simple task", hourly <€30 mentioned, or "other devs quoted €X and it seemed high"

**Brief clarity** — how well does the client know what they want?
- Clear: deliverables described, platform/CMS known, goals stated
- Vague: outcome described but no specifics on how to achieve it
- Unclear: "build me a website" with no further detail

**Timeline** — is the deadline realistic?
- Fine: weeks or months, or not stated
- Tight but manageable: days to a week for something small
- Concern: "I need this by tomorrow", "ASAP", or "it should only take a few hours"

**Red flags** — note any of these if present:
- "My previous developer disappeared / ghosted / failed"
- "It should be simple" combined with complex requirements
- Requests to work for equity only
- Unusually aggressive tone or entitlement
- Multiple rounds of "just one more thing" already visible in the brief

**Verdict:**
- **Pursue** — good fit, route to Athena
- **Investigate** — mixed signals, one or two questions will determine fit
- **Decline** — clear poor fit or red flags

### 4. Route

**If Pursue:**
Produce a structured Athena brief (format below). Log and continue.

**If Investigate:**
List the 1–3 questions that need answers before a routing decision can be made. Draft a short reply asking them (max 3 sentences, friendly tone). Log and continue.

**If Decline:**
Draft a polite decline (format below). Log and continue.

**If Support:**
Note which project this relates to (check project-database.csv). Route to Hephaestus: flag what's needed and which project directory it likely lives in.

**If Referral intro:**
Draft a warm acknowledgement reply. Note the referral source — this is useful for Mnemosyne over time.

**If Spam:**
Note it and discard. No draft reply needed.

### 5. Log to triage log

Append an entry to `{CONTENT_DIR}/pipeline/triage-log.md` using this format:

```markdown
---

## [YYYY-MM-DD] — [Signal type] — [Client name or "Unknown"]

**Channel:** [Email / LinkedIn / Upwork DM / Referral / Contact form / Other]
**Verdict:** [Pursue / Investigate / Decline / Support / Referral / Spam]
**Client history:** [Known: last project + outcome] or [New client]

### Summary
One paragraph: what they're asking for and any notable context.

### Qualification notes
(RFQs only — brief bullets on stack fit, budget signal, brief clarity, red flags)

### Action taken
What was produced: Athena brief / investigation questions / decline draft / routing note.
```

If `{CONTENT_DIR}/pipeline/triage-log.md` does not exist, create it with a heading `# Triage Log` before the first entry.

### 6. Output

Present to Mark:
1. The classification and verdict
2. The produced output (Athena brief, investigation reply, or decline draft)
3. A one-line note on what was logged

---

## Output formats

### Athena brief

```markdown
## Brief — [slug] — [YYYY-MM-DD]
**Client:** [Name / Company]
**Channel:** [Source]
**Contact:** [Email or profile URL if given]

### What they want
[Paraphrase of the request in plain terms]

### Budget & timeline
**Budget:** [Stated amount, or "not stated"]
**Timeline:** [Stated deadline, or "not stated"]

### Tech context
[Any stack, platform, or technical requirements mentioned]

### Open questions for Athena
- [Things that need clarifying before scope can be set]
```

Athena briefs are saved to `{CONTENT_DIR}/pipeline/briefs/[slug]-[date].md`.

### Decline draft

```
Subject: Re: [their subject or "Your enquiry"]

Hi [first name],

Thanks for getting in touch. [One specific sentence acknowledging what they're looking for.]

[One honest sentence explaining why it's not the right fit — too far from the studio's stack, timeline doesn't work, fully booked — without over-explaining.]

I hope you find the right person for it. [Optional: one-line referral if you know someone who'd be a good fit.]

Mark
```

Keep it under 80 words. Specific, warm, no false promises.

---

## Notes

- The automated Upwork pipeline (PIPE project) handles Upwork alert emails. Use this skill for DMs, emails, LinkedIn, referrals, and contact form submissions.
- For known clients with a poor outcome grade or Would Repeat = FALSE, note this in the qualification — it factors into the pursuit decision.
- Never invent budget or timeline figures not stated in the signal.
- Slug format: client name or company lowercased, spaces to hyphens, date appended (e.g. `harper-legal-2026-05`).
