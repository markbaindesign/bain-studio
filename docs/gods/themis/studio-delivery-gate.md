---
description: Pre-delivery checklist — last gate before work reaches Mark for approval
god: themis
invoke: /studio-delivery-gate
tags:
- skill
---

# Studio Delivery Gate

The moment between "done" and "shipped." Orchestrates the full delivery sequence: Themis QA → gate report for Mark → (Mark approves) → Iris announces → Harvest triggers.

Mark walks through the gate. Nobody else can.

## Invoke

```
/studio-delivery-gate {project-slug}
```

Invoke when a project is ready to ship.

## Sequence

1. **Load project context** — reads `CLAUDE.md` and the Athena report (`{CONTENT_DIR}/pipeline/athena/{slug}-*.md`)
2. **Themis QA** — invokes `/themis review`; if **GATE BLOCKED**, stops and notifies Mark via Notifier (high priority)
3. **Aphrodite visual gate** — invokes `/aphrodite review`; if blocked, stops
4. **Gate package** — assembles a delivery review package at `{CONTENT_DIR}/pipeline/delivery/{slug}-gate-{date}.md` for Mark's sign-off
5. **Mark approves** — gate does not proceed without explicit approval
6. **Iris** — invokes `/iris harvest` to extract and draft social posts from the project
7. **Harvest** — invokes `/harvest {slug}` to generate case study, blog post, and testimonial request

## Gate package contents

- Themis QA ruling (scope, accessibility, performance)
- Aphrodite visual gate ruling
- Delivery URL and artefacts
- Mark's go/no-go decision point

## If gate is blocked

Notifier fires:
```bash
python3 studio/notifier.py "{Project} delivery gate BLOCKED — {N} issues." \
  --priority high --sender hermes --project {PREFIX}
```

All blockers are listed with their owner (Hephaestus for technical, Aphrodite for visual). Gate does not proceed until resolved and Themis re-run.

## Notes

- The delivery gate enforces Law V: every delivery triggers harvest automatically
- Iris and Harvest run after Mark approves — not before
- Gate packages accumulate as a delivery history per project

## See also

- [themis.md](themis.md) — QA check at step 2
- [aphrodite.md](aphrodite.md) — visual gate at step 3
- [iris.md](iris.md) — social broadcasting at step 6
- [harvest.md](harvest.md) — post-delivery outputs at step 7
- [notifier.md](notifier.md) — Slack alert when gate is blocked
