---
name: wise-pulse
description: Daily Wise balance checker for bookkeeping. Polls balances, detects movement, and notifies. Interim measure while banking transaction feeds are pending.
allowed-tools: [Bash, Read, Write]
---

# Wise Pulse

**Wise Pulse** keeps your Wise business and personal account balances under observation. It polls balances daily, detects changes, and notifies via Slack for manual booking in GnuCash.

This is an interim solution until Wise banking feeds are available (BSTD-775).

---

## Setup

### Prerequisites

The Wise API client and credentials must already be installed:
- Client: `~/.config/wise/wise_client.py`
- Token: `~/.config/wise/token`
- Key: `~/.config/wise/wise_api_private.pem`

If these don't exist, set them up via the Wise dashboard at https://app.transferwise.com/user/settings/api.

### Profiles and balance IDs

Wise Pulse tracks these accounts by default:

| Profile | Type | Currency | Balance ID |
|---------|------|----------|-----------|
| Business (55828700) | Bain Design | USD | 93635981 |
| Business (55828700) | Bain Design | GBP | 93635748 |
| Business (55828700) | Bain Design | EUR | 93635923 |
| Personal (2753862) | Personal | GBP | 32845501 |
| Personal (2753862) | Personal | USD | 18115479 |
| Personal (2753862) | Personal | EUR | 18115478 |

Checkpoint data is stored in `~/.wise/balances-checkpoint.json`.

---

## Invoke

```bash
/wise-pulse [--verbose] [--dry-run]
```

**Arguments:**
- `--verbose`: Show detailed balance output
- `--dry-run`: Check balances without updating checkpoint or notifying

---

## How it works

1. **Poll balances** — Call `~/.config/wise/wise_client.py balances <profileId>` for both profiles
2. **Compare** — Read previous checkpoint from `~/.wise/balances-checkpoint.json`
3. **Detect changes** — For each balance, if current amount ≠ previous amount, flag it
4. **Notify** — Use `/notify` skill to Slack the changes (account, currency, previous, new, delta)
5. **Update checkpoint** — Write new checkpoint only after successful notification
6. **Log** — Record to `~/.wise/pulse.log`

---

## Example output

```
Wise Pulse poll: 6 balances checked
  ✓ Business/USD: $12,345.67 (no change)
  → Personal/GBP: £8,920.45 → £8,950.45 (+£30.00) [transfer in]
  ✓ Business/GBP: £15,200.00 (no change)
  ...
1 balance changed. Notified.
```

Slack notification:
```
Personal GBP balance: £8,920.45 → £8,950.45 (delta: +£30.00)
Please review and book in GnuCash.
```

---

## Scheduling

Run daily via cron or the `/schedule` skill:

```bash
# Daily at 09:30
/schedule --cron "30 9 * * *" --command "/wise-pulse"
```

Or add to crontab:
```bash
30 9 * * * python3 -c "import subprocess; subprocess.run(['claude', '--dangerously-skip-permissions', '-p', '/wise-pulse'], cwd='/media/data/dev/bain-studio')"
```

---

## Logs

Logs go to `~/.wise/pulse.log`. Check recent runs:
```bash
tail -f ~/.wise/pulse.log
```

---

## Troubleshooting

**"Wise client not found"**
- Ensure `~/.config/wise/wise_client.py` exists
- Run it directly: `python3 ~/.config/wise/wise_client.py profiles` (should list your profiles)

**"SCA challenge"** (two-factor authentication)
- Wise Pulse automatically handles SCA challenges via the client's existing signing flow
- If a challenge fails, manual setup may be needed — see `~/.config/wise/wise_client.py`

**"No checkpoint found"** (first run)
- This is normal. Wise Pulse creates the checkpoint on first run
- No notification is sent on the first run (baseline only)

**Incorrect balance values**
- Verify profile IDs and balance IDs in the Wise dashboard
- Update the hardcoded list in the pulse script if Wise adds new accounts

---

## Next phase: transaction inference

Once stable, Wise Pulse can attempt to match balance deltas against expected transactions:
- Check `studio/config/recurring-transactions.yaml` for known recurring charges
- Propose matching GnuCash entries based on amount + typical billing date
- Requires manual confirmation before booking (not automatic)

---

## See also

- **BSTD-775**: Enable Wise banking transaction feeds (blocks auto-booking without inference)
- `/notify` skill: Slack notifications
- GnuCash: Where the transactions are booked
