---
name: studio-delivery-gate
description: Run the full delivery gate sequence for a completed project — Themis QA → Mark sign-off package → Iris announce → Harvest trigger. Invoke when a project is ready to ship. Enforces the Law of the Gate.
argument-hint: <project-slug>
allowed-tools: [Read, Write, Bash]
---

# Studio Delivery Gate

The delivery gate is the moment between "done" and "shipped." Themis holds it open only if everything checks out. Mark walks through it. Nobody else can.

**The sequence:** Themis QA → Gate report for Mark → (Mark approves) → Iris announces → Harvest triggers.

---

## Step 1 — Load project context

Read `CLAUDE.md` in the current project directory. Extract: project name, prefix, client name, delivery URL or artefacts.

Read the Athena report from `context/pipeline/athena/{slug}-*.md` for the agreed scope and deliverables.

If no slug is provided, ask for it.

---

## Step 2 — Themis QA

Invoke Themis:
```
/themis review
```

Themis runs Eunomia (scope), Dike (accessibility), and Eirene (performance). She produces a gate ruling: **GATE CLEAR** or **GATE BLOCKED**.

If **GATE BLOCKED**: stop here. List every blocker with its owner (Hephaestus or Aphrodite). Do not proceed to gate prep. Notify Mark:

```bash
python3 /media/data/dev/bain-studio/studio/notifier.py \
  "{Project} delivery gate BLOCKED — {N} issues. Review Themis report at context/pipeline/review/{slug}-themis-{date}.md" \
  --priority high --sender hermes --project {prefix}
```

---

## Step 3 — Gate package for Mark

Assemble a delivery gate review package at `context/pipeline/delivery/{slug}-gate-{YYYY-MM-DD}.md`:

```markdown
# Delivery Gate — {Project Name} — {Date}

## Status
Themis: GATE CLEAR (or CLEAR WITH FLAGS)

## What was delivered
{Summary of deliverables from Eunomia's scope check — one line per item}

## Quality summary
- Scope: COMPLIANT (or COMPLIANT WITH FLAGS — list flags)
- Accessibility: PASS (or CONDITIONAL PASS — list advisory notes)
- Performance: PASS (or CONDITIONAL PASS — list metrics)

## Flags (advisory, non-blocking)
{List any flags from Themis — not blockers, but Mark should be aware}

## Delivery details
- Live URL: {url or TBC}
- Staging: {url}
- Themis report: context/pipeline/review/{slug}-themis-{date}.md

## What happens next (pending your approval)
1. Iris announces the launch (LinkedIn post, details below)
2. Poros raises the invoice
3. Harvest is triggered (case study, blog post, testimonial request)

## Proposed Iris post (for your review)
{Draft a short LinkedIn announcement — one paragraph, specific, honest.
 What was built, for whom, what makes it interesting. No marketing language.
 Mark approves this before it goes anywhere.}

---
GATE DECISION: [ ] Approve delivery  [ ] Request changes
```

Notify Mark:
```bash
python3 /media/data/dev/bain-studio/studio/notifier.py \
  "{Project} is at the delivery gate — Themis cleared it. Gate package at context/pipeline/delivery/{slug}-gate-{date}.md — your approval needed." \
  --priority high --sender hermes --project {prefix}
```

**Stop here.** Do not proceed until Mark explicitly approves.

---

## Step 4 — Post-approval: Iris announces

After Mark's approval, invoke Iris:
```
/iris harvest {slug}
```

Iris drafts the LinkedIn post. Mark reviews and publishes when ready. Iris does not auto-publish.

---

## Step 5 — Post-approval: Poros raises the invoice

```
/poros {project-slug}
```

Poros produces the invoice. Mark reviews and sends.

---

## Step 6 — Post-approval: Harvest

```
/harvest {slug}
```

Harvest produces the case study, blog post, and testimonial request. Updates Mnemosyne.

---

## Step 7 — Mark the project delivered in Asana

Update the project mirror — set the delivery milestone task to DONE and add a progress note:

```
**Progress:** Delivered {YYYY-MM-DD}. Gate cleared by Themis. Invoice raised. Harvest triggered.
```

Run sync:
```bash
cd /media/data/dev/bain-studio && python3 studio/sync.py --project {PREFIX}
```

---

## Guard rails

- **The Law of the Gate:** Mark's approval is required between Step 3 and Step 4. This is not a formality — it is the gate. Bainbot does not deliver without it.
- **Themis first, always.** Do not prepare the gate package if Themis is BLOCKED. Fix the issues first.
- **No auto-publishing.** Iris drafts; Mark publishes. Poros produces; Mark sends.
- **One project at a time.** Do not run the delivery gate for multiple projects simultaneously.
