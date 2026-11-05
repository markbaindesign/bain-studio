---
tags: [tool, reporting, client-deliverable, retainer, harvest]
god: hermes
command: python3 studio/tools/retainer-report/retainer_report.py PREFIX
description: Monthly maintenance retainer report. Computes a retainer client's hour bank for a billing cycle from Harvest time entries, renders the client-facing email text, and flags anything needing a decision before it is sent. Draft only, never sends.
---

# Retainer Report

Each retainer client gets a short monthly email showing what their hours were
spent on and where the bank stands. This tool does the arithmetic and drafts
the text. It does not send anything.

## Where the config lives

Client terms and recipient addresses are **not in this repo**, which is
public. The real config is at `~/.config/bain-studio/retainer-clients.yaml`,
or wherever `RETAINER_CLIENTS` points. `clients.example.yaml` beside the
script is a placeholder template to copy, nothing more.

## Usage

```bash
python3 studio/tools/retainer-report/retainer_report.py PREFIX
python3 studio/tools/retainer-report/retainer_report.py PREFIX --cycle 2026-10-03
python3 studio/tools/retainer-report/retainer_report.py PREFIX --json
python3 studio/tools/retainer-report/retainer_report.py PREFIX --today 2026-11-05
```

- `PREFIX` is a client key from the config file.
- `--cycle` reports a specific cycle by its start date. Without it, the tool
  reports the most recent cycle that has finished, which is what the task on
  the invoice date is asking for.
- `--json` emits the computed figures instead of the email text.
- `--today` overrides the current date, for testing.

## Billing cycles, not calendar months

A cycle runs from the client's top-up day to the day before the next one,
inclusive: a client who tops up on the 3rd has an October cycle of **3
October to 2 November**. This keeps the balance on the report identical to
the balance on the invoice raised the same day, which is the whole point of
reporting at all.

The consequence worth knowing: "the October report" means a slightly
different window for each client, and work done on the 3rd of a month lands
in that month's cycle, not the previous one.

## What draws down the bank

Every logged minute, calls, email and meetings included. These are
maintenance work and they are charged. Only the task types listed under
`excluded_tasks` in `clients.yaml` are left out, which in practice means
`Free Gratis Work`, the deliberate write-off lever.

If a call should not have cost the client, move it to another Harvest project
or to `Free Gratis Work`. Do not expect the report to absorb it.

## Hour bank arithmetic

```
opening = (top-ups landed to date x hours_month) - hours used before this cycle
closing = opening - hours used this cycle
```

Harvest's `budget` field is **not** used. It is maintained by hand and the
`/projects` endpoint does not return spend at all, not even for billable
projects, so the tool sums time entries itself.

Rollover terms come from each client's signed agreement, set per client in
the config. The productised tiers in `maintenance-plans.md` cap rollover and
expire it; the pilot agreements do not. Never apply the price-list terms to a
client whose contract says otherwise.

## Review flags

The tool prints a `REVIEW BEFORE SENDING` block when something needs a
decision. None of these stop it producing the draft.

| Flag | Means |
|---|---|
| `OVERDRAWN` | Closing balance is negative. Bill the overage or absorb it. |
| `BEFORE FIRST CYCLE` | Hours logged before the retainer started. Not drawn from the bank. Confirm they are free. |
| `THIN NOTE` | A Harvest note that tells the client nothing ("Updates"). Rewrite before sending. |
| `NOT CHARGED` | An excluded task type was logged. Confirm it should be free. |

## Before it reaches the client

1. Run the tool.
2. Resolve every review flag.
3. Send the text through the copywriter for the voice pass.
4. Create the Gmail draft. **Never send without Mark's approval.**
5. Comment on the Asana task that the draft is ready, by editing the project
   mirror. Not via the Asana MCP.

## Recurrence

A recurring Asana task on each client's invoice day is the prompt. There is
deliberately no cron, so a report is never generated and forgotten without a
visible task.

**Not yet set up.** Asana recurrence is a UI-only setting, like project
icons, so the recurring tasks have to be created by hand in Asana. Until
that is done, nothing prompts the monthly run.

## Adding a client

Add a block to the config with the Harvest project id, the Asana project
gid, the monthly hours and rate from the signed agreement, the top-up day,
the first cycle start date, and the recipients. Terms come from the signed
contract in `Dropbox/Work/Projects/Client/<Client>/Admin/Contracts/`, not
from the price list.

## Related

- `maintenance-plans.md` (Dropbox, studio internal) is the product thinking
  behind the retainers. Its sections 3.4 and 3.5 describe a fuller report for
  the productised tiers, carrying updates applied, uptime and backup status.
  This tool covers the hour bank only, which is all the pilot contracts
  promise.
- [[ga-report]] for the analytics report, [[brand-doc]] for branded PDFs.
