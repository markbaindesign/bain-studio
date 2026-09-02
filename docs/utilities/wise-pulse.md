---
tags: [tool, collector, finance]
god: hermes
invoke: .claude/skills/wise-pulse/wise_pulse.py
command: /wise-pulse
description: Polls Wise business and personal balances daily, detects movement, and pings Slack for manual booking in GnuCash
---

# wise-pulse

Polls the six tracked Wise balances (Business USD/GBP/EUR, Personal USD/GBP/EUR) through the Wise API, compares each against the previous checkpoint, and Slacks the deltas so they can be booked in GnuCash by hand.

This is an interim measure. It exists because Wise banking transaction feeds are not yet enabled (BSTD-775) - once they are, movement will be visible without polling and this collector becomes redundant. It reports *that* a balance moved, never *why*: there is no payee, no reference, no category. Attribution stays manual.

## Usage

```bash
python3 .claude/skills/wise-pulse/wise_pulse.py             # poll, notify on change, advance checkpoint
python3 .claude/skills/wise-pulse/wise_pulse.py --verbose   # print every balance, changed or not
python3 .claude/skills/wise-pulse/wise_pulse.py --dry-run   # poll only; no Slack, no checkpoint write
```

`--dry-run` writes no state, so it is always safe to run before a real pass.

## Scheduling

Runs from crontab against the release-pinned ops worktree, not this checkout (see [[ops-worktree]] and ADR 014):

```bash
30 8 * * * cd /home/bain/ops/bain-studio && python3 .claude/skills/wise-pulse/wise_pulse.py >> studio/collectors/wise_pulse.log 2>&1
```

Deploy the release to ops first with `studio/scripts/ops-deploy.sh` - a skill that only exists in the dev checkout will never run on the schedule.

## Files

- Credentials: `~/.config/wise/` - `token`, `wise_api_private.pem`, and the `wise_client.py` API client. Not in this repo.
- Checkpoint: `~/.wise/balances-checkpoint.json` - `{balance_id: amount}`, one entry per tracked balance.
- Log: `~/.wise/pulse.log`

Account and balance IDs are hardcoded in `ACCOUNTS` at the top of the script. Adding a Wise account means editing that list.

## Behaviour worth knowing

- **First run establishes a baseline.** No checkpoint means no notification - it writes the current balances and exits. The first real alert comes on the second run.
- **The checkpoint advances only after a successful Slack post.** A failed notification leaves the old checkpoint in place, so the movement is reported again on the next run rather than being lost silently.
- **Delta only, no attribution.** The Slack message gives account, currency, previous, current, delta. Matching that against a subscription or an invoice is a manual step, and a same-day in-and-out of equal size is invisible to it.

## See also

- [[notifier]] - the Slack transport; wise-pulse posts as `financial-review`
- [[financial-review]] - where the booked figures end up being reviewed
- [[ops-worktree]] - why cron runs a tag, not a branch
- **BSTD-775** - enable Wise banking transaction feeds, which retires this
